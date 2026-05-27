"""ReaderAgent answer mode adapter — with Run/Step/Trace/Citation/Model/Tool/Patch recording."""

from __future__ import annotations

import logging
from typing import Any

from app.agent_runtime.citation_verifier import CitationVerifier
from app.agent_runtime.model_call_store import MysqlModelCallStore
from app.agent_runtime.run_store import MysqlAgentRunStore
from app.agent_runtime.schemas import EvidenceItem, EvidenceLevel
from app.agent_runtime.state_machine import StateMachine
from app.agent_runtime.tool_call_store import MysqlToolCallStore
from app.agent_runtime.trace_store import MysqlRetrievalTraceStore
from app.knowledge_patch.schemas import (
    KnowledgePatch,
    PatchType,
    RiskLevel,
)
from app.knowledge_patch.service import KnowledgePatchService
from app.knowledge_patch.store import MysqlKnowledgePatchStore
from app.qa.qa_runner import QaRunner
from app.reader_agent.schemas import ReaderRequest, ReaderResponse
from app.reader_agent.states import ReaderState

logger = logging.getLogger(__name__)

# Patch types allowed for ReaderAgent auto-enrich
ALLOWED_PATCH_TYPES = frozenset({
    PatchType.CITATION_FIX,
    PatchType.EVAL_CASE_CANDIDATE,
    PatchType.CONTEXT_SUMMARY_UPDATE,
})


def _generate_enrich_patches(
    request: ReaderRequest,
    answer_text: str,
    raw_citations: list[dict],
    verification_passed: bool,
    verification_errors: list[str],
    run_id: int,
) -> list[dict[str, Any]]:
    """Deterministic patch generation — no LLM calls, only rules.

    Returns list of patch dicts with {ok, patch_id, status, errors} per patch.
    Failed proposals are recorded as errors but never crash the answer flow.
    """
    patches: list[dict[str, Any]] = []
    evidence_items = [
        EvidenceItem(
            source_type=_SOURCE_MAP.get(c.get("source_type", ""), "chunk"),
            source_id=c.get("source_id", 0),
            chapter_id=c.get("chapter_id"),
            excerpt=c.get("excerpt", "")[:300] if c.get("excerpt") else "",
            evidence_level=_EVIDENCE_MAP.get(
                c.get("evidence_level", ""), EvidenceLevel.NEAR
            ),
            relevance_score=c.get("relevance_score", 0.0),
        )
        for c in raw_citations[:10]
    ]
    if not evidence_items:
        # Fallback: use question as evidence context
        evidence_items = [
            EvidenceItem(
                source_type="chunk",
                source_id=0,
                excerpt=f"Question: {request.question[:200]}",
                evidence_level=EvidenceLevel.INFERRED,
            )
        ]

    # Rule 1: citation verification found issues → citation_fix
    if not verification_passed and verification_errors:
        patch = KnowledgePatch(
            book_id=request.book_id,
            patch_type=PatchType.CITATION_FIX,
            target_type="citation",
            payload={
                "question": request.question[:200],
                "answer_preview": answer_text[:200],
                "issues": verification_errors,
                "generated_by": "ReaderAgent.answer",
                "schema_version": "1",
            },
            evidence=evidence_items,
            risk_level=RiskLevel.LOW,
            created_by="reader_agent",
            run_id=run_id,
        )
        patches.append({
            "candidate": patch,
            "reason": f"citation_verification: {len(verification_errors)} issue(s)",
        })

    # Rule 2: insufficient evidence (INSUFFICIENT_EVIDENCE was set or citations empty)
    if not answer_text.strip() or not raw_citations:
        patch = KnowledgePatch(
            book_id=request.book_id,
            patch_type=PatchType.EVAL_CASE_CANDIDATE,
            target_type="eval",
            payload={
                "question": request.question[:200],
                "answer_preview": answer_text[:200],
                "issue_type": "insufficient_evidence",
                "context": "ReaderAgent could not produce evidence-based answer",
                "generated_by": "ReaderAgent.answer",
                "schema_version": "1",
            },
            evidence=evidence_items,
            risk_level=RiskLevel.LOW,
            created_by="reader_agent",
            run_id=run_id,
        )
        patches.append({
            "candidate": patch,
            "reason": "insufficient_evidence: no citations or empty answer",
        })

    return patches


# ---- Mapping helpers for old QA output -> Agent schema ----

_EVIDENCE_MAP = {
    "EXACT": EvidenceLevel.DIRECT,
    "DIRECT": EvidenceLevel.DIRECT,
    "NEAR": EvidenceLevel.NEAR,
    "INFERRED": EvidenceLevel.INFERRED,
}

_SOURCE_MAP: dict[str, str] = {
    "entity_profile": "entity",
    "relation_fact": "relation",
    "chapter_fact": "chapter_fact",
    "chunk": "chunk",
    "relation": "relation",
    "event": "event",
    "entity": "entity",
    "citation": "citation",
}


class AnswerMode:
    """Wrap existing QaRunner with Agent Run/Step/Trace/Citation recording.

    Does NOT change old QA API (/api/qa/ask) behavior.
    """

    def __init__(self, conn=None, machine: StateMachine | None = None) -> None:
        self.conn = conn
        self.machine = machine

    async def run(self, request: ReaderRequest) -> ReaderResponse:
        if self.conn is None:
            return ReaderResponse(
                mode="answer",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent answer mode requires a MySQL connection."],
            )

        # ---- 1. Init stores ----
        run_store = MysqlAgentRunStore(self.conn)
        trace_store = MysqlRetrievalTraceStore(self.conn)
        model_call_store = MysqlModelCallStore(self.conn)
        tool_call_store = MysqlToolCallStore(self.conn)

        # ---- 2. Create Run ----
        run_id = run_store.create_run(
            agent_name="ReaderAgent",
            mode="answer",
            payload={
                "book_id": request.book_id,
                "question": request.question,
                "session_id": request.session_id,
                "options": request.options.model_dump(),
            },
        )

        # ---- 3. Create retrieval step ----
        step1_id = run_store.create_step(
            run_id,
            "EVIDENCE_SEARCH",
            payload={
                "query": request.question,
                "book_id": request.book_id,
                "top_k": request.options.top_k,
            },
            step_order=0,
        )

        # ---- 4. Create trace record ----
        trace_store = MysqlRetrievalTraceStore(self.conn)
        trace_id = trace_store.create_trace(
            run_id,
            query=request.question,
            payload={
                "book_id": request.book_id,
                "provider": request.options.provider,
                "require_citations": request.options.require_citations,
            },
        )

        # ---- 5. Record retrieval tool call ----
        retrieval_tool_call_id = None
        try:
            tool_call_store.create_tool_call(
                "hybrid_search",
                agent_run_id=run_id,
                agent_step_id=step1_id,
                input_json={
                    "query": request.question,
                    "book_id": request.book_id,
                    "top_k": request.options.top_k,
                },
                status="SUCCESS",
            )
        except Exception as e:
            logger.warning("Tool call (retrieval) persistence failed: %s", e)

        # ---- 6. Run QaRunner (core answer logic) ----
        runner = QaRunner(self.conn)
        try:
            result = await runner.answer(
                session_id=request.session_id or 0,
                book_id=request.book_id,
                question=request.question,
                use_deepseek=request.options.provider == "deepseek",
                agent_run_id=run_id,
                agent_step_id=step1_id,
                model_call_store=model_call_store,
                tool_call_store=tool_call_store,
            )
            answer_text = result.get("answer", "")
            raw_citations = result.get("citations", [])
        except Exception as e:
            logger.exception("QaRunner.answer failed")
            run_store.finish_step(
                step1_id, "FAILED",
                error_type=type(e).__name__, error_message=str(e),
            )
            run_store.finish_run(
                run_id, "FAILED",
                error_type=type(e).__name__, error_message=str(e),
            )
            return ReaderResponse(
                mode="answer", status=ReaderState.FAILED,
                errors=[f"QaRunner.answer failed: {e}"],
                run_id=run_id, trace_id=trace_id,
            )

        # ---- 6. Sync connection after potential LLM reconnect ----
        self.conn = runner.conn
        run_store = MysqlAgentRunStore(self.conn)
        trace_store = MysqlRetrievalTraceStore(self.conn)

        # ---- 7. Convert citations ----
        citations = [
            EvidenceItem(
                source_type=_SOURCE_MAP.get(c.get("source_type", ""), "chunk"),
                source_id=c.get("source_id", 0),
                chapter_id=c.get("chapter_id"),
                excerpt=c.get("excerpt", ""),
                evidence_level=_EVIDENCE_MAP.get(
                    c.get("evidence_level", ""), EvidenceLevel.NEAR
                ),
                relevance_score=c.get("relevance_score", 0.0),
            )
            for c in raw_citations
        ]

        # ---- 8. CitationVerifier check ----
        citation_result = CitationVerifier().verify(citations)
        verification_passed = citation_result.ok
        verification_errors = citation_result.errors

        # ---- 9. Add trace items (per citation, with protection) ----
        for i, cit in enumerate(raw_citations[:20]):
            try:
                trace_store.add_item(
                    trace_id,
                    {
                        "source_type": _SOURCE_MAP.get(cit.get("source_type", ""), "chunk"),
                        "source_id": cit.get("source_id", 0),
                        "chapter_id": cit.get("chapter_id", 0),
                        "evidence_level": _EVIDENCE_MAP.get(
                            cit.get("evidence_level", ""), EvidenceLevel.NEAR
                        ).value,
                        "rank": i,
                        "selected_for_answer": True,
                    },
                )
            except Exception as e:
                logger.warning("Failed to add trace item %d: %s", i, e)

        # ---- 10. Answer generation step ----
        step2_id = run_store.create_step(
            run_id, "DRAFT_READY",
            payload={
                "answer_length": len(answer_text),
                "citation_count": len(raw_citations),
                "provider": request.options.provider,
                "citation_verification_passed": verification_passed,
                "citation_verification_errors": verification_errors,
            },
            step_order=1,
        )
        run_store.finish_step(step2_id, "SUCCESS", payload={
            "answer_preview": answer_text[:200],
        })

        # ---- 11. Finish retrieval step ----
        run_store.finish_step(
            step1_id, "SUCCESS",
            payload={
                "citation_count": len(raw_citations),
                "citation_verification_passed": verification_passed,
            },
        )

        # ---- 12. Determine final status ----
        status = ReaderState.RESPONDED
        status_errors: list[str] = []

        if request.options.require_citations:
            if not citations:
                status = ReaderState.INSUFFICIENT_EVIDENCE
                status_errors.append("No citations returned by LLM")
            elif not verification_passed:
                status_errors.append(
                    f"Citation verification found {len(verification_errors)} issue(s)"
                )

        # ---- 13. Enrich: generate KnowledgePatch candidates (if enabled) ----
        patch_results: list[dict[str, Any]] = []
        if request.options.allow_patch:
            try:
                kp_store = MysqlKnowledgePatchStore(self.conn)
                kp_service = KnowledgePatchService(kp_store)
                candidates = _generate_enrich_patches(
                    request, answer_text, raw_citations,
                    verification_passed, verification_errors, run_id,
                )
                for cand in candidates:
                    try:
                        result = kp_service.propose(cand["candidate"])
                        patch_results.append({
                            "patch_type": cand["candidate"].patch_type.value,
                            "patch_id": result.get("patch_id"),
                            "status": result.get("status"),
                            "ok": result.get("ok", False),
                            "reason": cand["reason"],
                            "errors": result.get("errors", []),
                        })
                        if not result.get("ok"):
                            status_errors.append(
                                f"Patch propose failed ({cand['reason']}): "
                                f"{result.get('errors', 'unknown')}"
                            )
                    except Exception as e:
                        logger.warning("Patch propose exception: %s", e)
                        status_errors.append(f"Patch propose error: {e}")
            except Exception as e:
                logger.warning("Patch store init failed: %s", e)
                status_errors.append(f"Patch enrichment unavailable: {e}")
            if not citations:
                status = ReaderState.INSUFFICIENT_EVIDENCE
                status_errors.append("No citations returned by LLM")
            elif not verification_passed:
                status_errors.append(
                    f"Citation verification found {len(verification_errors)} issue(s)"
                )

        # ---- 14. Finish run ----
        run_store.finish_run(
            run_id, status.value,
            payload={
                "answer_length": len(answer_text),
                "citation_count": len(raw_citations),
                "citation_verification_passed": verification_passed,
                "citation_verification_errors": verification_errors,
                "trace_id": trace_id,
                "patch_count": len(patch_results),
                "model_calls_note": (
                    "ModelCall records are now written by ReaderAgent "
                    "(Stage 5A) via QaRunner.answer() tracking params. "
                    "Check model_calls list in trace endpoint."
                ),
            },
        )

        return ReaderResponse(
            run_id=run_id,
            mode="answer",
            status=status,
            answer=answer_text,
            citations=citations,
            evidence=citations,
            trace_id=trace_id,
            patches=patch_results,
            errors=status_errors,
        )
