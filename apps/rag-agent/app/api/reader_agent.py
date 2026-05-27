"""
ReaderAgent API 路由。支持：
- POST /api/reader-agent/plan  (determine mode/targets without execution)
- POST /api/reader-agent/run   (mode=answer/analyze/trace/enrich)
- GET  /api/reader-agent/runs/{run_id}/trace
"""
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from app.agent_runtime.model_call_store import MysqlModelCallStore
from app.agent_runtime.run_store import MysqlAgentRunStore
from app.agent_runtime.tool_call_store import MysqlToolCallStore
from app.agent_runtime.trace_store import MysqlRetrievalTraceStore
from app.clients.mysql_client import MysqlClient
from app.knowledge_patch.store import MysqlKnowledgePatchStore
from app.reader_agent.agent import ReaderAgent
from app.reader_agent.memory import MemoryManager
from app.reader_agent.planner import plan as reader_plan
from app.reader_agent.planner_deepseek import plan_with_deepseek
from app.reader_agent.schemas import PlanRequest, PlanResponse, ReaderRequest, ReaderResponse, SessionInfo, SessionTurnInfo
from app.reader_agent.states import ReaderState
from app.qa.intent_detector import detect as detect_intent
from app.qa.query_rewriter import RewriteRequest, RewriteResult, rewrite as rewrite_query
from app.reader_agent.project_store import get_store as get_project_store


# ── Active memory managers + persistence ────────────────────────────
_memory_managers: dict[int, MemoryManager] = {}
_memory_store: Any = None  # MemoryStore singleton, set by init_router
_save_interval: int = 60   # seconds between periodic auto-saves
_periodic_task: Any = None  # asyncio periodic timer handle


def _get_memory_manager(session_id: int | None) -> MemoryManager | None:
    """Get or create a MemoryManager for the given session_id.

    Auto-injects memory_store for persistence.
    """
    if session_id is None:
        return None
    if session_id not in _memory_managers:
        mm = MemoryManager(session_id=session_id, memory_store=_memory_store)
        _memory_managers[session_id] = mm
        # Try to restore persisted memory from MySQL
        if _memory_store is not None:
            try:
                data = _memory_store.load_session_memory(session_id)
                if data:
                    _restore_memory_from_data(mm, data)
            except Exception as e:
                logger.warning("Failed to load persisted memory for session %s: %s", session_id, e)
    return _memory_managers[session_id]


def _restore_memory_from_data(mm: MemoryManager, data: dict):
    """Restore L0 memory from a previously persisted dict."""
    from app.reader_agent.memory.session_memory import SessionTurn, UserPreferences
    for t in data.get("turns", []):
        turn = SessionTurn(
            mode=t.get("mode", ""),
            question=t.get("question", ""),
            optimized_question=t.get("optimized_question", t.get("question", "")),
            answer_preview=t.get("answer_preview", ""),
            target_name=t.get("target_name"),
            target_type=t.get("target_type"),
            book_id=t.get("book_id", 0),
            run_id=t.get("run_id", 0),
            evidence_ids=t.get("evidence_ids", []),
            provider=t.get("provider", "local"),
            timestamp=t.get("timestamp", 0),
        )
        mm.l0.record_turn(turn)
    prefs = data.get("preferences", {})
    if prefs:
        mm.l0.preferences = UserPreferences.from_dict(prefs)
    if data.get("current_target_name"):
        mm.l0._current_target_name = data["current_target_name"]
        mm.l0._current_target_type = data.get("current_target_type", "")


async def _periodic_save():
    """Background task: periodically persist all memory managers."""
    global _periodic_task
    while True:
        try:
            await asyncio.sleep(_save_interval)
            if _memory_store is not None and _memory_managers:
                _memory_store.save_all_memories(_memory_managers)
                logger.debug("Periodic memory save: %d managers", len(_memory_managers))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Periodic memory save failed: %s", e)


def _save_all_memories_sync():
    """Synchronously persist all memories (used on shutdown)."""
    if _memory_store is not None and _memory_managers:
        try:
            _memory_store.save_all_memories(_memory_managers)
            logger.info("Shutdown memory save: %d managers persisted", len(_memory_managers))
        except Exception as e:
            logger.warning("Shutdown memory save failed: %s", e)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reader-agent", tags=["reader-agent"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client, _memory_store
    db_client = db

    # Initialize MySQL-backed MemoryStore and inject into project_store
    from app.stores.memory_store import MemoryStore
    _memory_store = MemoryStore(db.connect())

    from app.reader_agent.project_store import init_store
    init_store(_memory_store)

    # Restore existing project/session metadata
    from app.reader_agent.project_store import get_store
    try:
        projects = get_store().list_projects()
        if not projects:
            # First run: create default project
            get_store().create_project("默认项目")
            logger.info("MemoryStore: created default project")
    except Exception as e:
        logger.warning("MemoryStore init: %s", e)


@router.post("/plan", response_model=PlanResponse)
async def reader_agent_plan(req: PlanRequest):
    """@NB-ENTRYPOINT Stage 6E/6F planner endpoint.

    Deterministic planner: infer mode, targets, rewrite question.
    No model calls, no database writes, no KnowledgePatch creation.
    Supports session-based follow-up reference resolution.
    Returns a request_patch the caller merges into /api/reader-agent/run.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=422, detail="question is required")
    try:
        session = None
        session_summary = None
        if req.session_id:
            mm = _get_memory_manager(req.session_id)
            if mm and not mm.l0.empty():
                session = mm.l0
                session_summary = mm.l0.get_context_summary()

        # Route to model-based or deterministic planner
        if req.model_mode == "deepseek":
            result = await plan_with_deepseek(
                book_id=req.book_id,
                question=req.question.strip(),
                preferred_mode=req.preferred_mode,
                session_summary=session_summary,
            )
            if result is not None:
                return result
            # Fall through to deterministic on failure

        return reader_plan(
            book_id=req.book_id,
            question=req.question.strip(),
            preferred_mode=req.preferred_mode,
            session=session,
        )
    except Exception as e:
        logger.exception("ReaderAgent plan failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=ReaderResponse)
async def reader_agent_run(req: ReaderRequest):
    """ReaderAgent 入口。P3: answer mode 走 unified_pipeline；其他 mode 走现有 ReaderAgent。"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    if req.mode not in {"answer", "analyze", "trace", "enrich"}:
        return ReaderResponse(
            mode=req.mode,
            status=ReaderState.NEED_FOLLOWUP,
            errors=[f"ReaderAgent mode is not implemented yet: {req.mode}"],
        )

    conn = db_client.connect()

    # ── Build memory_manager BEFORE intent detection (gives context) ─
    memory_manager = _get_memory_manager(req.session_id)
    session_context = None
    if req.session_id:
        project_store = get_project_store()
        session_meta = project_store.get_session(req.session_id)
        if session_meta:
            project_store.touch_session(req.session_id)
            session_name = session_meta.get("name", "")
            if session_name.startswith("会话 ") and req.question:
                project_store.rename_session(req.session_id, req.question[:30])
        # Build session context from MemoryManager L0
        if memory_manager and memory_manager.l0.turns:
            last_turns = memory_manager.l0.turns[-3:]
            parts = []
            for t in last_turns:
                parts.append(f"用户: {t.question[:60]}")
                if t.answer_preview:
                    parts.append(f"助手: {t.answer_preview[:80]}")
            session_context = "\n".join(parts)

    # ── Intent detection with session context ─────────────────────────
    intent, chat_response = await detect_intent(
        req.question,
        book_id=req.book_id,
        provider=req.options.provider,
        session_context=session_context,
    )
    if intent != "book_qa":
        if chat_response:
            # Record this turn in memory even for chat responses
            if memory_manager and req.question:
                try:
                    from app.reader_agent.memory.session_memory import SessionTurn
                    memory_manager.l0.record_turn(SessionTurn(
                        mode="chat",
                        question=req.question,
                        optimized_question=req.question,
                        answer_preview=chat_response[:200],
                        target_name="",
                        target_type="",
                        book_id=req.book_id,
                        run_id=0,
                        evidence_ids=[],
                        provider=req.options.provider,
                    ))
                except Exception:
                    pass
            return ReaderResponse(
                mode="answer",
                status=ReaderState.RESPONDED,
                answer=chat_response,
            )

    # P3: answer mode → unified pipeline (with MemoryManager)
    if req.mode == "answer":
        try:
            book_title = _get_book_title(conn, req.book_id)
            from app.qa.unified_pipeline import run_pipeline
            result = await run_pipeline(
                question=req.question,
                book_id=req.book_id,
                book_title=book_title,
                session_id=req.session_id or 0,
                provider=req.options.provider,
                entity_name=req.target_name,
                top_k=req.options.top_k,
                conn=conn,
                memory_manager=memory_manager,
            )
            return ReaderResponse(
                mode="answer",
                status=ReaderState.RESPONDED if result["answer"] else ReaderState.INSUFFICIENT_EVIDENCE,
                answer=result.get("answer", ""),
                citations=result.get("citations", []),
                evidence=result.get("citations", []),
                run_id=result.get("run_id"),
            )
        except Exception as e:
            logger.exception("Unified pipeline failed, falling back to ReaderAgent")
            # Fall through to existing ReaderAgent

    agent = ReaderAgent(conn, memory_manager=memory_manager)
    response = await agent.run(req, tool_sequence=req.tool_sequence)
    return response


@router.post("/rephrase")
async def rephrase_question(req: PlanRequest):
    """P3: Debug endpoint — only rewrite, no retrieval or generation."""
    result = await rewrite_query(RewriteRequest(
        question=req.question,
        book_id=req.book_id,
        entities=[],
    ))
    return {"original": req.question, "rewritten": result.rewritten_query, "intent": result.intent, "strategy": result.strategy}


def _get_book_title(conn, book_id: int) -> str:
    """Get book title from DB."""
    _names = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}
    if book_id in _names:
        return _names[book_id]
    try:
        with conn.cursor() as c:
            c.execute("SELECT title FROM novel_book WHERE id = %s", (book_id,))
            row = c.fetchone()
            return str(row["title"]) if row else f"Book {book_id}"
    except Exception:
        return f"Book {book_id}"


def _safe_query(fn, default, field_name: str, warnings: list[str]):
    """Execute fn, return default on failure and append to warnings."""
    try:
        return fn()
    except Exception as e:
        msg = f"Failed to query {field_name}: {e}"
        logger.warning(msg)
        warnings.append(msg)
        return default


@router.get("/sessions")
async def list_agent_sessions():
    """List active sessions (from MemoryManager, for Trace Inspector)."""
    sessions = []
    for sid, mm in _memory_managers.items():
        lt = mm.l0.last_turn
        sessions.append({
            "session_id": sid,
            "book_id": mm.l0.book_id,
            "turn_count": mm.l0.turn_count,
            "last_question": lt.question if lt else None,
            "last_mode": lt.mode if lt else None,
            "current_target": mm.l0.current_target_name,
        })
    return sessions


@router.get("/sessions/{session_id}")
async def get_agent_session(session_id: int):
    """Get session details with turn history (from MemoryManager)."""
    mm = _memory_managers.get(session_id)
    if mm is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return SessionInfo(
        session_id=session_id,
        book_id=mm.l0.book_id,
        turn_count=mm.l0.turn_count,
        turns=[
            SessionTurnInfo(
                mode=t.mode,
                question=t.question,
                answer_preview=t.answer_preview,
                target_name=t.target_name,
                target_type=t.target_type,
                book_id=t.book_id,
                run_id=t.run_id,
                evidence_count=len(t.evidence_ids),
            )
            for t in mm.l0.turns[-10:]
        ],
        current_target_name=mm.l0.current_target_name,
        current_target_type=mm.l0.current_target_type,
        last_run_id=mm.l0.last_turn.run_id if mm.l0.last_turn else None,
        context_summary=mm.l0.get_context_summary(),
    )


# ═══════════════════════════════════════════════════════════════════
# Project + Session API
# ═══════════════════════════════════════════════════════════════════


@router.get("/projects")
async def list_projects():
    """List all projects with their sessions."""
    store = get_project_store()
    projects = store.list_projects()
    result = []
    for p in projects:
        sessions = store.list_sessions(p["id"])
        result.append({
            "id": p["id"],
            "name": p["name"],
            "sessions": [{"id": s["id"], "name": s["name"], "created_at": s.get("created_at")} for s in sessions],
        })
    return result


@router.post("/projects")
async def create_project(name: str = "新项目"):
    """Create a new project."""
    store = get_project_store()
    p = store.create_project(name=name)
    # Auto-create first session
    s = store.create_session(project_id=p["id"], name="会话 1")
    return {"project": {"id": p["id"], "name": p["name"]}, "session": {"id": s["id"], "name": s["name"]}}


@router.put("/projects/{project_id}")
async def rename_project(project_id: int, name: str):
    """Rename a project."""
    ok = get_project_store().rename_project(project_id, name)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project and all its sessions."""
    ok = get_project_store().delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found or cannot delete default")
    return {"ok": True}


@router.post("/projects/{project_id}/sessions")
async def create_session(project_id: int, name: str = "新会话"):
    """Create a new session in a project."""
    s = get_project_store().create_session(project_id=project_id, name=name)
    return {"id": s["id"], "name": s["name"]}


@router.put("/sessions/{session_id}")
async def rename_session(session_id: int, name: str):
    """Rename a session."""
    ok = get_project_store().rename_session(session_id, name)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    """Delete a session."""
    # Also remove from memory if present
    _memory_managers.pop(session_id, None)
    ok = get_project_store().delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/runs")
async def list_agent_runs(
    run_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """列出 Agent runs，可选按 run_type 前缀过滤 (ReaderAgent/PreprocessAgent)."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    run_store = MysqlAgentRunStore(conn)
    return run_store.get_runs(run_type_prefix=run_type, limit=limit, offset=offset)


@router.get("/runs/{run_id}/trace")
async def get_run_trace(run_id: int):
    """返回指定 run 的完整执行轨迹：run + steps + model_calls + tool_calls + retrieval_traces + patches."""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    run_store = MysqlAgentRunStore(conn)
    trace_store = MysqlRetrievalTraceStore(conn, auto_create=False)
    model_store = MysqlModelCallStore(conn)
    tool_store = MysqlToolCallStore(conn, auto_create=True)
    patch_store = MysqlKnowledgePatchStore(conn, auto_create=True)

    run_data = run_store.get_run(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    warnings: list[str] = []

    # Each query is individually guarded — a single store failure won't 500
    steps: list[dict[str, Any]] = _safe_query(
        lambda: run_store.get_steps(run_id), [], "steps", warnings
    )
    model_calls: list[dict[str, Any]] = _safe_query(
        lambda: model_store.get_model_calls_for_run(run_id), [], "model_calls", warnings
    )
    tool_calls: list[dict[str, Any]] = _safe_query(
        lambda: tool_store.get_tool_calls_for_run(run_id), [], "tool_calls", warnings
    )
    retrieval_traces: list[dict[str, Any]] = _safe_query(
        lambda: trace_store.get_traces_for_run(run_id), [], "retrieval_traces", warnings
    )
    patches: list[dict[str, Any]] = _safe_query(
        lambda: patch_store.list_patches(run_id=run_id), [], "patches", warnings
    )

    # Extract citations from retrieval_traces items where selected_for_answer=true
    citations: list[dict[str, Any]] = []
    for tr in retrieval_traces:
        items = tr.get("items_json")
        if isinstance(items, list):
            for item in items:
                if item.get("selected_for_answer"):
                    citations.append(item)

    # If model_calls is empty, explain why in warnings (not an error)
    model_calls_note = (run_data.get("output_json") or {}).get("model_calls_note")
    if not model_calls and model_calls_note:
        pass
    elif not model_calls:
        warnings.append(
            "model_calls is empty: ReaderAgent answer uses QaRunner internally, "
            "which writes model calls under a separate pipeline run_id."
        )

    return {
        "run": run_data,
        "steps": steps,
        "model_calls": model_calls,
        "tool_calls": tool_calls,
        "retrieval_traces": retrieval_traces,
        "patches": patches,
        "citations": citations,
        "warnings": warnings,
    }
