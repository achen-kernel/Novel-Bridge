"""
Pipeline status API — 查询和触发 Pipeline 阶段。
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


class PhaseInfo(BaseModel):
    phase: str
    name: str
    status: str = "PENDING"
    run_id: int = 0
    output: dict = {}
    error: str = ""
    started_at: str = ""


class PipelineStatus(BaseModel):
    book_id: int
    book_title: str = ""
    book_status: str = ""
    phases: list = []


PHASE_NAMES = {
    "P3": "实体/关系/事件抽取",
    "P4": "实体治理",
    "P5": "叙事构建",
    "P6": "Qdrant 索引",
    "P7": "Neo4j 图谱投影",
    "P8": "训练数据导出",
}

RUN_TYPE_MAP = {
    "EXTRACT": "P3",
    "ENTITY_GOVERNANCE": "P4",
    "NARRATIVE": "P5",
    "INDEX": "P6",
    "GRAPH_PROJECT": "P7",
    "EXPORT": "P8",
}

PHASE_API_MAP = {
    "P3": ("/api/books/{book_id}/extract", {"use_model": True}),
    "P4": ("/api/books/{book_id}/govern", {}),
    "P5": ("/api/books/{book_id}/narrative", {}),
    "P6": ("/api/books/{book_id}/index", {"reindex": False}),
    "P7": ("/api/books/{book_id}/graph/project", {}),
    "P8": ("/api/eval/export/chapter-facts?book_id={book_id}&min_review=PENDING", None),
}


@router.get("/{book_id}/status", response_model=PipelineStatus)
async def pipeline_status(book_id: int):
    """获取某本书的 Pipeline 状态"""
    if db_client is None:
        raise HTTPException(503, "Database not initialized")

    conn = db_client.connect()
    try:
        # 获取 book 信息
        with conn.cursor() as c:
            c.execute("SELECT id, title, status FROM novel_book WHERE id = %s", (book_id,))
            book = c.fetchone()
            if not book:
                raise HTTPException(404, "Book not found")

        # 获取所有 run 记录
        runs = {}
        with conn.cursor() as c:
            c.execute(
                "SELECT id, run_type, status, output_json, error_message, started_at "
                "FROM novel_agent_run WHERE book_id = %s ORDER BY id",
                (book_id,)
            )
            for r in c.fetchall():
                phase = RUN_TYPE_MAP.get(r['run_type'])
                if phase:
                    output = {}
                    if r.get('output_json'):
                        try:
                            import json
                            output = json.loads(r['output_json']) if isinstance(r['output_json'], str) else r['output_json']
                        except Exception:
                            output = {}
                    runs[phase] = {
                        'run_id': r['id'],
                        'status': r['status'],
                        'output': output,
                        'error': r.get('error_message', '') or '',
                        'started_at': str(r.get('started_at', '') or ''),
                    }

        # 构建 phases 列表
        phases = []
        for phase_num in ['P3', 'P4', 'P5', 'P6', 'P7', 'P8']:
            run = runs.get(phase_num, {})
            phases.append(PhaseInfo(
                phase=phase_num,
                name=PHASE_NAMES.get(phase_num, phase_num),
                status=run.get('status', 'PENDING'),
                run_id=run.get('run_id', 0),
                output=run.get('output', {}),
                error=run.get('error', ''),
                started_at=run.get('started_at', ''),
            ))

        return PipelineStatus(
            book_id=book['id'],
            book_title=book['title'],
            book_status=book['status'],
            phases=phases,
        )

    finally:
        conn.close()
