"""
Background task manager for pipeline phases.

Each pipeline phase (P3-P8) runs as an async background task.
The endpoint returns immediately with a task_id; the frontend polls
GET /api/tasks/{task_id} for status and progress updates.

Supports optional MySQL persistence via TaskStore.
When a store is configured, tasks survive server restarts.
"""
import asyncio
import logging
import time
import uuid
from enum import Enum
from threading import Lock
from typing import Coroutine, Optional

from app.pipeline.errors import PipelineError

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PipelineTask:
    """Represents a single pipeline phase execution."""

    def __init__(self, book_id: int, phase: str, label: str = ""):
        self.task_id = f"{phase}-{book_id}-{uuid.uuid4().hex[:8]}"
        self.book_id = book_id
        self.phase = phase
        self.label = label or f"{phase} Book {book_id}"
        self.status = TaskStatus.PENDING
        self.progress = 0.0  # 0-100
        self.message = ""
        self.result = {}
        self.error = ""
        self.error_code: str = ""        # structured error code
        self.error_detail: dict = {}      # structured error detail
        self.created_at = time.time()
        self.completed_at: float = 0.0
        self._coro: Optional[Coroutine] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "book_id": self.book_id,
            "phase": self.phase,
            "label": self.label,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "elapsed": round(time.time() - self.created_at, 1) if self.status in (TaskStatus.RUNNING, TaskStatus.PENDING) else round(self.completed_at - self.created_at, 1),
        }


class TaskManager:
    """Thread-safe task manager with optional MySQL persistence."""

    def __init__(self):
        self._tasks: dict[str, PipelineTask] = {}
        self._lock = Lock()
        self._store = None  # Optional[TaskStore] — set via set_store()

    def set_store(self, store):
        """Attach a persistent TaskStore for MySQL-backed durability."""
        self._store = store
        logger.info("TaskManager: persistent store attached")

    def restore(self, limit: int = 100):
        """Load recent tasks from persistent store into memory."""
        if not self._store:
            logger.warning("TaskManager: no store configured, skipping restore")
            return
        try:
            rows = self._store.list_recent(limit=limit)
            for row in rows:
                task = PipelineTask(
                    book_id=row["book_id"],
                    phase=row["phase"],
                    label=row.get("label", ""),
                )
                task.task_id = row["task_id"]
                task.status = TaskStatus(row["status"])
                task.progress = row["progress"]
                task.message = row.get("message") or ""
                task.error = row.get("error") or ""
                task.error_code = row.get("error_code") or ""
                task.error_detail = row.get("error_detail") or {}
                task.result = row.get("result_json") or {}
                task.created_at = row["created_at"]
                task.completed_at = row.get("completed_at") or 0.0
                with self._lock:
                    self._tasks[task.task_id] = task
            logger.info(f"TaskManager: restored {len(rows)} tasks from store")
        except Exception as e:
            logger.error(f"TaskManager: restore failed: {e}")

    # ── persistence helper ──

    def _persist(self, task: PipelineTask):
        if not self._store:
            return
        try:
            self._store.save(
                task_id=task.task_id,
                book_id=task.book_id,
                phase=task.phase,
                label=task.label,
                status=task.status.value,
                progress=task.progress,
                message=task.message,
                error=task.error,
                error_code=task.error_code,
                error_detail=task.error_detail,
                result=task.result,
                created_at=task.created_at,
                completed_at=task.completed_at,
            )
        except Exception as e:
            logger.warning(f"TaskManager: persist failed for {task.task_id}: {e}")

    # ── lifecycle ──

    def create(self, book_id: int, phase: str, label: str = "", coro: Optional[Coroutine] = None) -> PipelineTask:
        """Create a new task and optionally associate a coroutine."""
        task = PipelineTask(book_id, phase, label)
        task._coro = coro
        with self._lock:
            self._tasks[task.task_id] = task
        self._persist(task)
        logger.info(f"Task created: {task.task_id} ({label})")
        return task

    def get(self, task_id: str) -> Optional[PipelineTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def start(self, task_id: str):
        task = self.get(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.message = "启动中..."
            self._persist(task)

    def update_progress(self, task_id: str, progress: float, message: str = ""):
        task = self.get(task_id)
        if task:
            task.progress = min(progress, 99.9)
            if message:
                task.message = message
            self._persist(task)

    def complete(self, task_id: str, result: dict = None):
        task = self.get(task_id)
        if task:
            task.status = TaskStatus.SUCCESS
            task.progress = 100.0
            task.completed_at = time.time()
            task.message = "完成"
            if result:
                task.result = result
            self._persist(task)
            logger.info(f"Task completed: {task_id}")

    def fail(self, task_id: str, error: str, error_code: str = "", error_detail: dict = None):
        task = self.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = str(error)[:500]
            task.error_code = error_code
            task.error_detail = error_detail or {}
            task.message = f"失败 [{error_code}]" if error_code else "失败"
            self._persist(task)
            logger.error(f"Task failed: {task_id}: [{error_code}] {error}")

    def clear_by_book(self, book_id: int):
        """Remove all in-memory tasks for a book."""
        with self._lock:
            to_remove = [tid for tid, t in self._tasks.items() if t.book_id == book_id]
            for tid in to_remove:
                del self._tasks[tid]

    def list_by_book(self, book_id: int, phase: str = None) -> list[PipelineTask]:
        with self._lock:
            tasks = [t for t in self._tasks.values() if t.book_id == book_id]
            if phase:
                tasks = [t for t in tasks if t.phase == phase]
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def list_recent(self, limit: int = 50) -> list[PipelineTask]:
        with self._lock:
            tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]

    def cancel(self, task_id: str):
        """Cancel a task (mark as CANCELLED). Note: does not stop the actual coroutine."""
        task = self.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            task.message = "已取消"
            self._persist(task)
            logger.info(f"Task cancelled: {task_id}")

    def launch(self, task: PipelineTask, coro: Coroutine):
        """Launch a coroutine as a background task and wire up status updates."""
        task._coro = coro
        self.start(task.task_id)

        async def _run():
            try:
                # Check if already cancelled before starting
                if self.get(task.task_id) and self.get(task.task_id).status == TaskStatus.CANCELLED:
                    return
                result = await coro
                # Don't update if cancelled during execution
                t = self.get(task.task_id)
                if t and t.status == TaskStatus.CANCELLED:
                    return
                self.complete(task.task_id, result if isinstance(result, dict) else {"result": str(result)})
            except asyncio.CancelledError:
                self.cancel(task.task_id)
            except PipelineError as pe:
                # Structured pipeline error with code + detail
                t = self.get(task.task_id)
                if t and t.status != TaskStatus.CANCELLED:
                    self.fail(task.task_id, str(pe), error_code=pe.code, error_detail=pe.detail)
                    logger.error(f"Pipeline task {task.task_id} failed [{pe.code}]: {pe}")
            except Exception as e:
                # Don't mark as FAILED if already cancelled
                t = self.get(task.task_id)
                if t and t.status != TaskStatus.CANCELLED:
                    self.fail(task.task_id, f"{type(e).__name__}: {e}")
                    logger.exception(f"Background task {task.task_id} failed")

        asyncio.create_task(_run())


# Singleton
task_manager = TaskManager()
