"""
Pipeline state persistence: book-level stage tracking + P3 per-chapter checkpoint.

Tables:
  novel_book_pipeline_state   — one row per book, three-stage status + detail
  novel_p3_checkpoint         — per-chapter extraction result for Stage 2
"""
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pymysql

logger = logging.getLogger(__name__)


# ── SQL ──

SQL_CREATE_BOOK_STATE = """
CREATE TABLE IF NOT EXISTS novel_book_pipeline_state (
  book_id INT PRIMARY KEY,
  stage1_status VARCHAR(20) DEFAULT 'PENDING',
  stage1_completed_at DOUBLE DEFAULT NULL,
  stage2_status VARCHAR(20) DEFAULT 'PENDING',
  stage2_completed_at DOUBLE DEFAULT NULL,
  stage3_status VARCHAR(20) DEFAULT 'PENDING',
  stage3_completed_at DOUBLE DEFAULT NULL,
  stage2_detail JSON DEFAULT NULL,
  stage3_force_override TINYINT(1) DEFAULT 0,
  updated_at DOUBLE DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

SQL_CREATE_P3_CHECKPOINT = """
CREATE TABLE IF NOT EXISTS novel_p3_checkpoint (
  book_id INT NOT NULL,
  chapter_number INT NOT NULL,
  status VARCHAR(20) DEFAULT 'PENDING',
  retry_count INT DEFAULT 0,
  error TEXT DEFAULT NULL,
  started_at DOUBLE DEFAULT NULL,
  completed_at DOUBLE DEFAULT NULL,
  PRIMARY KEY (book_id, chapter_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


# ── Enums ──

class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"  # Stage 2 有失败章节
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class CheckpointStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# ── Data classes ──

@dataclass
class BookPipelineState:
    book_id: int
    stage1_status: str = StageStatus.PENDING.value
    stage1_completed_at: Optional[float] = None
    stage2_status: str = StageStatus.PENDING.value
    stage2_completed_at: Optional[float] = None
    stage3_status: str = StageStatus.PENDING.value
    stage3_completed_at: Optional[float] = None
    stage2_detail: dict = field(default_factory=lambda: {
        "consecutive_failures": 0,
        "total_failed": 0,
        "total_chapters": 0,
        "aborted": False,
    })
    stage3_force_override: bool = False
    updated_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "stage1": {"status": self.stage1_status, "completed_at": self.stage1_completed_at},
            "stage2": {"status": self.stage2_status, "completed_at": self.stage2_completed_at,
                       "detail": self.stage2_detail},
            "stage3": {"status": self.stage3_status, "completed_at": self.stage3_completed_at,
                       "force_override": self.stage3_force_override},
            "updated_at": self.updated_at,
        }


@dataclass
class P3Checkpoint:
    book_id: int
    chapter_number: int
    status: str = CheckpointStatus.PENDING.value
    retry_count: int = 0
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "chapter_number": self.chapter_number,
            "status": self.status,
            "retry_count": self.retry_count,
            "error": self.error[:200] if self.error else "",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ── Constants ──

MAX_RETRIES = 5                # 每章最多重试次数
MAX_CONSECUTIVE_FAILURES = 5   # 连续失败阈值
MAX_FAILURE_RATE = 0.20        # 总失败率阈值


# ── Store ──

class PipelineStateStore:
    """MySQL persistence for book pipeline state and P3 checkpoint."""

    def __init__(self, conn: Optional[pymysql.Connection] = None):
        self._conn = conn

    # -- connection management --

    def _get_conn(self) -> pymysql.Connection:
        if self._conn is None:
            from app.config import settings
            self._conn = pymysql.connect(
                host=settings.mysql_host, port=settings.mysql_port,
                user=settings.mysql_user, password=settings.mysql_password,
                database=settings.mysql_database, charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor, autocommit=True,
            )
        return self._conn

    def ensure_tables(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(SQL_CREATE_BOOK_STATE)
            c.execute(SQL_CREATE_P3_CHECKPOINT)
        logger.info("Pipeline state tables ensured")

    # -- BookPipelineState --

    def get_state(self, book_id: int) -> BookPipelineState:
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute("SELECT * FROM novel_book_pipeline_state WHERE book_id = %s", (book_id,))
            row = c.fetchone()
        if not row:
            state = BookPipelineState(book_id=book_id)
            self._insert_state(state)
            return state
        return self._row_to_state(row)

    def _row_to_state(self, row: dict) -> BookPipelineState:
        detail = row.get("stage2_detail")
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except (json.JSONDecodeError, TypeError):
                detail = {}
        return BookPipelineState(
            book_id=row["book_id"],
            stage1_status=row.get("stage1_status", "PENDING"),
            stage1_completed_at=row.get("stage1_completed_at"),
            stage2_status=row.get("stage2_status", "PENDING"),
            stage2_completed_at=row.get("stage2_completed_at"),
            stage3_status=row.get("stage3_status", "PENDING"),
            stage3_completed_at=row.get("stage3_completed_at"),
            stage2_detail=detail or {},
            stage3_force_override=bool(row.get("stage3_force_override", 0)),
            updated_at=row.get("updated_at"),
        )

    def _insert_state(self, state: BookPipelineState):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO novel_book_pipeline_state (book_id, stage1_status, stage2_status, stage3_status, updated_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (state.book_id, state.stage1_status, state.stage2_status, state.stage3_status, time.time()),
            )

    def update_stage(self, book_id: int, stage: int, status: str, detail: Optional[dict] = None):
        """Update a stage's status. stage=1|2|3."""
        conn = self._get_conn()
        now = time.time()
        col = f"stage{stage}_status"
        completed_col = f"stage{stage}_completed_at"
        with conn.cursor() as c:
            if status in (StageStatus.SUCCESS.value, StageStatus.FAILED.value,
                          StageStatus.CANCELLED.value, StageStatus.COMPLETED_WITH_ERRORS.value):
                c.execute(
                    f"INSERT INTO novel_book_pipeline_state (book_id, {col}, {completed_col}, stage2_detail, updated_at) "
                    f"VALUES (%s, %s, %s, %s, %s) "
                    f"ON DUPLICATE KEY UPDATE {col}=VALUES({col}), {completed_col}=VALUES({completed_col}), "
                    f"stage2_detail=COALESCE(VALUES(stage2_detail), stage2_detail), updated_at=VALUES(updated_at)",
                    (book_id, status, now, json.dumps(detail) if detail else None, now),
                )
            else:
                c.execute(
                    f"INSERT INTO novel_book_pipeline_state (book_id, {col}, stage2_detail, updated_at) "
                    f"VALUES (%s, %s, %s, %s) "
                    f"ON DUPLICATE KEY UPDATE {col}=VALUES({col}), "
                    f"stage2_detail=COALESCE(VALUES(stage2_detail), stage2_detail), updated_at=VALUES(updated_at)",
                    (book_id, status, json.dumps(detail) if detail else None, now),
                )

    def update_stage2_detail(self, book_id: int, detail: dict):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "UPDATE novel_book_pipeline_state SET stage2_detail = %s, updated_at = %s WHERE book_id = %s",
                (json.dumps(detail), time.time(), book_id),
            )

    def set_stage3_override(self, book_id: int, override: bool = True):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO novel_book_pipeline_state (book_id, stage3_force_override, updated_at) "
                "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE "
                "stage3_force_override=VALUES(stage3_force_override), updated_at=VALUES(updated_at)",
                (book_id, 1 if override else 0, time.time()),
            )

    def can_proceed_to_stage3(self, book_id: int) -> tuple[bool, str]:
        """Check if Stage 3 is allowed. Returns (allowed, reason)."""
        state = self.get_state(book_id)
        if state.stage3_status == StageStatus.SUCCESS.value:
            return False, "阶段三已完成"
        if state.stage2_status == StageStatus.SUCCESS.value:
            return True, ""
        if state.stage3_force_override:
            return True, "强制覆盖：阶段二未完成但用户已确认"
        if state.stage2_status == StageStatus.COMPLETED_WITH_ERRORS.value:
            return False, "阶段二有失败章节，请先处理（或使用'忽略继续'）"
        if state.stage2_status in (StageStatus.PENDING.value, StageStatus.RUNNING.value):
            return False, "阶段二未完成"
        return False, f"阶段二状态={state.stage2_status}，不允许进入阶段三"

    # -- P3Checkpoint --

    def get_checkpoint(self, book_id: int, chapter_number: int) -> Optional[P3Checkpoint]:
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_p3_checkpoint WHERE book_id = %s AND chapter_number = %s",
                (book_id, chapter_number),
            )
            row = c.fetchone()
        if not row:
            return None
        return P3Checkpoint(
            book_id=row["book_id"], chapter_number=row["chapter_number"],
            status=row["status"], retry_count=row["retry_count"],
            error=row["error"], started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def upsert_checkpoint(self, cp: P3Checkpoint):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO novel_p3_checkpoint (book_id, chapter_number, status, retry_count, error, started_at, completed_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE "
                "status=VALUES(status), retry_count=VALUES(retry_count), error=VALUES(error), "
                "started_at=VALUES(started_at), completed_at=VALUES(completed_at)",
                (cp.book_id, cp.chapter_number, cp.status, cp.retry_count,
                 cp.error, cp.started_at, cp.completed_at),
            )

    def get_pending_chapters(self, book_id: int) -> list[int]:
        """Get chapter numbers that need processing: PENDING or FAILED(retry<MAX)."""
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT chapter_number, retry_count FROM novel_p3_checkpoint "
                "WHERE book_id = %s AND status IN ('PENDING', 'FAILED') AND retry_count < %s "
                "ORDER BY chapter_number",
                (book_id, MAX_RETRIES),
            )
            return [r["chapter_number"] for r in c.fetchall()]

    def get_all_checkpoints(self, book_id: int) -> list[P3Checkpoint]:
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_p3_checkpoint WHERE book_id = %s ORDER BY chapter_number",
                (book_id,),
            )
            return [P3Checkpoint(
                book_id=r["book_id"], chapter_number=r["chapter_number"],
                status=r["status"], retry_count=r["retry_count"],
                error=r["error"], started_at=r["started_at"],
                completed_at=r["completed_at"],
            ) for r in c.fetchall()]

    def get_failed_chapters(self, book_id: int) -> list[P3Checkpoint]:
        """Get chapters that are permanently failed (retry >= MAX)."""
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_p3_checkpoint "
                "WHERE book_id = %s AND status = 'FAILED' AND retry_count >= %s "
                "ORDER BY chapter_number",
                (book_id, MAX_RETRIES),
            )
            return [P3Checkpoint(
                book_id=r["book_id"], chapter_number=r["chapter_number"],
                status=r["status"], retry_count=r["retry_count"],
                error=r["error"], started_at=r["started_at"],
                completed_at=r["completed_at"],
            ) for r in c.fetchall()]

    def get_checkpoint_summary(self, book_id: int) -> dict:
        """Get Stage 2 progress summary."""
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT status, COUNT(*) as cnt FROM novel_p3_checkpoint "
                "WHERE book_id = %s GROUP BY status",
                (book_id,),
            )
            counts = {r["status"]: r["cnt"] for r in c.fetchall()}
        total = sum(counts.values())
        return {
            "total": total,
            "success": counts.get("SUCCESS", 0),
            "failed": counts.get("FAILED", 0),
            "pending": counts.get("PENDING", 0),
            "permanent_failed": len(self.get_failed_chapters(book_id)),
        }

    def get_resume_chapters(self, book_id: int, lookback: int = 2) -> list[int]:
        """Get chapters to process on resume, going back `lookback` chapters
        before the first non-SUCCESS chapter for consistency.

        Example: chapters 1-13 SUCCESS, 14 PENDING → returns [12, 13, 14, ...]
        Chapters 12 and 13 get reset to PENDING for re-processing.
        """
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "SELECT chapter_number, status FROM novel_p3_checkpoint "
                "WHERE book_id = %s ORDER BY chapter_number",
                (book_id,),
            )
            rows = c.fetchall()

        if not rows:
            return []  # no checkpoint data, fall back to full run

        # Find first non-SUCCESS chapter
        first_pending = None
        for r in rows:
            if r["status"] != "SUCCESS":
                first_pending = r["chapter_number"]
                break

        if first_pending is None:
            return []  # all SUCCESS, nothing to resume

        # Go back `lookback` chapters from first_pending
        resume_start = max(1, first_pending - lookback)

        # Reset those chapters to PENDING
        for cn in range(resume_start, first_pending):
            self.reset_chapter_checkpoint(book_id, cn)

        # Also reset the first_pending if it's FAILED (to give it another try)
        cp = self.get_checkpoint(book_id, first_pending)
        if cp and cp.status == "FAILED" and cp.retry_count < MAX_RETRIES:
            self.reset_chapter_checkpoint(book_id, first_pending)

        # Return all chapters from resume_start onward
        return [r["chapter_number"] for r in rows if r["chapter_number"] >= resume_start
                and r["status"] in ("PENDING", "FAILED")
                and (r["status"] != "FAILED" or self.get_checkpoint(book_id, r["chapter_number"]).retry_count < MAX_RETRIES)]

    def reset_chapter_checkpoint(self, book_id: int, chapter_number: int):
        """Reset a chapter to PENDING (for retry)."""
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute(
                "UPDATE novel_p3_checkpoint SET status = 'PENDING', retry_count = 0, error = NULL "
                "WHERE book_id = %s AND chapter_number = %s",
                (book_id, chapter_number),
            )

    # -- Clear --

    def clear_state(self, book_id: int):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM novel_book_pipeline_state WHERE book_id = %s", (book_id,))

    def clear_checkpoints(self, book_id: int):
        conn = self._get_conn()
        with conn.cursor() as c:
            c.execute("DELETE FROM novel_p3_checkpoint WHERE book_id = %s", (book_id,))


# Singleton (lazy-initialized after DB is ready)
_state_store: Optional[PipelineStateStore] = None


def get_state_store() -> PipelineStateStore:
    global _state_store
    if _state_store is None:
        _state_store = PipelineStateStore()
        _state_store.ensure_tables()
    return _state_store


def init_state_store(conn: Optional[pymysql.Connection] = None):
    global _state_store
    _state_store = PipelineStateStore(conn)
    _state_store.ensure_tables()
    logger.info("PipelineStateStore initialized")
    return _state_store
