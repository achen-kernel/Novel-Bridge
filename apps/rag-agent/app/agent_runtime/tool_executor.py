"""Tool execution wrapper with a stable result shape and optional persistence."""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from typing import Any

from app.agent_runtime.schemas import ToolCallRecord
from app.agent_runtime.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Execute tools with optional persistence via tool_call_store.

    When tool_call_store is provided, each tool call is persisted to the
    novel_tool_call table.  Without a store, only the in-memory ToolCallRecord
    is returned (original skeleton behavior unchanged).
    """

    def __init__(
        self,
        registry: ToolRegistry,
        tool_call_store: Any = None,  # MysqlToolCallStore | None
    ) -> None:
        self.registry = registry
        self.tool_call_store = tool_call_store

    async def execute(
        self,
        tool_name: str,
        *,
        run_id: int | None = None,
        step_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ToolCallRecord:
        payload = payload or {}

        # ---- Persist start if store available ----
        db_call_id = None
        if self.tool_call_store is not None:
            try:
                db_call_id = self.tool_call_store.create_tool_call(
                    tool_name,
                    agent_run_id=run_id,
                    agent_step_id=step_id,
                    input_json=payload,
                    status="RUNNING",
                )
            except Exception as e:
                logger.warning("Tool call start persistence failed: %s", e)

        # ---- Execute ----
        record = ToolCallRecord(
            tool_name=tool_name,
            run_id=run_id,
            step_id=step_id,
            input_json=payload,
            status="RUNNING",
        )
        try:
            fn = self.registry.get(tool_name)
            result = fn(**payload)
            if inspect.isawaitable(result):
                result = await result
            record.output_json = result if isinstance(result, dict) else {"result": result}
            record.status = "SUCCESS"
        except Exception as exc:
            record.status = "FAILED"
            record.error = str(exc)
        finally:
            record.finished_at = datetime.utcnow()

        # ---- Persist finish if store available ----
        if self.tool_call_store is not None and db_call_id is not None:
            try:
                self.tool_call_store.finish_tool_call(
                    db_call_id,
                    status=record.status,
                    output_json=record.output_json,
                    error_message=record.error or "",
                )
            except Exception as e:
                logger.warning("Tool call finish persistence failed: %s", e)

        return record
