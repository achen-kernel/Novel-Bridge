import hashlib
import json
import logging
import os
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.pipeline.book_processor import BookProcessor
from app.pipeline.splitter import split_chapters

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/books", tags=["books"])

# 共享 db 实例 (在 main.py 中注入)
db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


class ProcessRequest(BaseModel):
    run_id: Optional[int] = None


class ProcessResponse(BaseModel):
    status: str
    book_id: int
    run_id: int = 0
    chapters: int = 0
    chunks: int = 0
    char_count: int = 0
    error: str = ""


@router.post("/{book_id}/process", response_model=ProcessResponse)
async def process_book(book_id: int, req: ProcessRequest):
    """处理一本书：拆章 + chunking"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    processor = BookProcessor(db_client)
    result = processor.process(book_id, run_id=req.run_id)

    if result["status"] == "error":
        return ProcessResponse(
            status="error", book_id=book_id, error=result.get("error", "Unknown error")
        )

    return ProcessResponse(
        status="success",
        book_id=book_id,
        run_id=result.get("run_id", 0),
        chapters=result["chapters"],
        chunks=result["chunks"],
        char_count=result["char_count"],
    )


class UploadResponse(BaseModel):
    status: str
    book_id: int = 0
    book_title: str = ""
    chapters: int = 0
    files_accepted: int = 0
    error: str = ""


@router.post("/upload", response_model=UploadResponse)
async def upload_book(
    title: str = Form(...),
    author: str = Form(""),
    language: str = Form("zh"),
    files: List[UploadFile] = File(...),
):
    """上传书籍文件（支持多文件/多卷合并为一本书）
    
    接受 TXT 文件，多文件按文件名排序后拼接。
    自动检测章节标题，写入 novel_book + novel_chapter 表。
    上传后状态为 UPLOADED，可通过 P3 端点启动提取。
    """
    if db_client is None:
        raise HTTPException(503, "Database not initialized")
    if not files:
        raise HTTPException(400, "No files uploaded")

    # 1. 排序文件（按文件名，以便多卷按顺序合并）
    sorted_files = sorted(files, key=lambda f: f.filename or "")

    # 2. 读取并合并文本
    full_text = ""
    file_names = []
    for f in sorted_files:
        content_bytes = await f.read()
        # 尝试 UTF-8，失败则 GB18030
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("gb18030")
            except UnicodeDecodeError:
                text = content_bytes.decode("gbk", errors="replace")
        full_text += text + "\n\n"
        file_names.append(f.filename or "unnamed")

    if not full_text.strip():
        raise HTTPException(400, "Empty file content")

    # 3. 创建 novel_book 记录
    conn = db_client.connect()
    book_id = None
    try:
        source_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

        # 检查是否已存在相同内容的书（防重复上传）
        with conn.cursor() as c:
            c.execute("SELECT id, title FROM novel_book WHERE source_hash = %s", (source_hash,))
            existing = c.fetchone()
            if existing:
                return UploadResponse(
                    status="duplicate",
                    book_id=existing['id'],
                    book_title=existing['title'],
                    chapters=0,
                    files_accepted=0,
                    error=f"内容相同的书已存在: {existing['title']} (ID={existing['id']})",
                )

        with conn.cursor() as c:
            c.execute(
                "INSERT INTO novel_book (title, author, language, status, raw_text, source_hash, "
                "source_file_name, char_count) "
                "VALUES (%s, %s, %s, 'UPLOADED', %s, %s, %s, %s)",
                (title, author, language, full_text, source_hash,
                 ", ".join(file_names[:5]), len(full_text.replace(" ", "").replace("\n", ""))),
            )
            book_id = c.lastrowid
        conn.commit()
        logger.info(f"Created book #{book_id}: {title} ({len(full_text)} chars)")

        # 4. 拆章
        chapters = split_chapters(full_text, book_id)
        logger.info(f"  Split into {len(chapters)} chapters")

        # 5. 写入 novel_chapter
        with conn.cursor() as c:
            for ch in chapters:
                c.execute(
                    "INSERT INTO novel_chapter (book_id, chapter_number, title, raw_content, status) "
                    "VALUES (%s, %s, %s, %s, 'CREATED')",
                    (book_id, ch['chapter_number'], ch['title'], ch['content']),
                )
        conn.commit()

        # 6. 更新 chapter_count
        with conn.cursor() as c:
            c.execute(
                "UPDATE novel_book SET chapter_count = %s WHERE id = %s",
                (len(chapters), book_id),
            )
        conn.commit()

        return UploadResponse(
            status="success",
            book_id=book_id,
            book_title=title,
            chapters=len(chapters),
            files_accepted=len(sorted_files),
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        if book_id:
            try:
                with conn.cursor() as c:
                    c.execute("DELETE FROM novel_book WHERE id = %s", (book_id,))
                conn.commit()
            except Exception:
                pass
        raise HTTPException(500, f"Upload failed: {str(e)}")
    finally:
        conn.close()
