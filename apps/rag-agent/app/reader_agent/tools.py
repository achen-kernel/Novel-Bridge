"""@NB-ENTRYPOINT ReaderAgent tool definitions for ToolRegistry.

Each tool wraps a mode runner or a data access function.
Tools are registered with ToolRegistry and executed by ToolExecutor.

Usage:
    from app.reader_agent.tools import register_all_tools
    registry = ToolRegistry()
    register_all_tools(registry, conn=db_connection)
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent_runtime.schemas import EvidenceItem
from app.agent_runtime.tool_registry import ToolRegistry
from app.reader_agent.answer_polish import audit, polish
from app.reader_agent.modes.analyze import AnalyzeMode
from app.reader_agent.modes.answer import AnswerMode
from app.reader_agent.modes.enrich import EnrichMode
from app.reader_agent.modes.trace import TraceMode
from app.reader_agent.schemas import ReaderRequest, ReaderResponse

logger = logging.getLogger(__name__)


def register_all_tools(registry: ToolRegistry, conn=None) -> None:
    """Register all ReaderAgent tools into the given registry.

    Args:
        registry: ToolRegistry instance.
        conn: MySQL connection (optional — tools that need DB will fail gracefully).
    """
    _tools = _build_tools(conn)
    for name, fn in _tools.items():
        registry.register(name, fn)


def _build_tools(conn) -> dict[str, Any]:
    """Build all tool callables. Internal factory."""
    return {
        # ── Core execution tools ────────────────────────────────────
        "answer": _make_mode_runner(AnswerMode, conn, "answer"),
        "analyze": _make_mode_runner(AnalyzeMode, conn, "analyze"),
        "trace": _make_mode_runner(TraceMode, conn, "trace"),
        "enrich": _make_mode_runner(EnrichMode, conn, "enrich"),
        # ── Data tools ──────────────────────────────────────────────
        "hybrid_search": _make_hybrid_search(conn),
        # ── Post-process tools ──────────────────────────────────────
        "audit": _make_audit(),
    }


# ── Tool factories ────────────────────────────────────────────────────


def _make_mode_runner(mode_class: type, conn, mode_name: str):
    """Wrap a mode runner class into a callable tool."""

    async def run(**params) -> dict[str, Any]:
        try:
            # Build ReaderRequest from params
            request = _params_to_request(mode_name, params)
            instance = mode_class(conn)
            response: ReaderResponse = await instance.run(request)

            # Post-process: polish + audit
            if response.answer:
                response.answer = polish(response.answer, provider=params.get("provider", "local"))
                audit_result = audit(response.answer)
                if audit_result.warnings:
                    response.errors = (response.errors or []) + [
                        f"[tool audit] {w}" for w in audit_result.warnings
                    ]

            return {
                "run_id": response.run_id,
                "status": response.status.value if hasattr(response.status, "value") else str(response.status),
                "answer": response.answer,
                "citations": [c.model_dump() if hasattr(c, "model_dump") else c for c in (response.citations or [])],
                "evidence": [e.model_dump() if hasattr(e, "model_dump") else e for e in (response.evidence or [])],
                "trace_id": response.trace_id,
                "analysis": response.analysis,
                "timeline": response.timeline,
                "errors": response.errors,
            }
        except Exception as e:
            logger.exception("Tool %s failed", mode_name)
            return {"status": "FAILED", "errors": [str(e)]}

    run.__name__ = mode_name
    run.__doc__ = {
        "answer": "基于检索证据回答问题，返回带引用的自然语言回答",
        "analyze": "结构化分析人物或关系，返回 summary + key_points + limitations",
        "trace": "跨章节追踪目标的变化，返回 timeline items",
        "enrich": "生成 KnowledgePatch candidate，不自动合并",
    }.get(mode_name, f"执行 {mode_name}")
    return run


def _params_to_request(mode: str, params: dict[str, Any]) -> ReaderRequest:
    """Convert tool params dict into a ReaderRequest."""
    from app.reader_agent.schemas import ReaderRequest, ReaderOptions

    return ReaderRequest(
        mode=mode,  # type: ignore
        book_id=int(params.get("book_id", 0)),
        question=str(params.get("question", "")),
        target_name=str(params.get("target_name")) if params.get("target_name") else None,
        target_type=str(params.get("target_type")) if params.get("target_type") else None,
        analysis_type=str(params.get("analysis_type")) if params.get("analysis_type") else None,
        trace_target_type=str(params.get("trace_target_type")) if params.get("trace_target_type") else None,
        options=ReaderOptions(
            provider=str(params.get("provider", "local")),
            top_k=int(params.get("top_k", 12)),
        ),
    )


def _make_hybrid_search(conn):
    """Wrap RetrievalRunner into a tool."""

    async def hybrid_search(**params) -> dict[str, Any]:
        try:
            from app.qa.retrieval_runner import RetrievalRunner

            if conn is None:
                return {"status": "FAILED", "errors": ["No database connection"]}

            query = str(params.get("query", ""))
            book_id = int(params.get("book_id", 0))
            top_k = min(int(params.get("top_k", 12)), 20)
            entity_name = str(params.get("entity_name", "") or None) or None

            runner = RetrievalRunner(conn)
            results = await runner.hybrid_search(query, book_id, top_k=top_k, entity_name=entity_name)

            items = []
            for r in results[:top_k]:
                items.append({
                    "source": r.get("source", "chunk"),
                    "id": r.get("id"),
                    "score": r.get("score"),
                    "excerpt": str(r.get("content") or r.get("excerpt") or "")[:300],
                    "chapter_id": r.get("metadata", {}).get("chapter_id") if isinstance(r.get("metadata"), dict) else None,
                })

            return {"status": "SUCCESS", "items": items, "count": len(items)}
        except Exception as e:
            logger.exception("hybrid_search failed")
            return {"status": "FAILED", "errors": [str(e)]}

    hybrid_search.__name__ = "hybrid_search"
    hybrid_search.__doc__ = "混合检索：lexical + dense Qdrant + ChapterFact fusion"
    return hybrid_search


def _make_audit():
    """Answer audit tool — post-processes already-generated answer."""

    async def audit_tool(**params) -> dict[str, Any]:
        answer = str(params.get("answer", "") or "")
        provider = str(params.get("provider", "local"))
        if not answer:
            return {"status": "SUCCESS", "warnings": [], "polished": ""}

        polished = polish(answer, provider=provider)
        audit_result = audit(polished)

        return {
            "status": "SUCCESS",
            "polished": polished,
            "warnings": audit_result.warnings,
            "has_broad_claims": audit_result.has_broad_claims,
            "has_repetition": audit_result.has_repetition,
            "has_punctuation_issues": audit_result.has_punctuation_issues,
        }

    audit_tool.__name__ = "audit"
    audit_tool.__doc__ = "检查答案格式和潜在问题：清理标点、检测 broad claim 和重复"
    return audit_tool
