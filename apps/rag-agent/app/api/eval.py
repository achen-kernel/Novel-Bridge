import datetime
import logging
import os
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.eval.eval_runner import EvalRunner
from app.pipeline.dataset_exporter import DatasetExporter, TRAINING_DATA_DIR
from app.stores.eval_store import EvalStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/eval", tags=["eval"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


class EvalRunResponse(BaseModel):
    run_id: int
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


class ExportResponse(BaseModel):
    status: str
    samples: int = 0
    file: str = ""
    book_count: int = 0
    message: str = ""


@router.post("/run", response_model=EvalRunResponse)
async def run_eval(book_id: int = None, category: str = None, use_deepseek: bool = False):
    """运行评估"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    runner = EvalRunner(db_client)
    result = await runner.run_all(book_id=book_id, category=category, use_deepseek=use_deepseek)

    return EvalRunResponse(
        run_id=result.get('run_id', 0),
        total=result.get('total', 0),
        passed=result.get('passed', 0),
        failed=result.get('failed', 0),
        pass_rate=result.get('pass_rate', 0.0),
    )


@router.post("/export/chapter-facts", response_model=ExportResponse)
async def export_chapter_facts(book_id: int = None, min_review: str = "ACCEPTED"):
    """导出 ChapterFacts 为训练数据"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    exporter = DatasetExporter(db_client)
    result = exporter.export_chapter_facts(book_id=book_id, min_review_status=min_review)

    return ExportResponse(**result)


@router.post("/export/qa-pairs", response_model=ExportResponse)
async def export_qa_pairs(book_id: int = None):
    """导出 QA 对为训练数据"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    exporter = DatasetExporter(db_client)
    result = exporter.export_qa_pairs(book_id=book_id)

    return ExportResponse(**result)


class TrainingFile(BaseModel):
    filename: str
    size: int = 0
    modified: str = ""


@router.get("/training-files", response_model=List[TrainingFile])
async def list_training_files():
    """列出可下载的训练数据文件"""
    files = []
    if os.path.exists(TRAINING_DATA_DIR):
        for f in sorted(os.listdir(TRAINING_DATA_DIR), reverse=True):
            if f.endswith('.jsonl'):
                fp = os.path.join(TRAINING_DATA_DIR, f)
                stat = os.stat(fp)
                files.append(TrainingFile(
                    filename=f,
                    size=stat.st_size,
                    modified=str(datetime.datetime.fromtimestamp(stat.st_mtime)),
                ))
    return files


@router.get("/download/{filename}")
async def download_training_file(filename: str):
    """下载训练数据文件"""
    filepath = os.path.join(TRAINING_DATA_DIR, filename)
    if not os.path.exists(filepath) or not filename.endswith('.jsonl'):
        raise HTTPException(404, "File not found")
    return FileResponse(filepath, filename=filename, media_type='application/octet-stream')
