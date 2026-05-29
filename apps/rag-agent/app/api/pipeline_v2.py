"""
Pipeline v2 API — background tasks, progress tracking, stage/checkpoint/queue.

Architecture layers (bottom-up):
  Phase 0: pipeline_state.py      — BookPipelineState + P3Checkpoint store
  Phase 1: fact_pipeline_runner.py — checkpoint-aware P3 with resume + cancel
  Phase 2: pipeline_v2.py          — stage gate, force override, stage-level cleanup
  Phase 3: scheduler.py            — queue + batch pipelined execution
  Phase 4: pipeline.js/html         — three-stage UI + queue panel
  Phase 5: extraction_strategy.py   — abstraction for future API mode

Stages:
  Stage 1 = P1 (分章+分块) + P2 (梗概) — fast, ~1min
  Stage 2 = P3 (提取)                 — slow, ~2-4h per 100-ch book
  Stage 3 = P4-P8 (治理/叙事/索引/图谱/导出) — fast, ~5min
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.clients.neo4j_client import neo4j_client
from app.pipeline.errors import PipelineError, db_error, model_error, not_found_error, phase_failed_error
from app.pipeline.pipeline_state import get_state_store, PipelineStateStore, StageStatus
from app.pipeline.task_manager import TaskStatus, task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["pipeline-v2"])

db_client: Optional[MysqlClient] = None
_state_store: Optional[PipelineStateStore] = None


def init_router(db: MysqlClient):
    global db_client, _state_store
    db_client = db
    _state_store = get_state_store()


def state_store() -> PipelineStateStore:
    global _state_store
    if _state_store is None:
        _state_store = get_state_store()
    return _state_store


def _make_thread_db() -> MysqlClient:
    """Create a MysqlClient with an independent connection for thread pool use.
    
    Thread pool tasks MUST use a separate connection to avoid packet sequence conflicts
    with the main event loop's shared connection.
    """
    new_client = MysqlClient()
    new_client.connection = db_client.new_connection()
    return new_client


# ── Models ──

class PhaseTriggerRequest(BaseModel):
    use_model: bool = True          # default True: model extraction primary
    provider: str = "local"          # "local" (9B llama) or "deepseek"


class PhaseTriggerResponse(BaseModel):
    status: str
    task_id: str = ""
    message: str = ""


class CleanupResponse(BaseModel):
    status: str
    message: str = ""


# ── Helper: get a fresh MySQL connection (caller should NOT close it) ──

def _conn():
    return db_client.connect()


# ── Phase implementations ──

async def _run_p1(book_id: int, task_id: str, **_):
    """Split chapters + chunking. Validates output."""
    from app.pipeline.book_processor import BookProcessor
    state_store().update_stage(book_id, 1, 'RUNNING')
    task_manager.update_progress(task_id, 10, "正在拆分章节...")
    try:
        result = BookProcessor(db_client).process(book_id, 0)
        chapters = result.get('chapters', 0)
        chunks = result.get('chunks', 0)
        if chapters == 0:
            state_store().update_stage(book_id, 1, 'FAILED')
            raise phase_failed_error("P1", book_id,
                                     f"P1 产生 0 章节 — 请检查书籍 raw_text 是否存在",
                                     {"raw_text": result.get('char_count', 0),
                                      "book_result": result.get('status', 'unknown')})
        state_store().update_stage(book_id, 1, 'SUCCESS')
        task_manager.update_progress(task_id, 100, f"拆分完成: {chapters}章 {chunks}块")
        return result
    except PipelineError:
        raise  # re-raise structured errors (already handled)
    except Exception as e:
        state_store().update_stage(book_id, 1, 'FAILED')
        raise


async def _run_p2(book_id: int, task_id: str, **_):
    """Prior hint via DeepSeek API (梗概需要大上下文+高质量，强制 DeepSeek)."""
    import os
    from app.clients.model_client import ModelClient

    state_store().update_stage(book_id, 1, 'RUNNING')
    task_manager.update_progress(task_id, 10, "正在获取 DeepSeek 梗概...")
    conn = _conn()
    with conn.cursor() as c:
        c.execute("SELECT id, title, raw_text FROM novel_book WHERE id = %s", (book_id,))
        book = c.fetchone()
        if not book:
            raise not_found_error("P2", book_id, f"Book {book_id} not found")
        book_title = book["title"]
        raw_text = book["raw_text"]

    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "book_prior_hint.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    hint_text = raw_text[:12000] if len(raw_text) > 12000 else raw_text
    prompt = prompt_template.replace("{book_title}", book_title).replace("{raw_text}", hint_text)

    client = ModelClient(provider="deepseek")
    result = await client.chat_json([
        {"role": "system", "content": "你是古典小说分析专家。"},
        {"role": "user", "content": prompt},
    ])
    prior_hint_dict = result if isinstance(result, dict) else {"raw": result}

    with conn.cursor() as c:
        c.execute("UPDATE novel_book SET prior_hint_json = %s WHERE id = %s",
                  (json.dumps(prior_hint_dict, ensure_ascii=False), book_id))
    conn.commit()

    state_store().update_stage(book_id, 1, 'SUCCESS')
    task_manager.update_progress(task_id, 100, "prior_hint 完成")
    return {"status": "success", "book_id": book_id, "prior_hint_keys": list(prior_hint_dict.keys())}


async def _run_p3(book_id: int, task_id: str, use_model: bool = True, provider: str = "local"):
    """Extract chapter facts (checkpoint-aware, supports cancel).

    Supports provider="local" (llama-server 9B) or "deepseek" (DeepSeek API).
    When use_model=False, falls back to rule-based extraction.
    """
    from app.pipeline.fact_pipeline_runner import FactPipelineRunner
    from app.stores.chapter_store import ChapterStore

    task_manager.update_progress(task_id, 1, "初始化提取...")
    conn = _conn()
    chapter_store = ChapterStore(conn)
    chapters = chapter_store.get_chapters_by_book(book_id)
    total = len(chapters)

    if total == 0:
        raise phase_failed_error("P3", book_id,
                                 f"P3 发现 0 章节 — 请先运行 P1 分章",
                                 {"book_id": book_id})

    runner = FactPipelineRunner(db_client, use_model=use_model, provider=provider)
    task_manager.update_progress(task_id, 2, f"共 {total} 章，开始提取...")

    # Wire up cancel event
    cancel_event = _get_cancel_event(book_id, "P3")
    if cancel_event is None:
        cancel_event = asyncio.Event()
        _store_cancel_event(book_id, "P3", cancel_event)

    result = await runner.process_book(book_id, cancel_event=cancel_event)

    # BUG FIX: DictCursor returns dict, not tuple. Use COUNT(*) key.
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM novel_chapter_fact WHERE book_id = %s", (book_id,))
        row = c.fetchone()
        done = row["cnt"] if row else 0

    pct = min(100, done * 100 / max(total, 1))
    task_manager.update_progress(task_id, pct, f"提取完成: {done}/{total} 章")
    return result


async def _run_p4(book_id: int, task_id: str, **_):
    """Entity governance.
    
    NOTE: runs in thread pool with independent DB connection.
    """
    import asyncio
    from app.pipeline.entity_governance_runner import EntityGovernanceRunner

    state_store().update_stage(book_id, 3, 'RUNNING')
    task_manager.update_progress(task_id, 10, "实体治理中...")
    thread_db = _make_thread_db()
    try:
        runner = EntityGovernanceRunner(thread_db)
        result = await asyncio.to_thread(runner.process_book, book_id)
    finally:
        thread_db.close()
    profiles = result.get("profiles", 0)
    decisions = result.get("decisions", 0)
    task_manager.update_progress(task_id, 100, f"治理完成: {profiles} 画像, {decisions} 别名决策")
    state_store().update_stage(book_id, 3, 'SUCCESS')
    return result


async def _run_p5(book_id: int, task_id: str, **_):
    """Narrative build."""
    import asyncio
    from app.pipeline.narrative_builder import NarrativeBuilder

    state_store().update_stage(book_id, 3, 'RUNNING')
    task_manager.update_progress(task_id, 10, "叙事构建中...")
    thread_db = _make_thread_db()
    try:
        builder = NarrativeBuilder(thread_db)
        result = await asyncio.to_thread(builder.build_from_book, book_id)
    finally:
        thread_db.close()
    task_manager.update_progress(task_id, 100, "叙事构建完成")
    state_store().update_stage(book_id, 3, 'SUCCESS')
    return result


async def _run_p6(book_id: int, task_id: str, **_):
    """Index to Qdrant."""
    from app.pipeline.index_runner import IndexRunner

    state_store().update_stage(book_id, 3, 'RUNNING')
    task_manager.update_progress(task_id, 10, "索引到 Qdrant...")
    result = await IndexRunner(db_client).index_book(book_id, reindex=True)
    chunks = result.get("chunks_indexed", 0)
    facts = result.get("facts_indexed", 0)
    task_manager.update_progress(task_id, 100, f"索引完成: {chunks} chunks, {facts} facts")
    state_store().update_stage(book_id, 3, 'SUCCESS')
    return result


async def _run_p7(book_id: int, task_id: str, **_):
    """Project to Neo4j."""
    import asyncio
    from app.pipeline.graph_projector import GraphProjector

    state_store().update_stage(book_id, 3, 'RUNNING')
    task_manager.update_progress(task_id, 10, "投影到 Neo4j...")
    thread_db = _make_thread_db()
    try:
        conn = thread_db.new_connection()
        projector = GraphProjector(conn)
        result = await asyncio.to_thread(projector.project_book, book_id, True)
        conn.close()
    finally:
        thread_db.close()
    task_manager.update_progress(task_id, 100, f"投影完成: {result.get('entities', 0)} 实体, {result.get('relations', 0)} 关系")
    state_store().update_stage(book_id, 3, 'SUCCESS')
    return result


async def _run_p8(book_id: int, task_id: str, **_):
    """Export training data."""
    import asyncio
    from app.stores.chapter_fact_store import ChapterFactStore
    from datetime import datetime

    state_store().update_stage(book_id, 3, 'RUNNING')
    task_manager.update_progress(task_id, 10, "导出训练数据...")
    thread_db = _make_thread_db()
    conn = None
    try:
        conn = thread_db.new_connection()
        store = ChapterFactStore(conn)
        facts = store.find_by_book(book_id)

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (datetime,)):
                    return o.isoformat()
                return super().default(o)

        task_manager.update_progress(task_id, 50, f"写入 {len(facts)} 条 facts...")
        output_path = f"training/data/chapter_facts_book_{book_id}.jsonl"
        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        def _export():
            with open(output_path, "w", encoding="utf-8") as f:
                for fact in facts:
                    f.write(json.dumps(fact, ensure_ascii=False, cls=DateTimeEncoder) + "\n")
            return len(facts)

        count = await asyncio.to_thread(_export)
        task_manager.update_progress(task_id, 100, f"导出完成: {count} 条 -> {output_path}")
        state_store().update_stage(book_id, 3, 'SUCCESS')
        return {"status": "success", "exported": count, "path": output_path}
    finally:
        if conn:
            try: conn.close()
            except: pass
        try: thread_db.close()
        except: pass


# ── Phase registry ──

PHASE_RUNNERS = {
    "P1": _run_p1, "P2": _run_p2, "P3": _run_p3, "P4": _run_p4,
    "P5": _run_p5, "P6": _run_p6, "P7": _run_p7, "P8": _run_p8,
}

PHASE_LABELS = {
    "P1": "分章+分块", "P2": "梗概", "P3": "提取",
    "P4": "治理", "P5": "叙事", "P6": "索引",
    "P7": "图谱", "P8": "导出",
}


# ── Endpoints ──

@router.post("/books/{book_id}/phase/{phase}", response_model=PhaseTriggerResponse)
async def trigger_phase(book_id: int, phase: str, req: PhaseTriggerRequest = None):
    """Trigger a pipeline phase as background task. Returns immediately with task_id."""
    phase = phase.upper()
    if phase not in PHASE_RUNNERS:
        raise HTTPException(400, f"Unknown phase: {phase}. Valid: {', '.join(PHASE_RUNNERS.keys())}")

    if req is None:
        req = PhaseTriggerRequest()

    use_model = req.use_model
    provider = req.provider
    runner = PHASE_RUNNERS[phase]
    label = f"{PHASE_LABELS.get(phase, phase)}-B{book_id}"

    task = task_manager.create(book_id, phase, label)
    logger.info(f"Triggering {label} use_model={use_model} provider={provider} (task={task.task_id})")

    # Create cancel event for this phase
    cancel_event = asyncio.Event()
    _store_cancel_event(book_id, phase, cancel_event)

    coro = runner(book_id=book_id, task_id=task.task_id,
                  use_model=use_model, provider=provider)
    task_manager.launch(task, coro)

    return PhaseTriggerResponse(status="started", task_id=task.task_id,
                                message=f"{label} 已启动")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return task.to_dict()


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(400, f"Task {task_id} is not running (status={task.status.value})")
    task_manager.cancel(task_id)
    logger.info(f"Task cancelled: {task_id}")
    return {"status": "cancelled", "task_id": task_id}


@router.get("/books/{book_id}/tasks")
async def list_book_tasks(book_id: int, phase: str = None):
    tasks = task_manager.list_by_book(book_id, phase=phase)
    return {"book_id": book_id, "tasks": [t.to_dict() for t in tasks]}


@router.delete("/books/{book_id}/tasks")
async def clear_book_tasks(book_id: int):
    """清除某本书的所有 pipeline 任务（用于全流程开始时重置状态）。"""
    task_manager.clear_by_book(book_id)
    # 同时清理 MySQL 中的持久化任务
    try:
        conn = _conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM novel_pipeline_task WHERE book_id = %s", (book_id,))
        conn.commit()
    except Exception:
        pass
    return {"status": "ok", "book_id": book_id}


@router.get("/pipeline/books")
async def get_pipeline_books():
    """Get all books with latest task status for each phase."""
    conn = _conn()
    with conn.cursor() as c:
        c.execute("SELECT id, title, author, status, chapter_count, chunk_count, char_count FROM novel_book ORDER BY id")
        books = c.fetchall()

    result = []
    for b in books:
        bid = b["id"]
        # 检测该书是否有正在运行的任务（流水线活动中）
        has_running = any(
            t.status == TaskStatus.RUNNING
            for phase_name in PHASE_RUNNERS
            for t in task_manager.list_by_book(bid, phase=phase_name)
        )
        phases = {}
        for phase_name in PHASE_RUNNERS:
            tasks_list = task_manager.list_by_book(bid, phase=phase_name)
            if tasks_list:
                latest = tasks_list[0]
                # 如果该书有任务正在运行，且该阶段不是当前运行阶段，
                # 并且最新任务不是 RUNNING 状态 → 视为旧任务，显示 PENDING
                if has_running and latest.status != TaskStatus.RUNNING:
                    phases[phase_name] = {"latest_status": "PENDING", "latest_progress": 0,
                                           "latest_task_id": "", "latest_error": ""}
                else:
                    phases[phase_name] = {
                        "latest_status": latest.status.value,
                        "latest_progress": latest.progress,
                        "latest_task_id": latest.task_id,
                        "latest_error": latest.error[:200] if latest.error else "",
                        "tasks": [t.to_dict() for t in tasks_list[:3]],
                    }
            else:
                phases[phase_name] = {"latest_status": "PENDING", "latest_progress": 0,
                                       "latest_task_id": "", "latest_error": ""}

        # 添加 stage-level 状态（来自 pipeline_state）
        stage_state = state_store().get_state(bid)
        stage2_cp = state_store().get_checkpoint_summary(bid)
        result.append({
            "id": bid,
            "title": b["title"],
            "author": b["author"] or "",
            "status": b["status"],
            "chapter_count": b["chapter_count"],
            "chunk_count": b["chunk_count"],
            "char_count": b["char_count"],
            "phases": phases,
            "pipeline_state": {
                "stage1": {"status": stage_state.stage1_status},
                "stage2": {"status": stage_state.stage2_status,
                           "detail": stage_state.stage2_detail,
                           "checkpoint_summary": stage2_cp},
                "stage3": {"status": stage_state.stage3_status,
                           "force_override": stage_state.stage3_force_override},
            },
        })

    return {"books": result}


# ── Phase 1+2: Book Pipeline State + Stage 2 Checkpoint ──


@router.get("/books/{book_id}/pipeline-state")
async def get_book_pipeline_state(book_id: int):
    """Get three-stage pipeline state for a book."""
    st = state_store().get_state(book_id)
    return st.to_dict()


@router.post("/books/{book_id}/stage3/force")
async def force_stage3(book_id: int, override: bool = True):
    """Override Stage 3 gate: allow Stage 3 even if Stage 2 has errors."""
    state_store().set_stage3_override(book_id, override)
    # If override is false and status was FAILED, reset to PENDING
    if not override:
        st = state_store().get_state(book_id)
        if st.stage3_status in ('FAILED', 'COMPLETED_WITH_ERRORS'):
            state_store().update_stage(book_id, 3, 'PENDING')
    return {"status": "ok", "book_id": book_id, "stage3_force_override": override}


@router.post("/books/{book_id}/pipeline-state/reset")
async def reset_pipeline_state(book_id: int, stage: int = 0):
    """Reset pipeline state for a book. stage=0 resets all, 1/2/3 resets specific."""
    store = state_store()
    if stage == 0 or stage == 1:
        store.update_stage(book_id, 1, 'PENDING')
    if stage == 0 or stage == 2:
        store.update_stage(book_id, 2, 'PENDING')
        store.clear_checkpoints(book_id)
    if stage == 0 or stage == 3:
        store.update_stage(book_id, 3, 'PENDING')
        store.set_stage3_override(book_id, False)
    return {"status": "ok", "book_id": book_id, "stage": stage}


# ── Stage 2 Checkpoint (P3 detail) ──


@router.get("/books/{book_id}/stage2/checkpoint")
async def get_stage2_checkpoint(book_id: int):
    """Get per-chapter checkpoint status for Stage 2."""
    store = state_store()
    checkpoints = store.get_all_checkpoints(book_id)
    summary = store.get_checkpoint_summary(book_id)
    state = store.get_state(book_id)
    return {
        "book_id": book_id,
        "stage2_status": state.stage2_status,
        "stage2_detail": state.stage2_detail,
        "summary": summary,
        "chapters": [cp.to_dict() for cp in checkpoints],
        "permanent_failed": [cp.to_dict() for cp in store.get_failed_chapters(book_id)],
    }


@router.post("/books/{book_id}/stage2/resume")
async def resume_stage2(book_id: int):
    """Resume Stage 2: only process PENDING + FAILED (retry<5) chapters."""
    from app.pipeline.fact_pipeline_runner import FactPipelineRunner

    label = f"提取续跑-B{book_id}"
    task = task_manager.create(book_id, "P3", label)
    cancel_event = asyncio.Event()

    runner = FactPipelineRunner(db_client, use_model=True, provider="local")

    async def _run():
        try:
            state_store().update_stage(book_id, 2, 'RUNNING')
            result = await runner.resume_book(book_id, cancel_event=cancel_event)
            task_manager.complete(task.task_id, result)
        except Exception as e:
            task_manager.fail(task.task_id, f"{type(e).__name__}: {e}")
            logger.exception(f"Stage 2 resume failed for book {book_id}")

    _store_cancel_event(book_id, "P3", cancel_event)
    task_manager.launch(task, _run())
    return PhaseTriggerResponse(status="started", task_id=task.task_id, message=f"{label} 已启动")


@router.post("/books/{book_id}/stage2/retry-chapter/{chapter_number}")
async def retry_stage2_chapter(book_id: int, chapter_number: int):
    """Reset and retry a single failed chapter."""
    from app.pipeline.fact_pipeline_runner import FactPipelineRunner

    store = state_store()
    store.reset_chapter_checkpoint(book_id, chapter_number)

    label = f"重试第{chapter_number}章-B{book_id}"
    task = task_manager.create(book_id, "P3", label)
    cancel_event = asyncio.Event()

    runner = FactPipelineRunner(db_client, use_model=True, provider="local")

    async def _run():
        try:
            result = await runner.resume_book(book_id, cancel_event=cancel_event)
            task_manager.complete(task.task_id, result)
        except Exception as e:
            task_manager.fail(task.task_id, f"{type(e).__name__}: {e}")

    _store_cancel_event(book_id, "P3", cancel_event)
    task_manager.launch(task, _run())
    return PhaseTriggerResponse(status="started", task_id=task.task_id, message=f"{label} 已启动")


@router.post("/books/{book_id}/stage2/rerun-all")
async def rerun_stage2_all(book_id: int):
    """Clear checkpoint and rerun ALL chapters."""
    from app.pipeline.fact_pipeline_runner import FactPipelineRunner

    store = state_store()
    store.clear_checkpoints(book_id)
    state_store().update_stage(book_id, 2, 'PENDING')

    label = f"全量重跑提取-B{book_id}"
    task = task_manager.create(book_id, "P3", label)
    cancel_event = asyncio.Event()

    runner = FactPipelineRunner(db_client, use_model=True, provider="local")

    async def _run():
        try:
            result = await runner.process_book(book_id, cancel_event=cancel_event)
            task_manager.complete(task.task_id, result)
        except Exception as e:
            task_manager.fail(task.task_id, f"{type(e).__name__}: {e}")

    _store_cancel_event(book_id, "P3", cancel_event)
    task_manager.launch(task, _run())
    return PhaseTriggerResponse(status="started", task_id=task.task_id, message=f"{label} 已启动")


# ── Stage-level cleanup ──


@router.post("/books/{book_id}/cleanup/stage1", response_model=CleanupResponse)
async def cleanup_stage1(book_id: int):
    """Clean Stage 1 data (chapters + chunks) + reset state + clear tasks."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM novel_chunk WHERE book_id = %s", (book_id,))
            cur.execute("DELETE FROM novel_chapter WHERE book_id = %s", (book_id,))
            cur.execute("UPDATE novel_book SET status='IMPORTED', chapter_count=0, chunk_count=0 WHERE id = %s", (book_id,))
            cur.execute("DELETE FROM novel_pipeline_task WHERE book_id = %s AND phase IN ('P1','P2')", (book_id,))
        conn.commit()
        state_store().update_stage(book_id, 1, 'PENDING')
        task_manager.clear_by_book(book_id)
        return CleanupResponse(status="success", message="阶段一已清理（分章+分块）")
    except Exception as e:
        return CleanupResponse(status="error", message=str(e))


@router.post("/books/{book_id}/cleanup/stage2", response_model=CleanupResponse)
async def cleanup_stage2(book_id: int):
    """Clean Stage 2 data (chapter facts + model calls + checkpoint)."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM novel_model_call WHERE book_id = %s", (book_id,))
            cur.execute("DELETE FROM novel_chapter_fact WHERE book_id = %s", (book_id,))
            cur.execute("DELETE FROM novel_pipeline_task WHERE book_id = %s AND phase IN ('P3')", (book_id,))
        conn.commit()
        state_store().clear_checkpoints(book_id)
        state_store().update_stage(book_id, 2, 'PENDING')
        task_manager.clear_by_book(book_id)
        return CleanupResponse(status="success", message="阶段二已清理（提取+模型调用）")
    except Exception as e:
        return CleanupResponse(status="error", message=str(e))


@router.post("/books/{book_id}/cleanup/stage3", response_model=CleanupResponse)
async def cleanup_stage3(book_id: int):
    """Clean Stage 3 data (governance, narrative, qdrant, neo4j, export)."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            tables = [
                "novel_plot_stage", "novel_event_fact", "novel_event_mention",
                "novel_relation_fact", "novel_relation_mention", "novel_alias_decision",
                "novel_entity_profile", "novel_entity_mention",
            ]
            for t in tables:
                cur.execute(f"DELETE FROM {t} WHERE book_id = %s", (book_id,))
            cur.execute("DELETE FROM novel_pipeline_task WHERE book_id = %s AND phase IN ('P4','P5','P6','P7','P8')", (book_id,))
        conn.commit()
        # 清向量和图谱
        try:
            from app.stores.vector_index_store import VectorIndexStore
            VectorIndexStore(conn).delete_book_vectors(book_id)
        except Exception:
            pass
        neo4j_client.clear_book(book_id=book_id)
        state_store().update_stage(book_id, 3, 'PENDING')
        task_manager.clear_by_book(book_id)
        return CleanupResponse(status="success", message="阶段三已清理（治理+叙事+索引+图谱+导出）")
    except Exception as e:
        return CleanupResponse(status="error", message=str(e))


# ── Phase 3: Queue API ──

_queue_started = False


@router.post("/pipeline/enqueue")
async def pipeline_enqueue(body: dict):
    """Enqueue books for batch pipelined execution.
    Body: {"book_ids": [6,7,9,10], "mode": "full"|"stage1"|"stage2"|"stage3"}
    """
    from app.pipeline.scheduler import get_scheduler
    sched = get_scheduler()
    book_ids = body.get("book_ids", [])
    mode = body.get("mode", "full")
    if not book_ids:
        raise HTTPException(400, "book_ids required")
    reqs = await sched.enqueue(book_ids, mode)
    # Start scheduler if not running
    global _queue_started
    if not _queue_started:
        sched.start()
        _queue_started = True
    return {"status": "ok", "enqueued": len(reqs), "book_ids": [r.book_id for r in reqs]}


@router.post("/pipeline/cancel/{book_id}")
async def pipeline_cancel_book(book_id: int):
    from app.pipeline.scheduler import get_scheduler
    ok = await get_scheduler().cancel_book(book_id)
    return {"status": "ok" if ok else "not_found", "book_id": book_id}


@router.get("/pipeline/queue")
async def pipeline_queue_status():
    from app.pipeline.scheduler import get_scheduler
    try:
        result = await get_scheduler().get_status()
        return result
    except Exception as e:
        logger.error(f"Queue status error: {e}", exc_info=True)
        raise HTTPException(500, detail=f"Queue error: {type(e).__name__}: {e}")


@router.post("/pipeline/queue/clear")
async def pipeline_queue_clear():
    from app.pipeline.scheduler import get_scheduler
    await get_scheduler().cancel_all()
    return {"status": "ok", "message": "队列已清空"}


# ── Cancel event tracking ──

_cancel_events: dict[str, asyncio.Event] = {}  # key: "{book_id}_{phase}"


def _store_cancel_event(book_id: int, phase: str, event: asyncio.Event):
    key = f"{book_id}_{phase}"
    _cancel_events[key] = event


def _get_cancel_event(book_id: int, phase: str) -> Optional[asyncio.Event]:
    return _cancel_events.get(f"{book_id}_{phase}")


# ── Extended cancel: actually stops running coroutine ──

@router.post("/tasks/{task_id}/cancel-hard")
async def cancel_task_hard(task_id: str):
    """Cancel a task and signal the running coroutine to stop."""
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    task_manager.cancel(task_id)
    # Signal cancel event if any
    ev = _get_cancel_event(task.book_id, task.phase)
    if ev:
        ev.set()
        logger.info(f"Cancel event set for {task_id} (book={task.book_id} phase={task.phase})")
    return {"status": "cancelled", "task_id": task_id}


# ── Cleanup endpoints ──

@router.post("/books/{book_id}/cleanup", response_model=CleanupResponse)
async def cleanup_book(book_id: int):
    """Clear ALL derived data. Keeps novel_book (raw text)."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            tables = [
                "novel_plot_stage", "novel_event_fact", "novel_event_mention",
                "novel_relation_fact", "novel_relation_mention", "novel_alias_decision",
                "novel_entity_profile", "novel_entity_mention", "novel_model_call",
                "novel_chapter_fact", "novel_chunk", "novel_chapter",
            ]
            total = 0
            for t in tables:
                cur.execute(f"DELETE FROM {t} WHERE book_id = %s", (book_id,))
                total += cur.rowcount
            cur.execute("UPDATE novel_book SET status='IMPORTED', chapter_count=0, chunk_count=0 WHERE id = %s", (book_id,))
        # 清理 pipeline task + state + checkpoint 记录
        task_manager.clear_by_book(book_id)
        from app.stores.task_store import TaskStore
        try:
            TaskStore(conn).delete_by_book(book_id)
        except Exception:
            pass
        cur.execute("DELETE FROM novel_pipeline_task WHERE book_id = %s", (book_id,))
        cur.execute("DELETE FROM novel_book_pipeline_state WHERE book_id = %s", (book_id,))
        cur.execute("DELETE FROM novel_p3_checkpoint WHERE book_id = %s", (book_id,))
        conn.commit()
        logger.info(f"Cleaned book {book_id}: {total} rows")
        return CleanupResponse(status="success", message=f"已清理 {total} 条数据")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return CleanupResponse(status="error", message=str(e))


@router.post("/books/{book_id}/cleanup/qdrant", response_model=CleanupResponse)
async def cleanup_qdrant(book_id: int):
    from app.stores.vector_index_store import VectorIndexStore
    conn = _conn()
    try:
        VectorIndexStore(conn).delete_book_vectors(book_id)
        return CleanupResponse(status="success", message=f"Qdrant 向量已清理")
    except Exception as e:
        return CleanupResponse(status="error", message=str(e))


@router.post("/books/{book_id}/cleanup/neo4j", response_model=CleanupResponse)
async def cleanup_neo4j(book_id: int):
    neo4j_client.clear_book(book_id=book_id)
    return CleanupResponse(status="success", message=f"Neo4j 已清理")


@router.post("/pipeline/cleanup-all", response_model=CleanupResponse)
async def cleanup_all_books():
    conn = _conn()
    try:
        book_ids = "6,7,8,9,10"
        with conn.cursor() as cur:
            tables = [
                "novel_plot_stage", "novel_event_fact", "novel_event_mention",
                "novel_relation_fact", "novel_relation_mention", "novel_alias_decision",
                "novel_entity_profile", "novel_entity_mention", "novel_model_call",
                "novel_chapter_fact", "novel_chunk", "novel_chapter",
            ]
            total = 0
            for t in tables:
                cur.execute(f"DELETE FROM {t} WHERE book_id IN ({book_ids})")
                total += cur.rowcount
            cur.execute(f"UPDATE novel_book SET status='IMPORTED', chapter_count=0, chunk_count=0 WHERE id IN ({book_ids})")
        conn.commit()
        from app.stores.vector_index_store import VectorIndexStore
        store = VectorIndexStore(conn)
        for bid in [6, 7, 8, 9, 10]:
            store.delete_book_vectors(bid)
        neo4j_client.clear_all()
        return CleanupResponse(status="success", message=f"全量清理完成: {total} 条")
    except Exception as e:
        logger.error(f"Cleanup all failed: {e}")
        return CleanupResponse(status="error", message=str(e))
