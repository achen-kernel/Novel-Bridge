"""
Pipeline v2 API — background tasks, progress tracking, cleanup, parallel books.

== Bugs fixed 2026-05-27 ==
1. P3 KeyError:0 — fetchone() returns dict with DictCursor, [0] fails → use ['COUNT(*)']
2. P5 NoneType — NarrativeBuilder needs MysqlClient, not raw connection
3. Default use_model changed to True (model extraction primary, rules fallback)
4. Added provider selection: "local" (llama-server 9B) or "deepseek" (API)
5. Added provider support to P3 extraction (FactPipelineRunner + extract_chunk)
6. Better error handling: each phase runner wraps errors, catches + logs
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
from app.pipeline.task_manager import TaskStatus, task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["pipeline-v2"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


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
    task_manager.update_progress(task_id, 10, "正在拆分章节...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, BookProcessor(db_client).process, book_id, 0)
    chapters = result.get('chapters', 0)
    chunks = result.get('chunks', 0)
    if chapters == 0:
        raise phase_failed_error("P1", book_id,
                                 f"P1 产生 0 章节 — 请检查书籍 raw_text 是否存在",
                                 {"raw_text": result.get('char_count', 0)})
    task_manager.update_progress(task_id, 100, f"拆分完成: {chapters}章 {chunks}块")
    return result


async def _run_p2(book_id: int, task_id: str, **_):
    """Prior hint via DeepSeek API (梗概需要大上下文+高质量，强制 DeepSeek)."""
    import os
    from app.clients.model_client import ModelClient

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

    task_manager.update_progress(task_id, 100, "prior_hint 完成")
    return {"status": "success", "book_id": book_id, "prior_hint_keys": list(prior_hint_dict.keys())}


async def _run_p3(book_id: int, task_id: str, use_model: bool = True, provider: str = "local"):
    """Extract chapter facts.

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

    result = await runner.process_book(book_id)

    # BUG FIX: DictCursor returns dict, not tuple. Use COUNT(*) key.
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM novel_chapter_fact WHERE book_id = %s", (book_id,))
        row = c.fetchone()
        done = row["cnt"] if row else 0

    if done == 0:
        raise phase_failed_error("P3", book_id,
                                 f"P3 提取后产生 0 条 fact — 模型可能不可用或规则提取为空",
                                 {"total_chapters": total, "provider": provider})

    pct = min(100, done * 100 / max(total, 1))
    task_manager.update_progress(task_id, pct, f"提取完成: {done}/{total} 章")
    return result


async def _run_p4(book_id: int, task_id: str, **_):
    """Entity governance."""
    from app.pipeline.entity_governance_runner import EntityGovernanceRunner

    task_manager.update_progress(task_id, 10, "实体治理中...")
    result = EntityGovernanceRunner(db_client).process_book(book_id)
    profiles = result.get("profiles", 0)
    decisions = result.get("decisions", 0)
    task_manager.update_progress(task_id, 100, f"治理完成: {profiles} 画像, {decisions} 别名决策")
    return result


async def _run_p5(book_id: int, task_id: str, **_):
    """Narrative build.

    BUG FIX: NarrativeBuilder.__init__ takes MysqlClient, not a raw connection.
    """
    from app.pipeline.narrative_builder import NarrativeBuilder

    task_manager.update_progress(task_id, 10, "叙事构建中...")
    # FIX: pass db_client (MysqlClient), not conn (Connection)
    result = NarrativeBuilder(db_client).build_from_book(book_id)
    task_manager.update_progress(task_id, 100, "叙事构建完成")
    return result


async def _run_p6(book_id: int, task_id: str, **_):
    """Index to Qdrant."""
    from app.pipeline.index_runner import IndexRunner

    task_manager.update_progress(task_id, 10, "索引到 Qdrant...")
    result = await IndexRunner(db_client).index_book(book_id, reindex=True)
    chunks = result.get("chunks_indexed", 0)
    facts = result.get("facts_indexed", 0)
    task_manager.update_progress(task_id, 100, f"索引完成: {chunks} chunks, {facts} facts")
    return result


async def _run_p7(book_id: int, task_id: str, **_):
    """Project to Neo4j."""
    from app.pipeline.graph_projector import GraphProjector

    task_manager.update_progress(task_id, 10, "投影到 Neo4j...")
    conn = _conn()
    result = GraphProjector(conn).project_book(book_id, clear_first=True)
    task_manager.update_progress(task_id, 100, f"投影完成: {result.get('entities', 0)} 实体, {result.get('relations', 0)} 关系")
    return result


async def _run_p8(book_id: int, task_id: str, **_):
    """Export training data."""
    from app.stores.chapter_fact_store import ChapterFactStore
    from datetime import datetime

    task_manager.update_progress(task_id, 10, "导出训练数据...")
    conn = _conn()
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
    with open(output_path, "w", encoding="utf-8") as f:
        for fact in facts:
            f.write(json.dumps(fact, ensure_ascii=False, cls=DateTimeEncoder) + "\n")
    task_manager.update_progress(task_id, 100, f"导出完成: {len(facts)} 条 -> {output_path}")
    return {"status": "success", "exported": len(facts), "path": output_path}


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
        phases = {}
        for phase_name in PHASE_RUNNERS:
            tasks_list = task_manager.list_by_book(bid, phase=phase_name)
            if tasks_list:
                latest = tasks_list[0]
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

        result.append({
            "id": bid,
            "title": b["title"],
            "author": b["author"] or "",
            "status": b["status"],
            "chapter_count": b["chapter_count"],
            "chunk_count": b["chunk_count"],
            "char_count": b["char_count"],
            "phases": phases,
        })

    return {"books": result}


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
