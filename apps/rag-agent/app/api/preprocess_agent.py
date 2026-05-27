"""
PreprocessAgent API 路由。支持：
- POST /api/preprocess-agent/run
- POST /api/preprocess-agent/plan   (dry-run, no data written)
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.clients.mysql_client import MysqlClient
from app.preprocess_agent import PreprocessAgent
from app.preprocess_agent.schemas import (
    PreprocessPlanRequest,
    PreprocessPlanResponse,
    PreprocessRequest,
    PreprocessResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/preprocess-agent", tags=["preprocess-agent"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


@router.post("/run", response_model=PreprocessResult)
async def preprocess_agent_run(req: PreprocessRequest):
    """PreprocessAgent 入口。复用现有 pipeline 包装器。"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    agent = PreprocessAgent(db_client)
    result = await agent.run(req)
    return result


@router.post("/plan", response_model=PreprocessPlanResponse)
async def preprocess_agent_plan(req: PreprocessPlanRequest):
    """PreprocessAgent dry-run plan. 不执行、不写数据。"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    agent = PreprocessAgent(db_client)
    result = await agent.plan(
        book_id=req.book_id,
        start_state=req.start_state,
        target_state=req.target_state,
    )
    return result
