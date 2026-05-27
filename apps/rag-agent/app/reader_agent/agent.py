"""@NB-AGENT-STEP ReaderAgent orchestration with ReAct loop (v2 closure).

Key runtime closure fixes:
  1. Creates top-level orchestration run — all tool calls share one run_id.
  2. ToolExecutor injected with MysqlToolCallStore — tool calls persist to DB.
  3. audit executes exactly once, with answer injected before execution.
  4. hybrid_search items → L2 EvidenceMemory.
  5. All fields passed to mode runners.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent_runtime.schemas import ToolCallStep
from app.agent_runtime.tool_executor import ToolExecutor
from app.agent_runtime.tool_registry import ToolRegistry
from app.clients.deepseek_client import deepseek_client
from app.reader_agent.answer_polish import audit, polish
from app.reader_agent.memory import MemoryManager
from app.reader_agent.memory.session_memory import SessionTurn
from app.reader_agent.memory.working_memory import ToolCallRecord as WmToolCall
from app.reader_agent.planner import plan as reader_plan
from app.reader_agent.schemas import ReaderRequest, ReaderResponse
from app.reader_agent.states import READER_TRANSITIONS, ReaderState
from app.reader_agent.tools import register_all_tools

logger = logging.getLogger(__name__)

_REACT_SYSTEM_PROMPT = """你是一个阅读助手工具调度器。你的任务是观察已执行的工具及其结果，然后决定下一步操作。

可用决策：
- "continue": 继续执行下一个计划步骤
- "done": 已有足够信息生成回答，停止执行
- "retry_tool": 需要重新运行某个工具获取更多信息（需指定 tool_name）

回答必须是严格的 JSON 格式，不要包含其他文字：
{"decision": "continue" | "done" | "retry_tool", "tool_name": null | "工具名称", "reason": "解释"}
"""


class ReaderAgent:
    """@NB-ENTRYPOINT ReaderAgent with ReAct tool loop.

    Fixes #1-#5: tool_sequence consumption, field completeness,
    hybrid_search → memory, audit injection, tool call trace.
    """

    def __init__(
        self,
        conn=None,
        memory_manager: MemoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.conn = conn
        self.memory_manager = memory_manager

        if tool_registry is not None:
            self.tool_registry = tool_registry
        else:
            self.tool_registry = ToolRegistry()
            register_all_tools(self.tool_registry, conn)

        # Fix #4: Inject MysqlToolCallStore so orchestrator tool calls persist
        tool_call_store = None
        if conn is not None:
            try:
                from app.agent_runtime.tool_call_store import MysqlToolCallStore
                tool_call_store = MysqlToolCallStore(conn)
            except Exception:
                pass
        self.tool_executor = ToolExecutor(self.tool_registry, tool_call_store=tool_call_store)

    async def run(
        self,
        request: ReaderRequest,
        tool_sequence: list[ToolCallStep] | None = None,
    ) -> ReaderResponse:
        """Execute ReaderAgent as a ReAct loop over tool_sequence.

        Runtime closure fixes:
        1. Accepts external tool_sequence; if None, re-call planner.
        2. _default_sequence passes ALL ReaderRequest fields.
        3. hybrid_search items → L2 EvidenceMemory.
        4. audit executes exactly once, with answer injected.
        5. Top-level orchestration run created; all tool calls share run_id.
        """
        # ── Fix #1: Accept from param or request, then re-plan ───
        if tool_sequence is None:
            tool_sequence = request.tool_sequence
        if tool_sequence is None:
            plan_result = reader_plan(
                book_id=request.book_id,
                question=request.question,
                preferred_mode=request.mode if request.mode != "auto" else "auto",
            )
            tool_sequence = plan_result.tool_sequence

        # ── Fix #3: Create top-level orchestration run ──────────
        orchestration_run_id: int | None = None
        orchestration_step_id: int | None = None
        if self.conn is not None:
            try:
                from app.agent_runtime.run_store import MysqlAgentRunStore
                run_store = MysqlAgentRunStore(self.conn)
                orchestration_run_id = run_store.create_run(
                    agent_name="ReaderAgent",
                    mode="orchestrator",
                    payload={
                        "book_id": request.book_id,
                        "question": request.question[:200],
                        "tool_sequence": [s.tool_name for s in tool_sequence],
                        "mode": request.mode,
                        "target_name": request.target_name,
                        "target_type": request.target_type,
                    },
                )
                orchestration_step_id = run_store.create_step(
                    orchestration_run_id, "ORCHESTRATE",
                    payload={"tool_count": len(tool_sequence)},
                    step_order=0,
                )
                logger.info(
                    "Orchestration run %d created for mode=%s question=%s",
                    orchestration_run_id, request.mode, request.question[:50],
                )
            except Exception as e:
                logger.warning("Failed to create orchestration run: %s", e)

        # ── Reset working + evidence memory ─────────────────────
        if self.memory_manager:
            self.memory_manager.reset_run()
            self.memory_manager.l1.status = "planning"
            self.memory_manager.l1.set_plan({
                "mode": request.mode,
                "question": request.question,
                "book_id": request.book_id,
                "target_name": request.target_name,
                "target_type": request.target_type,
            })

        # ── Accumulated state ───────────────────────────────────
        accumulated: dict[str, Any] = {
            "answer": "",
            "citations": [],
            "evidence": [],
            "analysis": {},
            "timeline": [],
            "errors": [],
            "run_id": orchestration_run_id,  # Fix #5: set at start
            "trace_id": None,
            "search_items": [],
        }

        if self.memory_manager:
            self.memory_manager.l1.status = "executing"

        provider = request.options.provider
        MAX_TOOL_CALLS = 4
        tool_calls_count = 0
        current_idx = 0
        executed_tools: list[dict[str, Any]] = []

        while tool_calls_count < MAX_TOOL_CALLS and current_idx < len(tool_sequence):
            step = tool_sequence[current_idx]
            tool_params = dict(step.params)
            if "provider" not in tool_params:
                tool_params["provider"] = provider

            # ── Fix #5: audit step — inject answer, run once ──
            # Skip generic execution for audit; run here with answer injected
            if step.tool_name == "audit":
                curr = accumulated.get("answer", "") or ""
                if curr:
                    audit_params = {"answer": curr, "provider": provider}
                    audit_record = await self.tool_executor.execute(
                        "audit", payload=audit_params,
                        run_id=orchestration_run_id, step_id=orchestration_step_id,
                    )
                    tool_calls_count += 1
                    if audit_record.status == "SUCCESS" and audit_record.output_json:
                        polished_text = audit_record.output_json.get("polished", "") or ""
                        if polished_text:
                            accumulated["answer"] = polished_text
                        for w in (audit_record.output_json.get("warnings", []) or []):
                            accumulated["errors"].append(f"[audit] {w}")
                    executed_tools.append({"tool_name": "audit", "status": audit_record.status, "has_output": True})
                if self.memory_manager:
                    self.memory_manager.l1.add_observation(f"audit: {'skipped (no answer)' if not curr else 'done'}")
                current_idx += 1
                continue

            # ── Execute tool ──────────────────────────────────────
            record = await self.tool_executor.execute(
                step.tool_name,
                payload=tool_params,
                run_id=orchestration_run_id,
                step_id=orchestration_step_id,
            )
            tool_calls_count += 1

            # ── hybrid_search → L2 EvidenceMemory ──────────────
            if step.tool_name == "hybrid_search":
                items = (record.output_json or {}).get("items", [])
                if items:
                    accumulated["search_items"] = items
                    if self.memory_manager:
                        from app.agent_runtime.schemas import EvidenceItem, EvidenceLevel
                        for item in items[:10]:
                            try:
                                ev = EvidenceItem(
                                    source_type=str(item.get("source", "chunk")),
                                    source_id=int(item.get("id", 0)),
                                    chapter_id=item.get("chapter_id"),
                                    excerpt=str(item.get("excerpt", "") or "")[:300],
                                    evidence_level=EvidenceLevel.NEAR,
                                    relevance_score=float(item.get("score", 0.5)),
                                )
                                self.memory_manager.l2.add_item(ev)
                            except Exception:
                                pass

            # ── Record working memory ──────────────────────────
            if self.memory_manager:
                self.memory_manager.l1.record_tool_call(
                    WmToolCall(
                        tool_name=step.tool_name,
                        status=record.status,
                        input_json=record.input_json,
                        output_json=record.output_json,
                        error=record.error,
                    )
                )

            # ── Handle tool failure + merge success ────────────
            if record.status == "FAILED":
                error_msg = f"Tool {step.tool_name} failed: {record.error}"
                logger.warning(error_msg)
                accumulated["errors"].append(error_msg)
                executed_tools.append({"tool_name": step.tool_name, "status": "FAILED", "has_output": False})
                if step.fallback_tool and tool_calls_count < MAX_TOOL_CALLS:
                    fb = await self.tool_executor.execute(
                        step.fallback_tool, payload=tool_params,
                        run_id=orchestration_run_id, step_id=orchestration_step_id,
                    )
                    tool_calls_count += 1
                    executed_tools.append({"tool_name": step.fallback_tool, "status": fb.status, "has_output": bool(fb.output_json)})
                    if fb.status == "SUCCESS":
                        self._merge_output(accumulated, fb.output_json or {})
                        if self.memory_manager:
                            self.memory_manager.l1.add_observation(f"{step.tool_name} → fallback {step.fallback_tool}")
            else:
                if record.output_json:
                    self._merge_output(accumulated, record.output_json)
                executed_tools.append({"tool_name": step.tool_name, "status": record.status, "has_output": bool(record.output_json)})
                if self.memory_manager:
                    self.memory_manager.l1.add_observation(f"{step.tool_name}: {record.status}")

            # ── ReAct think step (deepseek only) ────────────────
            if provider == "deepseek":
                decision = await self._react_think(
                    accumulated=accumulated, tool_sequence=tool_sequence,
                    current_index=current_idx, just_executed_tool=step.tool_name,
                    executed_tools=executed_tools,
                )
                if decision:
                    if decision.get("decision") == "done":
                        if self.memory_manager:
                            self.memory_manager.l1.add_observation(f"ReAct: stop after {step.tool_name}")
                        break
                    elif decision.get("decision") == "retry_tool":
                        rt = decision.get("tool_name")
                        if rt:
                            ridx = next((i for i, s in enumerate(tool_sequence) if s.tool_name == rt), None)
                            if ridx is not None:
                                if self.memory_manager:
                                    self.memory_manager.l1.add_observation(f"ReAct: retry '{rt}'")
                                current_idx = ridx
                                continue
            current_idx += 1

        # ── Finalize orchestration run ──────────────────────────
        if self.conn is not None and orchestration_run_id is not None:
            try:
                from app.agent_runtime.run_store import MysqlAgentRunStore
                run_store = MysqlAgentRunStore(self.conn)
                run_store.finish_step(
                    orchestration_step_id, "SUCCESS",
                    payload={
                        "tool_calls": tool_calls_count,
                        "has_answer": bool(accumulated.get("answer")),
                        "citation_count": len(accumulated.get("citations", [])),
                    },
                )
                run_store.finish_run(
                    orchestration_run_id, self._final_status(accumulated).value,
                    payload={
                        "answer_length": len(accumulated.get("answer", "") or ""),
                        "tool_calls": tool_calls_count,
                    },
                )
            except Exception as e:
                logger.warning("Failed to finalize orchestration run: %s", e)

        # ── Model fallback: if mode returned INSUFFICIENT_EVIDENCE ──
        final_answer = accumulated.get("answer") or ""
        # Analyze/trace modes return "INSUFFICIENT_EVIDENCE" as answer string
        is_insufficient = (
            not final_answer
            or "INSUFFICIENT_EVIDENCE" in final_answer.upper()
            or "无法回答" in final_answer
            or "无法确认" in final_answer
        )
        if is_insufficient and request.question and request.mode in ("answer", "analyze", "trace", "enrich"):
            # No evidence found — fallback to model knowledge
            try:
                from app.qa.unified_pipeline import _generate_then_retrieve
                book_title = ""
                if self.conn:
                    try:
                        with self.conn.cursor() as c:
                            c.execute("SELECT title FROM novel_book WHERE id = %s", (request.book_id,))
                            row = c.fetchone()
                            book_title = row["title"] if row else ""
                    except Exception:
                        pass
                _fb = await _generate_then_retrieve(request.question, book_title, provider, book_id=request.book_id, conn=self.conn)
                if _fb:
                    final_answer = _fb
                    accumulated["answer"] = _fb
                    accumulated["errors"].append("(模型知识回答，非检索证据)")
            except Exception as e:
                logger.warning("Model fallback failed: %s", e)

        # ── Build final response ────────────────────────────────
        if final_answer:
            final_answer = polish(final_answer, provider=provider)
            audit_result = audit(final_answer)
            if audit_result.warnings:
                accumulated["errors"].extend(f"[agent audit] {w}" for w in audit_result.warnings)

        response = ReaderResponse(
            mode=request.mode,
            status=self._final_status(accumulated),
            answer=final_answer,
            citations=accumulated.get("citations", []) or [],
            evidence=accumulated.get("evidence", []) or [],
            analysis=accumulated.get("analysis") or {},
            timeline=accumulated.get("timeline", []) or [],
            run_id=orchestration_run_id or accumulated.get("run_id"),
            trace_id=accumulated.get("trace_id"),
            errors=accumulated.get("errors", []),
        )

        # ── Record turn in session memory ───────────────────────
        if self.memory_manager and response.run_id:
            try:
                self.memory_manager.l0.record_turn(SessionTurn(
                    mode=response.mode,
                    question=request.question,
                    optimized_question=request.question,
                    answer_preview=response.answer[:150] if response.answer else "",
                    target_name=request.target_name,
                    target_type=request.target_type,
                    book_id=request.book_id,
                    run_id=response.run_id or 0,
                    evidence_ids=[c.source_id for c in (response.citations or [])[:10] if hasattr(c, "source_id")],
                    provider=provider,
                ))
                self.memory_manager.l1.status = "done"
            except Exception as e:
                logger.warning("Session turn record failed: %s", e)

        return response

    async def _react_think(
        self,
        accumulated: dict[str, Any],
        tool_sequence: list[ToolCallStep],
        current_index: int,
        just_executed_tool: str,
        executed_tools: list[dict[str, Any]],
        provider: str = "deepseek",
    ) -> dict[str, Any] | None:
        if provider != "deepseek":
            return None
        remaining = tool_sequence[current_index:] if current_index < len(tool_sequence) else []
        executed_summary = "\n".join(
            f"  - {t['tool_name']}: status={t['status']}, "
            f"has_output={'yes' if t.get('has_output') else 'no'}"
            for t in executed_tools
        ) if executed_tools else "  （无）"
        remaining_summary = "\n".join(
            f"  - {s.tool_name}: {s.description}" for s in remaining
        ) if remaining else "  （无）"
        answer_preview = (accumulated.get("answer") or "")[:300]

        try:
            result = await deepseek_client.chat_json(
                messages=[
                    {"role": "system", "content": _REACT_SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"## 已执行\n{executed_summary}\n\n"
                        f"## 当前回答\n{answer_preview or '（无）'}\n\n"
                        f"## 剩余步骤\n{remaining_summary}\n\n"
                        f"## 刚执行的工具\n{just_executed_tool}\n\n"
                        "请决定下一步。"
                    )},
                ],
                temperature=0.3, max_tokens=512,
            )
            if isinstance(result, dict) and result.get("decision") in ("continue", "done", "retry_tool"):
                logger.info("ReAct: %s (tool=%s, reason=%s)", result["decision"], result.get("tool_name"), result.get("reason", ""))
                return result
            return None
        except Exception as e:
            logger.warning("ReAct failed: %s", e)
            return None

    def _merge_output(self, acc: dict[str, Any], output: dict[str, Any]) -> None:
        """Merge a tool's output into accumulated result."""
        answer = output.get("answer")
        if answer and isinstance(answer, str) and answer.strip():
            acc["answer"] = answer
        if acc.get("run_id") is None:
            acc["run_id"] = output.get("run_id")
        if acc.get("trace_id") is None:
            acc["trace_id"] = output.get("trace_id")
        for key in ("citations", "evidence"):
            vals = output.get(key)
            if isinstance(vals, list):
                acc.setdefault(key, []).extend(vals)
        analysis = output.get("analysis")
        if analysis and isinstance(analysis, dict) and analysis:
            acc["analysis"] = analysis
        timeline = output.get("timeline")
        if isinstance(timeline, list):
            acc["timeline"] = timeline if not acc.get("timeline") else acc["timeline"] + timeline
        errors = output.get("errors")
        if isinstance(errors, list):
            acc.setdefault("errors", []).extend(errors)
        elif errors and isinstance(errors, str):
            acc.setdefault("errors", []).append(errors)

    def _default_sequence(self, request: ReaderRequest) -> list[ToolCallStep]:
        """Build a default single-mode sequence from the request.

        Fix #2: Pass ALL relevant fields from ReaderRequest.
        """
        base_params: dict[str, Any] = {
            "question": request.question,
            "book_id": request.book_id,
            "top_k": request.options.top_k,
        }
        if request.target_name:
            base_params["target_name"] = request.target_name
        if request.target_type:
            base_params["target_type"] = request.target_type
        if request.analysis_type:
            base_params["analysis_type"] = request.analysis_type
        if request.trace_target_type:
            base_params["trace_target_type"] = request.trace_target_type
        if request.chapter_range:
            base_params["chapter_range"] = request.chapter_range
        if request.session_id:
            base_params["session_id"] = request.session_id
        if request.issue_type:
            base_params["issue_type"] = request.issue_type
        if request.target:
            base_params["target"] = request.target
        if request.evidence:
            base_params["evidence"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in request.evidence]

        return [
            ToolCallStep(
                tool_name="hybrid_search",
                params={
                    "query": request.question,
                    "book_id": request.book_id,
                    "top_k": request.options.top_k,
                    "entity_name": request.target_name or "",
                },
                description="检索相关章节和事实证据",
            ),
            ToolCallStep(
                tool_name=request.mode,
                params=dict(base_params),
                description=f"执行 {request.mode} 模式",
            ),
            ToolCallStep(
                tool_name="audit",
                params={"provider": request.options.provider},
                description="审核输出质量",
            ),
        ]

    def _final_status(self, acc: dict[str, Any]) -> ReaderState:
        errors = acc.get("errors", [])
        has_answer = bool(acc.get("answer"))
        has_citations = bool(acc.get("citations"))
        if errors and not has_answer:
            return ReaderState.FAILED
        if not has_answer and not has_citations:
            return ReaderState.INSUFFICIENT_EVIDENCE
        if errors:
            return ReaderState.RESPONDED
        return ReaderState.RESPONDED
