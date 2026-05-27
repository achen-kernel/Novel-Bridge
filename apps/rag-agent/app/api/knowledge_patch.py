"""
KnowledgePatch API 路由。支持 propose-only 流程：
- POST /api/knowledge-patches          propose new patch
- GET  /api/knowledge-patches           list patches
- GET  /api/knowledge-patches/{id}      get single patch (with review_logs)
- POST /api/knowledge-patches/{id}/review  review with action or approved
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.agent_runtime.schemas import EvidenceItem
from app.knowledge_patch.schemas import (
    KnowledgePatch,
    PatchStatus,
    PatchType,
    RiskLevel,
)
from app.knowledge_patch.service import KnowledgePatchService
from app.knowledge_patch.store import MysqlKnowledgePatchStore
from app.knowledge_patch.validator import KnowledgePatchValidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge-patches", tags=["knowledge-patches"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


class ProposeRequest(BaseModel):
    book_id: int
    patch_type: PatchType
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    payload: dict[str, Any] = {}
    evidence: list[EvidenceItem] = []
    risk_level: RiskLevel = RiskLevel.MEDIUM
    created_by: str = "reader_agent"
    run_id: Optional[int] = None


class ReviewRequest(BaseModel):
    action: str = ""  # ACCEPT | REJECT | NEEDS_MORE_EVIDENCE | SUPERSEDE
    approved: Optional[bool] = None  # backward compat
    note: str = ""
    reviewed_by: str = "human"
    risk_override: Optional[str] = None


class ProposeResponse(BaseModel):
    ok: bool
    patch_id: Optional[int] = None
    status: str = ""
    errors: list[str] = []


@router.post("", response_model=ProposeResponse)
async def propose_patch(req: ProposeRequest):
    """Propose a KnowledgePatch. Validates and stores, never auto-merges."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    store = MysqlKnowledgePatchStore(conn)
    service = KnowledgePatchService(store)

    patch = KnowledgePatch(
        book_id=req.book_id,
        patch_type=req.patch_type,
        target_type=req.target_type,
        target_id=req.target_id,
        payload=req.payload,
        evidence=req.evidence,
        risk_level=req.risk_level,
        created_by=req.created_by,
        run_id=req.run_id,
    )
    result = service.propose(patch)
    return ProposeResponse(**result)


@router.get("")
async def list_patches(book_id: int | None = None, status: str | None = None, limit: int = 50):
    """List KnowledgePatches with evidence_count and review_count."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    store = MysqlKnowledgePatchStore(conn, auto_create=False)
    return store.list_patches(book_id=book_id, status=status, limit=limit)


@router.get("/{patch_id}")
async def get_patch(patch_id: int):
    """Get a single KnowledgePatch with evidence + review_logs."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    store = MysqlKnowledgePatchStore(conn, auto_create=False)
    patch = store.get_patch(patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")
    return patch


@router.post("/{patch_id}/review", response_model=ProposeResponse)
async def review_patch(patch_id: int, req: ReviewRequest):
    """Review a KnowledgePatch.

    Use action: ACCEPT | REJECT | NEEDS_MORE_EVIDENCE | SUPERSEDE.
    Backward compat: approved=True → ACCEPT, approved=False → REJECT.
    Does NOT auto-merge.
    """
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    store = MysqlKnowledgePatchStore(conn, auto_create=False)
    service = KnowledgePatchService(store)

    result = service.review(
        patch_id,
        approved=req.approved,
        action=req.action,
        review_note=req.note,
        reviewed_by=req.reviewed_by,
        risk_override=req.risk_override,
    )
    return ProposeResponse(**result)
