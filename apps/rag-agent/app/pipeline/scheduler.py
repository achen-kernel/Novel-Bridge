"""
Batch pipeline scheduler — queue + pipelined execution.

Pipelining logic:
  Book A Stage 1 (fast) → Book A Stage 2 (slow) → Book B Stage 1 starts immediately
  → Book A Stage 2 done → Book A Stage 3 (fast) → Book B Stage 2 starts

Concurrency rules:
  Stage 1: unlimited (fast, <1min per book)
  Stage 2: 1 book at a time (local 9B bottleneck)
  Stage 3: unlimited (fast, ~5min per book)
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.pipeline.pipeline_state import get_state_store

logger = logging.getLogger(__name__)


class QueueMode(str, Enum):
    FULL = "full"           # 从 Stage 1 开始全流程
    STAGE1 = "stage1"       # 只跑 Stage 1
    STAGE2 = "stage2"       # 只跑 Stage 2 (续跑)
    STAGE3 = "stage3"       # 只跑 Stage 3


class BookQueueStatus(str, Enum):
    QUEUED = "QUEUED"           # 在排队
    STAGE1_RUNNING = "STAGE1_RUNNING"
    STAGE1_DONE = "STAGE1_DONE"
    STAGE2_RUNNING = "STAGE2_RUNNING"
    STAGE2_DONE = "STAGE2_DONE"
    STAGE3_RUNNING = "STAGE3_RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class BookPipelineRequest:
    book_id: int
    mode: QueueMode = QueueMode.FULL
    status: BookQueueStatus = BookQueueStatus.QUEUED
    enqueued_at: float = field(default_factory=time.time)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "enqueued_at": self.enqueued_at,
            "error": self.error[:200] if self.error else "",
        }


STAGE2_MAX_CONCURRENT = 1


class BookPipelineScheduler:
    """Manages the queue and drives pipelined execution."""

    def __init__(self, db_client: Optional[MysqlClient] = None):
        self.db_client = db_client
        self._queue: list[BookPipelineRequest] = []
        self._lock = asyncio.Lock()
        self._active_stage2_count = 0  # books currently in Stage 2
        self._scheduler_task: Optional[asyncio.Task] = None
        self._started = False

    # ── Lifecycle ──

    def start(self):
        """Start the scheduler background loop."""
        if self._started:
            return
        self._started = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("Pipeline scheduler started")

    async def stop(self):
        self._started = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Pipeline scheduler stopped")

    # ── Queue management ──

    async def enqueue(self, book_ids: list[int], mode: QueueMode = QueueMode.FULL) -> list[BookPipelineRequest]:
        """Add books to the queue. Returns the requests created."""
        # Convert string to enum if needed (API receives JSON strings)
        if isinstance(mode, str):
            mode = QueueMode(mode)
        async with self._lock:
            requests = []
            for bid in book_ids:
                # Don't re-enqueue if already in queue
                if any(r.book_id == bid and r.status not in (
                    BookQueueStatus.COMPLETED, BookQueueStatus.CANCELLED, BookQueueStatus.FAILED
                ) for r in self._queue):
                    continue
                req = BookPipelineRequest(book_id=bid, mode=mode)
                self._queue.append(req)
                requests.append(req)
            return requests

    async def cancel_book(self, book_id: int) -> bool:
        """Cancel a book: remove from queue or signal running task."""
        async with self._lock:
            for req in self._queue:
                if req.book_id != book_id:
                    continue
                if req.status in (BookQueueStatus.COMPLETED, BookQueueStatus.CANCELLED, BookQueueStatus.FAILED):
                    return False
                if req.status in (BookQueueStatus.QUEUED, BookQueueStatus.STAGE1_DONE, BookQueueStatus.STAGE2_DONE):
                    # Not currently running, just remove
                    req.status = BookQueueStatus.CANCELLED
                    logger.info(f"Removed book {book_id} from queue (was {req.status.value})")
                    return True
                # Running — signal cancel via event
                req.status = BookQueueStatus.CANCELLED
                logger.info(f"Requested cancel for running book {book_id}")
                self._signal_cancel(book_id)
                return True
            return False

    async def cancel_all(self):
        """Cancel all queued and running books."""
        async with self._lock:
            for req in self._queue:
                if req.status not in (BookQueueStatus.COMPLETED, BookQueueStatus.CANCELLED, BookQueueStatus.FAILED):
                    req.status = BookQueueStatus.CANCELLED
                    if req.status in (BookQueueStatus.STAGE1_RUNNING, BookQueueStatus.STAGE2_RUNNING, BookQueueStatus.STAGE3_RUNNING):
                        self._signal_cancel(req.book_id)

    async def get_status(self) -> dict:
        """Get full queue status."""
        async with self._lock:
            active = [r for r in self._queue if r.status not in (
                BookQueueStatus.COMPLETED, BookQueueStatus.CANCELLED, BookQueueStatus.FAILED)]
            completed = [r for r in self._queue if r.status in (
                BookQueueStatus.COMPLETED, BookQueueStatus.CANCELLED, BookQueueStatus.FAILED)][-20:]
            return {
                "active_queue": [r.to_dict() for r in active],
                "completed": [r.to_dict() for r in completed],
                "stage2_active_count": self._active_stage2_count,
            }

    # ── Cancel event signal ──

    def _signal_cancel(self, book_id: int):
        """Signal cancel event for a running book's phase."""
        from app.api.pipeline_v2 import _get_cancel_event
        for phase in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"):
            ev = _get_cancel_event(book_id, phase)
            if ev:
                ev.set()
                logger.info(f"Cancel event set for book {book_id} phase {phase}")

    # ── Scheduler loop ──

    async def _run_scheduler(self):
        """Background loop: pick from queue, advance stages, respect concurrency."""
        # Late import to avoid circular deps
        from app.api.pipeline_v2 import (
            PHASE_RUNNERS, PHASE_LABELS, state_store, task_manager,
            _store_cancel_event, _get_cancel_event,
            _run_p1, _run_p2, _run_p3, _run_p4, _run_p5,
            _run_p6, _run_p7, _run_p8,
        )

        STAGE1_PHASES = [("P1", _run_p1), ("P2", _run_p2)]
        STAGE2_PHASES = [("P3", _run_p3)]
        STAGE3_PHASES = [("P4", _run_p4), ("P5", _run_p5), ("P6", _run_p6), ("P7", _run_p7), ("P8", _run_p8)]

        while self._started:
            try:
                async with self._lock:
                    # Find the next book to advance
                    active_books = [r for r in self._queue if r.status not in (
                        BookQueueStatus.QUEUED, BookQueueStatus.COMPLETED,
                        BookQueueStatus.CANCELLED, BookQueueStatus.FAILED)]
                    queued_books = [r for r in self._queue if r.status == BookQueueStatus.QUEUED]
                    stage2_ready = [r for r in active_books if r.status == BookQueueStatus.STAGE1_DONE]

                # ── Stage 2 slot check ──
                if self._active_stage2_count < STAGE2_MAX_CONCURRENT and stage2_ready:
                    req = stage2_ready[0]
                    async with self._lock:
                        req.status = BookQueueStatus.STAGE2_RUNNING
                    self._active_stage2_count += 1
                    asyncio.create_task(self._run_stages(req, STAGE2_PHASES, BookQueueStatus.STAGE2_DONE))
                    logger.info(f"Scheduler: Book {req.book_id} → Stage 2 (P3)")

                # ── Start new books from queue (Stage 1) ──
                if queued_books:
                    req = queued_books[0]
                    async with self._lock:
                        req.status = BookQueueStatus.STAGE1_RUNNING
                    asyncio.create_task(self._run_stages(req, STAGE1_PHASES, BookQueueStatus.STAGE1_DONE))
                    logger.info(f"Scheduler: Book {req.book_id} → Stage 1 (P1+P2)")

                # ── Stage 3: books that finished Stage 2 ──
                stage3_ready = [r for r in active_books if r.status == BookQueueStatus.STAGE2_DONE]
                for req in stage3_ready:
                    async with self._lock:
                        req.status = BookQueueStatus.STAGE3_RUNNING
                    asyncio.create_task(self._run_stages(req, STAGE3_PHASES, BookQueueStatus.COMPLETED))
                    logger.info(f"Scheduler: Book {req.book_id} → Stage 3 (P4-P8)")

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            await asyncio.sleep(2)  # poll interval

    async def _run_stages(self, req: BookPipelineRequest, phases: list[tuple],
                           done_status: BookQueueStatus):
        """Run a list of phases for a book. Updates queue status on completion."""
        # Late import avoids circular dep (pipeline_v2 imports scheduler inside methods)
        from app.api.pipeline_v2 import task_manager as tm
        from app.api.pipeline_v2 import PHASE_LABELS as pl
        from app.api.pipeline_v2 import state_store as ss
        from app.api.pipeline_v2 import _store_cancel_event as sce

        for phase_name, phase_runner in phases:
            try:
                # Check cancellation
                async with self._lock:
                    if req.status == BookQueueStatus.CANCELLED:
                        return

                # Check stage gate for Stage 3
                if phase_name in ("P4", "P5", "P6", "P7", "P8"):
                    allowed, reason = ss().can_proceed_to_stage3(req.book_id)
                    if not allowed:
                        logger.warning(f"Book {req.book_id} blocked from Stage 3: {reason}")
                        # If forced override, proceed anyway
                        st = ss().get_state(req.book_id)
                        if not st.stage3_force_override:
                            async with self._lock:
                                req.status = BookQueueStatus.FAILED
                                req.error = f"阶段三被阻止: {reason}"
                            return

                label = f"{pl.get(phase_name, phase_name)}-B{req.book_id}"
                task = tm.create(req.book_id, phase_name, label)

                # Create cancel event
                cancel_event = asyncio.Event()
                sce(req.book_id, phase_name, cancel_event)

                logger.info(f"Scheduler: running {label}")
                result = await phase_runner(
                    book_id=req.book_id, task_id=task.task_id,
                    use_model=True, provider="local",
                )

                # If cancelled during execution, stop
                async with self._lock:
                    if req.status == BookQueueStatus.CANCELLED:
                        tm.cancel(task.task_id)
                        return

                tm.complete(task.task_id, result if isinstance(result, dict) else {"result": str(result)})

                # Update book state for Stage 1 completion
                if phase_name == "P2":
                    ss().update_stage(req.book_id, 1, 'SUCCESS')
                elif phase_name == "P3":
                    # Stage 2 status already updated inside FactPipelineRunner
                    pass

            except Exception as e:
                logger.error(f"Scheduler: phase {phase_name} failed for book {req.book_id}: {e}")
                async with self._lock:
                    req.status = BookQueueStatus.FAILED
                    req.error = f"{phase_name}: {e}"
                ss().update_stage(req.book_id, 2 if phase_name == "P3" else 3, 'FAILED')
                # If Stage 2 fails, decrease count
                if phase_name == "P3":
                    self._active_stage2_count = max(0, self._active_stage2_count - 1)
                return

        # All phases in this stage completed
        async with self._lock:
            req.status = done_status
            if done_status == BookQueueStatus.COMPLETED:
                ss().update_stage(req.book_id, 3, 'SUCCESS')
                logger.info(f"Scheduler: Book {req.book_id} fully completed!")
            elif done_status == BookQueueStatus.STAGE2_DONE:
                self._active_stage2_count = max(0, self._active_stage2_count - 1)
            elif done_status == BookQueueStatus.STAGE1_DONE:
                pass  # Wait for Stage 2 slot


# Singleton
_scheduler: Optional[BookPipelineScheduler] = None


def get_scheduler() -> BookPipelineScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BookPipelineScheduler()
    return _scheduler
