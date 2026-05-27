"""
QA (问答) API 路由。
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.qa.qa_runner import QaRunner
from app.schemas.qa import QaRequest, QaResponse, CitationItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/qa", tags=["qa"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


@router.post("/ask", response_model=QaResponse)
async def ask_question(req: QaRequest):
    """回答一个关于小说的问题"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    runner = QaRunner(conn)

    result = await runner.answer(
        session_id=req.session_id,
        book_id=req.book_id,
        question=req.question,
        use_deepseek=req.use_deepseek  # True = DeepSeek API, False = local 9B
    )

    citations = [
        CitationItem(
            source_type=c.get('source_type', 'chunk'),
            source_id=c.get('source_id', 0),
            chapter_id=c.get('chapter_id', 0),
            excerpt=c.get('excerpt', ''),
            evidence_level=c.get('evidence_level', 'NEAR'),
            relevance_score=c.get('relevance_score', 0.5)
        )
        for c in result.get('citations', [])
    ]

    return QaResponse(
        answer=result.get('answer', ''),
        citations=citations
    )
