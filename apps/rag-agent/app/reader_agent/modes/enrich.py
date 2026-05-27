"""ReaderAgent enrich mode, minimal KnowledgePatch candidate wrapper."""

from __future__ import annotations

import logging
from typing import Any

from app.agent_runtime.citation_verifier import CitationVerifier
from app.agent_runtime.run_store import MysqlAgentRunStore
from app.knowledge_patch.schemas import KnowledgePatch, PatchType, RiskLevel
from app.knowledge_patch.service import KnowledgePatchService
from app.knowledge_patch.store import MysqlKnowledgePatchStore
from app.reader_agent.schemas import ReaderRequest, ReaderResponse
from app.reader_agent.states import ReaderState

logger = logging.getLogger(__name__)

ALLOWED_ENRICH_TYPES: dict[str, PatchType] = {
    "citation_fix": PatchType.CITATION_FIX,
    "eval_case_candidate": PatchType.EVAL_CASE_CANDIDATE,
    "context_summary_update": PatchType.CONTEXT_SUMMARY_UPDATE,
}


class EnrichMode:
    """Minimal enrich mode.

    It proposes low-risk KnowledgePatch candidates from caller-supplied L2
    evidence. It never merges and never creates high-risk patch types.
    """

    def __init__(self, conn=None) -> None:
        self.conn = conn

    async def run(self, request: ReaderRequest) -> ReaderResponse:
        if self.conn is None:
            return ReaderResponse(
                mode="enrich",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent enrich mode requires a MySQL connection."],
            )

        issue_type = request.issue_type
        if issue_type not in ALLOWED_ENRICH_TYPES:
            return ReaderResponse(
                mode="enrich",
                status=ReaderState.NEED_FOLLOWUP,
                errors=[
                    "ReaderAgent enrich mode only supports citation_fix, "
                    "eval_case_candidate, and context_summary_update."
                ],
            )

        run_store = MysqlAgentRunStore(self.conn)
        run_id = run_store.create_run(
            agent_name="ReaderAgent",
            mode="enrich",
            payload={
                "book_id": request.book_id,
                "question": request.question,
                "issue_type": issue_type,
                "target": request.target or request.target_name,
                "evidence_count": len(request.evidence),
                "options": request.options.model_dump(),
            },
        )
        step_id = run_store.create_step(
            run_id,
            "PATCH_DRAFTED",
            payload={
                "issue_type": issue_type,
                "target": request.target or request.target_name,
                "evidence_count": len(request.evidence),
            },
            step_order=0,
        )

        verification = CitationVerifier().verify(request.evidence)
        if not request.evidence or not verification.ok:
            errors = verification.errors or ["KnowledgePatch proposal requires evidence."]
            run_store.finish_step(
                step_id,
                "FAILED",
                payload={
                    "evidence_count": len(request.evidence),
                    "citation_verification_passed": verification.ok,
                    "citation_verification_errors": verification.errors,
                },
                error_type="INSUFFICIENT_EVIDENCE",
                error_message="; ".join(errors),
            )
            run_store.finish_run(
                run_id,
                ReaderState.INSUFFICIENT_EVIDENCE.value,
                payload={"patch_count": 0, "issue_type": issue_type},
                error_type="INSUFFICIENT_EVIDENCE",
                error_message="; ".join(errors),
            )
            return ReaderResponse(
                run_id=run_id,
                mode="enrich",
                status=ReaderState.INSUFFICIENT_EVIDENCE,
                answer="INSUFFICIENT_EVIDENCE",
                evidence=request.evidence,
                citations=request.evidence,
                errors=errors,
            )

        try:
            patch = KnowledgePatch(
                book_id=request.book_id,
                patch_type=ALLOWED_ENRICH_TYPES[issue_type],
                target_type=request.target_type or "reader_agent",
                payload=self._payload(request),
                evidence=request.evidence,
                risk_level=RiskLevel.LOW,
                created_by="reader_agent",
                run_id=run_id,
            )
            service = KnowledgePatchService(MysqlKnowledgePatchStore(self.conn))
            result = service.propose(patch)
            patches = [{
                "patch_type": patch.patch_type.value,
                "patch_id": result.get("patch_id"),
                "status": result.get("status"),
                "ok": result.get("ok", False),
                "errors": result.get("errors", []),
            }]
            status = ReaderState.RESPONDED if result.get("ok") else ReaderState.FAILED
            errors = result.get("errors", [])
            run_store.finish_step(step_id, "SUCCESS" if result.get("ok") else "FAILED", payload=result)
            run_store.finish_run(
                run_id,
                status.value,
                payload={
                    "patch_count": 1 if result.get("ok") else 0,
                    "issue_type": issue_type,
                    "patch_result": result,
                },
            )
            return ReaderResponse(
                run_id=run_id,
                mode="enrich",
                status=status,
                answer="KnowledgePatch candidate proposed." if result.get("ok") else "",
                citations=request.evidence,
                evidence=request.evidence,
                patches=patches,
                errors=errors,
            )
        except Exception as exc:
            logger.exception("ReaderAgent enrich failed")
            run_store.finish_step(
                step_id,
                "FAILED",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            run_store.finish_run(
                run_id,
                "FAILED",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return ReaderResponse(
                run_id=run_id,
                mode="enrich",
                status=ReaderState.FAILED,
                citations=request.evidence,
                evidence=request.evidence,
                errors=[f"ReaderAgent enrich failed: {exc}"],
            )

    def _payload(self, request: ReaderRequest) -> dict[str, Any]:
        return {
            "issue_type": request.issue_type,
            "question": request.question[:300],
            "target": request.target or request.target_name,
            "target_type": request.target_type,
            "generated_by": "ReaderAgent.enrich",
            "schema_version": "1",
        }
