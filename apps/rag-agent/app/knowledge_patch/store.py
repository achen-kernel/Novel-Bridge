"""KnowledgePatch persistence — MySQL implementation with three-table schema.

Tables:
  novel_knowledge_patch          — patch main record
  novel_knowledge_patch_evidence — individual evidence items
  novel_patch_review             — review history log

Backward compatible: old patches with evidence_json still readable via
evidence_json fallback in get_patch() / list_patches().
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql

from app.knowledge_patch.schemas import KnowledgePatch, PatchStatus

logger = logging.getLogger(__name__)

DDL_ALL = """
CREATE TABLE IF NOT EXISTS novel_knowledge_patch (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    patch_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) DEFAULT NULL,
    target_id BIGINT DEFAULT NULL,
    payload_json JSON,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(30) NOT NULL DEFAULT 'PROPOSED',
    created_by VARCHAR(100) NOT NULL DEFAULT 'reader_agent',
    run_id BIGINT DEFAULT NULL,
    review_note TEXT,
    reviewed_by VARCHAR(100) DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_kp_book (book_id),
    KEY idx_kp_status (status),
    KEY idx_kp_type (patch_type),
    KEY idx_kp_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_knowledge_patch_evidence (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patch_id BIGINT NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    source_id BIGINT NOT NULL DEFAULT 0,
    chapter_id BIGINT DEFAULT NULL,
    excerpt TEXT,
    evidence_level VARCHAR(20) NOT NULL DEFAULT 'NEAR',
    relevance_score DOUBLE DEFAULT 0.0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_evidence_patch (patch_id),
    CONSTRAINT fk_evidence_patch FOREIGN KEY (patch_id) REFERENCES novel_knowledge_patch(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS novel_patch_review (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patch_id BIGINT NOT NULL,
    action VARCHAR(30) NOT NULL DEFAULT 'REVIEW',
    previous_status VARCHAR(30) NOT NULL,
    new_status VARCHAR(30) NOT NULL,
    review_note TEXT,
    reviewed_by VARCHAR(100) NOT NULL DEFAULT 'human',
    risk_override VARCHAR(20) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_review_patch (patch_id),
    CONSTRAINT fk_review_patch FOREIGN KEY (patch_id) REFERENCES novel_knowledge_patch(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Terminal states that prevent further reviews
TERMINAL_REVIEW_STATES = frozenset({"MERGED", "CANCELED"})


class MysqlKnowledgePatchStore:
    """MySQL adapter for KnowledgePatch CRUD with evidence/review tables."""

    def __init__(self, conn: pymysql.Connection, *, auto_create: bool = True) -> None:
        self.conn = conn
        if auto_create:
            self._ensure_tables()

    def _ensure_tables(self) -> None:
        for stmt in DDL_ALL.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    with self.conn.cursor() as c:
                        c.execute(stmt + ";")
                    self.conn.commit()
                except Exception as e:
                    logger.warning("DDL statement skipped (may already exist): %s", e)

        # Migration: add action/risk_override if table already exists
        self._migrate_patch_review()

    def _migrate_patch_review(self) -> None:
        """Add action/risk_override columns — silently skip if they exist."""
        for col, ddl in [
            ("action",
             "ALTER TABLE novel_patch_review "
             "ADD COLUMN action VARCHAR(30) NOT NULL DEFAULT 'REVIEW' AFTER patch_id"),
            ("risk_override",
             "ALTER TABLE novel_patch_review "
             "ADD COLUMN risk_override VARCHAR(20) DEFAULT NULL AFTER reviewed_by"),
        ]:
            try:
                with self.conn.cursor() as c:
                    c.execute(ddl)
                self.conn.commit()
            except pymysql.err.OperationalError as e:
                # code 1060 = Duplicate column; code 1062 = already exists
                code = e.args[0] if e.args else 0
                if code in (1060, 1062):
                    pass
                else:
                    logger.warning("ALTER TABLE failed (code=%s): %s", code, str(ddl)[:60])

    def create_patch(self, patch: KnowledgePatch) -> int:
        """Insert patch main record + evidence rows. Returns patch_id."""
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_knowledge_patch
                   (book_id, patch_type, target_type, target_id,
                    payload_json, risk_level, status,
                    created_by, run_id, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    patch.book_id,
                    patch.patch_type.value,
                    patch.target_type,
                    patch.target_id,
                    json.dumps(patch.payload, ensure_ascii=False),
                    patch.risk_level.value,
                    patch.status.value,
                    patch.created_by,
                    patch.run_id,
                    now,
                    now,
                ),
            )
            patch_id = c.lastrowid

            for ev in patch.evidence:
                c.execute(
                    """INSERT INTO novel_knowledge_patch_evidence
                       (patch_id, source_type, source_id, chapter_id,
                        excerpt, evidence_level, relevance_score, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        patch_id,
                        ev.source_type,
                        ev.source_id,
                        ev.chapter_id,
                        ev.excerpt[:500] if ev.excerpt else "",
                        ev.evidence_level.value
                        if hasattr(ev.evidence_level, "value")
                        else ev.evidence_level,
                        ev.relevance_score,
                        now,
                    ),
                )
            self.conn.commit()
            return patch_id  # type: ignore[return-value]

    def _attach_evidence_to_row(self, row: dict[str, Any]) -> None:
        """Populate row['evidence'] from evidence table or legacy evidence_json."""
        patch_id = row["id"]
        with self.conn.cursor() as c2:
            c2.execute(
                "SELECT * FROM novel_knowledge_patch_evidence "
                "WHERE patch_id = %s ORDER BY id",
                (patch_id,),
            )
            evidence_rows: list[dict[str, Any]] = c2.fetchall()  # type: ignore[assignment]
            if evidence_rows:
                row["evidence"] = evidence_rows
                row["evidence_count"] = len(evidence_rows)
                return
        raw = row.pop("evidence_json", None)
        if isinstance(raw, str):
            try:
                row["evidence"] = json.loads(raw)
                row["evidence_count"] = len(row["evidence"])
            except (json.JSONDecodeError, TypeError):
                row["evidence"] = []
                row["evidence_count"] = 0
        else:
            row["evidence"] = []
            row["evidence_count"] = 0

    def _attach_review_logs_to_row(self, row: dict[str, Any]) -> None:
        """Populate row['review_logs'] from novel_patch_review."""
        patch_id = row["id"]
        with self.conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_patch_review "
                "WHERE patch_id = %s ORDER BY id",
                (patch_id,),
            )
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            row["review_logs"] = rows

    def get_patch(self, patch_id: int) -> dict[str, Any] | None:
        with self.conn.cursor() as c:
            c.execute("SELECT * FROM novel_knowledge_patch WHERE id = %s", (patch_id,))
            row: dict[str, Any] | None = c.fetchone()  # type: ignore[assignment]
            if not row:
                return None
            if isinstance(row.get("payload_json"), str):
                try:
                    row["payload_json"] = json.loads(row["payload_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            self._attach_evidence_to_row(row)
            self._attach_review_logs_to_row(row)
            return row

    def list_patches(
        self,
        book_id: int | None = None,
        status: str | None = None,
        run_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            conditions: list[str] = []
            params: list[Any] = []
            if book_id is not None:
                conditions.append("p.book_id = %s")
                params.append(book_id)
            if status:
                conditions.append("p.status = %s")
                params.append(status)
            if run_id is not None:
                conditions.append("p.run_id = %s")
                params.append(run_id)
            where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
            sql = (
                "SELECT p.*, "
                "  (SELECT COUNT(*) FROM novel_knowledge_patch_evidence e "
                "   WHERE e.patch_id = p.id) as evidence_count, "
                "  (SELECT COUNT(*) FROM novel_patch_review r "
                "   WHERE r.patch_id = p.id) as review_count "
                f"FROM novel_knowledge_patch p{where} ORDER BY p.created_at DESC LIMIT %s"
            )
            params.append(limit)
            c.execute(sql, params)
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in rows:
                if isinstance(row.get("payload_json"), str):
                    try:
                        row["payload_json"] = json.loads(row["payload_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return rows

    def update_status(
        self,
        patch_id: int,
        status: PatchStatus,
        *,
        action: str = "REVIEW",
        review_note: str = "",
        reviewed_by: str = "",
        risk_override: str | None = None,
    ) -> dict:
        """Update patch status, write review log. Returns {ok, errors}."""
        now = datetime.utcnow()

        # Read current patch
        with self.conn.cursor() as c:
            c.execute(
                "SELECT id, status FROM novel_knowledge_patch WHERE id = %s",
                (patch_id,),
            )
            row = c.fetchone()
            if not row:
                return {"ok": False, "errors": [f"Patch {patch_id} not found"]}

            previous_status = row["status"]

            if previous_status in TERMINAL_REVIEW_STATES:
                return {
                    "ok": False,
                    "errors": [
                        f"Cannot review patch in terminal state {previous_status}"
                    ],
                }

            # Update main table
            c.execute(
                """UPDATE novel_knowledge_patch
                   SET status = %s, review_note = %s,
                       reviewed_by = %s, reviewed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (status.value, review_note, reviewed_by, now, now, patch_id),
            )

            # Write review log with action and risk_override
            c.execute(
                """INSERT INTO novel_patch_review
                   (patch_id, action, previous_status, new_status,
                    review_note, reviewed_by, risk_override, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    patch_id,
                    action,
                    previous_status,
                    status.value,
                    review_note,
                    reviewed_by,
                    risk_override,
                    now,
                ),
            )

            self.conn.commit()
            return {"ok": True, "errors": []}
