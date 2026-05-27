import logging
import traceback
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.pipeline.chunker import chunk_chapter
from app.pipeline.splitter import split_chapters
from app.stores.book_source_store import BookSourceStore
from app.stores.chapter_store import ChapterStore
from app.stores.chunk_store import ChunkStore
from app.stores.model_run_store import ModelRunStore

logger = logging.getLogger(__name__)


class BookProcessor:
    """处理一本书：分成章节 → 构建 chunks → 写回 DB"""

    STEP_SPLIT = "SPLIT_CHAPTERS"
    STEP_CHUNK = "BUILD_CHUNKS"

    def __init__(self, db: MysqlClient):
        self.db = db

    def process(self, book_id: int, run_id: Optional[int] = None) -> dict:
        """处理一本书的完整流程"""
        conn = self.db.connect()
        run_store = ModelRunStore(conn)

        try:
            book_source_store = BookSourceStore(conn)
            chapter_store = ChapterStore(conn)
            chunk_store = ChunkStore(conn)

            # 如果没有传入 run_id，自行创建 AgentRun
            if run_id is None:
                run_id = run_store.create_run('BOOK_BUILD', book_id, {'book_id': book_id})
                logger.info(f"Created AgentRun {run_id} for book {book_id}")

            # 1. 读取原始文本
            book = book_source_store.get_book_raw_text(book_id)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            raw_text = book["raw_text"]
            if not raw_text:
                raise ValueError(f"Book {book_id} has empty raw_text")

            logger.info(f"Processing book {book_id}: {book.get('title', '')} ({len(raw_text)} chars)")

            # 2. 读取 prior_hint（DeepSeek 梗概），用于辅助拆章
            prior_hint = book.get("prior_hint_json")
            if prior_hint and isinstance(prior_hint, str):
                import json
                try:
                    prior_hint = json.loads(prior_hint)
                except json.JSONDecodeError:
                    prior_hint = None

            step_id = run_store.create_step(
                run_id, self.STEP_SPLIT, 1, {"book_id": book_id, "char_count": len(raw_text)}
            )

            chapters = split_chapters(raw_text, prior_hint=prior_hint)

            run_store.update_step_status(
                step_id,
                "SUCCESS",
                {
                    "chapter_count": len(chapters),
                    "strategy": chapters[0]["split_strategy"] if chapters else "none",
                },
            )

            logger.info(f"Split {len(chapters)} chapters")

            # 3. 保存章节到 DB
            chapter_ids = []
            for ch in chapters:
                ch_id = chapter_store.insert_chapter(
                    book_id=book_id,
                    chapter_number=ch["chapter_number"],
                    title=ch["title"],
                    content=ch["content"],
                    start_offset=ch["start_offset"],
                    end_offset=ch["end_offset"],
                    split_strategy=ch["split_strategy"],
                    split_confidence=ch["split_confidence"],
                )
                chapter_ids.append(ch_id)

            # 4. 构建 chunks
            step_id = run_store.create_step(
                run_id,
                self.STEP_CHUNK,
                2,
                {"book_id": book_id, "chapter_count": len(chapters)},
            )

            total_chunks = 0
            for ch, ch_id in zip(chapters, chapter_ids):
                chunks = chunk_chapter(
                    chapter_id=ch_id,
                    book_id=book_id,
                    chapter_text=ch["content"],
                    chapter_start_offset=ch["start_offset"],
                )
                for ck in chunks:
                    chunk_store.insert_chunk(
                        book_id=book_id,
                        chapter_id=ch_id,
                        chunk_index=ck["chunk_index"],
                        content=ck["content"],
                        start_offset=ck["start_offset"],
                        end_offset=ck["end_offset"],
                    )
                total_chunks += len(chunks)

            run_store.update_step_status(
                step_id,
                "SUCCESS",
                {"total_chunks": total_chunks},
            )

            # 5. 更新 book 状态
            book_source_store.update_book_status(
                book_id=book_id,
                status="BUILT",
                chapter_count=len(chapters),
                chunk_count=total_chunks,
            )

            # 6. 更新 run 状态
            run_store.update_run_status(
                run_id,
                "SUCCESS",
                {
                    "book_id": book_id,
                    "chapters": len(chapters),
                    "chunks": total_chunks,
                    "char_count": len(raw_text),
                },
            )

            logger.info(f"Book {book_id} processed: {len(chapters)} chapters, {total_chunks} chunks")

            return {
                "status": "success",
                "book_id": book_id,
                "run_id": run_id,
                "chapters": len(chapters),
                "chunks": total_chunks,
                "char_count": len(raw_text),
            }

        except Exception as e:
            logger.error(f"Failed to process book {book_id}: {e}")
            logger.error(traceback.format_exc())

            try:
                book_source_store = BookSourceStore(conn)
                book_source_store.update_book_status(
                    book_id=book_id, status="FAILED", error_message=str(e)
                )
                assert run_id is not None
                run_store.update_run_status(
                    run_id, "FAILED", error_type=type(e).__name__, error_message=str(e)
                )
            except Exception as inner_e:
                logger.error(f"Failed to update error status: {inner_e}")

            return {
                "status": "error",
                "book_id": book_id,
                "error": str(e),
            }
