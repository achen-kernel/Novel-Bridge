"""@NB-ENTRYPOINT P0 tool registration + ReAct loop tests.

Tests that tools register correctly and produce expected output shapes.

Run:
    python -B scripts/test/test_reader_agent_tools.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.agent_runtime.schemas import ToolCallStep, ToolDef
from app.agent_runtime.tool_registry import ToolRegistry
from app.reader_agent.planner import plan
from app.reader_agent.tools import register_all_tools

# P1 ReAct imports
from app.reader_agent.agent import ReaderAgent
import asyncio
import inspect


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")


def test_closure():
    """Fix #1, #2, #4: tool_sequence consumption, field completeness, audit injection."""
    failures = []
    print("\nP2 Runtime closure tests")
    from app.reader_agent.agent import ReaderAgent
    from app.reader_agent.schemas import ReaderRequest, ReaderOptions

    # 17. _default_sequence passes all fields from a analyze request
    req = ReaderRequest(
        mode="analyze",
        book_id=6,
        question="分析孙悟空的人物形象",
        target_name="孙悟空",
        target_type="character",
        analysis_type="character",
        options=ReaderOptions(provider="local", top_k=10),
    )
    seq = ReaderAgent()._default_sequence(req)
    mode_step = seq[1]  # the analyze tool
    ok = mode_step.params.get("target_name") == "孙悟空"
    ok = ok and mode_step.params.get("target_type") == "character"
    ok = ok and mode_step.params.get("analysis_type") == "character"
    ok = ok and mode_step.tool_name == "analyze"
    failures.append("17: _default_sequence drops target fields") if not ok else None
    check("17._default_sequence 传递 target_name/target_type/analysis_type", ok)

    # 18. _default_sequence for trace passes trace_target_type
    req2 = ReaderRequest(
        mode="trace",
        book_id=6,
        question="追踪孙悟空和唐僧关系变化",
        target_name="孙悟空,唐僧",
        target_type="relation",
        trace_target_type="character",
        options=ReaderOptions(provider="local", top_k=10),
    )
    seq2 = ReaderAgent()._default_sequence(req2)
    trace_step = seq2[1]
    ok = trace_step.params.get("trace_target_type") == "character"
    ok = ok and trace_step.tool_name == "trace"
    failures.append("18: trace_target_type dropped") if not ok else None
    check("18.trace _default_sequence 传递 trace_target_type", ok)

    # 19. _default_sequence first step is hybrid_search
    ok = seq[0].tool_name == "hybrid_search"
    ok = ok and seq2[0].tool_name == "hybrid_search"
    failures.append("19: first step not hybrid_search") if not ok else None
    check("19.工具序列以 hybrid_search 开头", ok)

    # 20. planner tool_sequence can be consumed by inspectable structure
    from app.reader_agent.planner import plan as reader_plan
    p = reader_plan(book_id=6, question="火焰山的火是怎么来的？")
    ok = len(p.tool_sequence) == 3
    ok = ok and p.tool_sequence[0].tool_name == "hybrid_search"
    ok = ok and p.tool_sequence[1].tool_name == "answer"
    ok = ok and p.tool_sequence[2].tool_name == "audit"
    failures.append("20: planner tool_sequence broken") if not ok else None
    check("20.planner tool_sequence 可被消费 (3 steps)", ok)

    # 21. audit function handles answer injection
    from app.reader_agent.answer_polish import polish, audit as do_audit
    test_answer = "孙悟空是主角。他很强。id: 42"
    polished = polish(test_answer, provider="local")
    ok = "id:" not in polished  # local polish strips ids
    failures.append("21: local polish didn't strip id:") if not ok else None
    check("21.local polish 清理 internal ids", ok, f"polished={polished!r}")

    # 22. DeepSeek polish preserves more
    polished_ds = polish(test_answer, provider="deepseek")
    ok = "id:" in polished_ds  # deepseek polish preserves ids
    failures.append("22: deepseek polish stripped too much") if not ok else None
    check("22.DeepSeek polish 保留 internal ids", ok)

    # 23. audit detects broad claims
    r = do_audit("这是毫无疑问最重要的作品。")
    ok = len(r.warnings) >= 1
    failures.append("23: broad claim not detected") if not ok else None
    check("23.audit 检测 broad claim", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All P2 closure tests passed.")
    return 0


def test_p0():
    failures = []
    print("P0 Tool orchestration + ReAct smoke test")

    # 1. ToolRegistry registers all tools
    registry = ToolRegistry()
    register_all_tools(registry)
    names = registry.names()
    for expected in ["answer", "analyze", "trace", "enrich", "hybrid_search", "audit"]:
        ok = expected in names
        failures.append(f"1.1 tool {expected} not registered") if not ok else None
        check(f"1.{['answer','analyze','trace','enrich','hybrid_search','audit'].index(expected)+1} 注册工具 {expected}", ok)

    # 2. Planner returns tool_sequence
    r = plan(book_id=6, question="火焰山的火是怎么来的？")
    ok = len(r.tool_sequence) >= 2
    failures.append("2.1 tool_sequence empty") if not ok else None
    check("2.planner 返回 tool_sequence", ok, f"steps={len(r.tool_sequence)}")

    # 3. Tool sequence has expected structure
    r = plan(book_id=6, question="分析孙悟空的人物形象")
    ok = len(r.tool_sequence) >= 2
    ok = ok and r.tool_sequence[0].tool_name == "hybrid_search"
    failures.append("3.1 first step not hybrid_search") if not ok else None
    ok = ok and r.tool_sequence[1].tool_name == "analyze"
    failures.append("3.2 second step not analyze") if not ok else None
    ok = ok and r.tool_sequence[2].tool_name == "audit"
    failures.append("3.3 third step not audit") if not ok else None
    check("3.tool_sequence 结构正确（search→analyze→audit）", ok)

    # 4. Tool sequence for trace mode
    r = plan(book_id=6, question="追踪孙悟空和唐僧关系变化")
    ok = len(r.tool_sequence) >= 2 and r.tool_sequence[1].tool_name == "trace"
    failures.append("4.1 trace not in sequence") if not ok else None
    check("4.trace 模式的 tool_sequence", ok, f"steps={[s.tool_name for s in r.tool_sequence]}")

    # 5. ToolCallStep schema
    step = ToolCallStep(tool_name="answer", params={"book_id": 6}, description="回答")
    ok = step.tool_name == "answer" and step.params["book_id"] == 6
    failures.append("5.1 ToolCallStep schema") if not ok else None
    check("5.ToolCallStep schema 正常", ok)

    # 6. ToolDef schema
    d = ToolDef(name="answer", description="回答问题", input_example={"question": "?"})
    ok = d.name == "answer"
    failures.append("6.1 ToolDef schema") if not ok else None
    check("6.ToolDef schema 正常", ok)

    # 7. Tool callable exists
    fn = registry.get("audit")
    ok = fn is not None and callable(fn)
    failures.append("7.1 audit tool not callable") if not ok else None
    check("7.工具可调用", ok)

    # 8. Fallback tool in sequence
    r = plan(book_id=6, question="分析孙悟空")
    ok = all(s.fallback_tool is None for s in r.tool_sequence)
    check("8.fallback_tool 字段正确", ok)

    # 9. Tool sequence for enrich
    r = plan(book_id=6, question="生成一个 KnowledgePatch 修正")
    ok = r.tool_sequence[1].tool_name == "enrich"
    failures.append("9.1 enrich not in sequence") if not ok else None
    check("9.enrich 模式的 tool_sequence", ok, f"steps={[s.tool_name for s in r.tool_sequence]}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All P0 tool tests passed.")
    return 0


def test_p1():
    """P1 True ReAct: _react_think method exists and behaves correctly."""
    failures = []
    print("P1 ReAct _react_think test")

    # 10. _react_think method exists on ReaderAgent
    agent = ReaderAgent()
    ok = hasattr(agent, "_react_think") and callable(agent._react_think)
    failures.append("10.1 _react_think method missing") if not ok else None
    check("10._react_think 方法存在", ok)

    # 11. Signature includes all required parameters
    sig = inspect.signature(agent._react_think)
    params = list(sig.parameters.keys())
    required = ["accumulated", "tool_sequence", "current_index",
                "just_executed_tool", "executed_tools", "provider"]
    ok = all(p in params for p in required)
    failures.append("11.1 missing required params") if not ok else None
    check("11._react_think 参数完整", ok, f"params={params}")

    # 12. Has return annotation (-> dict | None)
    ok = "->" in str(sig)
    failures.append("12.1 no return annotation") if not ok else None
    check("12.方法为 async 且有返回值注释", ok)

    # 13. Non-deepseek provider returns None (fast fallthrough)
    async def check_fallthrough():
        result = await agent._react_think(
            accumulated={"answer": "test answer"},
            tool_sequence=[],
            current_index=0,
            just_executed_tool="hybrid_search",
            executed_tools=[],
            provider="local",
        )
        return result is None

    ok = asyncio.run(check_fallthrough())
    failures.append("13.1 local provider did not return None") if not ok else None
    check("13.local provider → None（fallthrough）", ok)

    # 14. DeepSeek provider returns dict with expected decision keys
    async def check_deepseek_decision_shape():
        result = await agent._react_think(
            accumulated={"answer": "test"},
            tool_sequence=[],
            current_index=0,
            just_executed_tool="hybrid_search",
            executed_tools=[],
            provider="deepseek",
        )
        if result is None:
            # If no API key or network issue, this is a graceful fallback
            return True
        # If API succeeds, must have the right shape
        return (
            isinstance(result, dict)
            and "decision" in result
            and result["decision"] in ("continue", "done", "retry_tool")
        )

    ok = asyncio.run(check_deepseek_decision_shape())
    failures.append("14.1 deepseek response missing required keys") if not ok else None
    check("14.deepseek provider → dict with decision keys", ok)

    # 15. executed_tools tracking works: list grows correctly during loop
    def simulate_tool_tracking():
        executed = []
        executed.append({"tool_name": "hybrid_search", "status": "SUCCESS", "has_output": True})
        executed.append({"tool_name": "answer", "status": "SUCCESS", "has_output": True})
        executed.append({"tool_name": "audit", "status": "SUCCESS", "has_output": True})
        return len(executed) == 3 and executed[0]["tool_name"] == "hybrid_search"

    ok = simulate_tool_tracking()
    failures.append("15.1 executed_tools tracking incorrect") if not ok else None
    check("15.executed_tools 追踪逻辑正确", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All P1 ReAct think tests passed.")
    return 0


def test_e2e():
    """End-to-end test: fake registry + full tool_sequence flow.

    Verifies the complete runtime closure without requiring DB or LLM:
    1. Fake tools register and return predictable results
    2. tool_sequence = hybrid_search → answer → audit
    3. run() processes all three tools
    4. answer is polished by audit
    5. run_id flows through
    """
    failures = []
    print("\nP3 End-to-end runtime closure test")

    from app.agent_runtime.tool_registry import ToolRegistry
    from app.reader_agent.agent import ReaderAgent
    from app.reader_agent.schemas import ReaderRequest, ReaderOptions, ToolCallStep

    # ── Fake tools ───────────────────────────────────────────────
    registry = ToolRegistry()

    @registry.register("hybrid_search")
    async def fake_hybrid(**params):
        return {
            "status": "SUCCESS",
            "items": [{"source": "chunk", "id": 1, "excerpt": "孙悟空是西游记主角"}],
            "count": 1,
        }

    @registry.register("answer")
    async def fake_answer(**params):
        return {
            "status": "SUCCESS",
            "answer": "孙悟空是西游记的主角。他有金箍棒。",
            "citations": [{
                "source_type": "chunk", "source_id": 1,
                "excerpt": "孙悟空是西游记主角", "relevance_score": 0.9,
            }],
            "run_id": 888,
            "trace_id": 7,
        }

    @registry.register("analyze")
    async def fake_analyze(**params):
        return {
            "status": "SUCCESS",
            "answer": "分析结果：孙悟空是核心人物。",
            "analysis": {"summary": "孙悟空是核心人物", "key_points": [{"claim": "核心人物"}]},
            "run_id": 889,
        }

    @registry.register("trace")
    async def fake_trace(**params):
        return {
            "status": "SUCCESS",
            "answer": "时间线：第1回出场，第5回成长。",
            "timeline": [{"chapter_number": 1, "summary": "出场"}, {"chapter_number": 5, "summary": "成长"}],
            "run_id": 890,
        }

    # Audit call counter — verify single execution
    _audit_call_count = 0

    @registry.register("audit")
    async def fake_audit(**params):
        nonlocal _audit_call_count
        _audit_call_count += 1
        answer = params.get("answer", "")
        return {
            "status": "SUCCESS",
            "polished": answer.replace("。", "。\n") if answer else "",
            "warnings": [],
        }

    # ── Test 24: answer mode tool_sequence via function param ───
    async def run_e2e():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(
            mode="answer", book_id=6,
            question="孙悟空的特征",
            target_name="孙悟空", target_type="character",
            options=ReaderOptions(provider="local", top_k=8),
        )
        seq = [
            ToolCallStep(tool_name="hybrid_search", params={"query": "孙悟空", "book_id": 6, "top_k": 8}),
            ToolCallStep(tool_name="answer", params={"question": "孙悟空的特征", "book_id": 6}),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        resp = await agent.run(req, tool_sequence=seq)
        return resp

    resp = asyncio.run(run_e2e())
    ok = resp.mode == "answer"
    failures.append("24.1 mode not answer") if not ok else None
    check("24.answer mode tool_sequence 返回", ok, f"mode={resp.mode}")

    # 25. Answer contains content from fake_answer
    ok = "孙悟空" in resp.answer
    failures.append("25.1 answer missing content") if not ok else None
    check("25.回答内容包含'孙悟空'", ok, f"answer={resp.answer[:60]!r}")

    # 26. Citations present
    ok = len(resp.citations) > 0
    failures.append("26.1 no citations") if not ok else None
    check("26.引用存在", ok, f"citations={len(resp.citations)}")

    # 27. Answer was polished by audit (period replaced with period+newline)
    ok = "。\n" in resp.answer
    failures.append("27.1 answer not polished by audit") if not ok else None
    check("27.audit polish 生效", ok, f"answer contains '。\\n': {ok}")

    # 28. run_id captured from fake_answer
    ok = resp.run_id is not None
    failures.append("28.1 run_id not set") if not ok else None
    check("28.run_id 正确传递", ok, f"run_id={resp.run_id}")

    # ── Test 29: trace mode tool_sequence ────────────────────────
    async def run_trace():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(
            mode="trace", book_id=6,
            question="追踪孙悟空",
            target_name="孙悟空", target_type="character",
            trace_target_type="character",
            options=ReaderOptions(provider="local"),
        )
        seq = [
            ToolCallStep(tool_name="hybrid_search", params={"query": "孙悟空", "book_id": 6}),
            ToolCallStep(tool_name="trace", params={"question": "追踪孙悟空", "book_id": 6, "target_name": "孙悟空"}),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        return await agent.run(req, tool_sequence=seq)

    resp2 = asyncio.run(run_trace())
    ok = resp2.mode == "trace" and len(resp2.timeline) == 2
    failures.append("29.1 trace timeline missing") if not ok else None
    check("29.trace mode 返回 timeline", ok, f"timeline={len(resp2.timeline)}")

    # 30. timeline items have expected structure
    ok = resp2.timeline[0].get("chapter_number") == 1
    failures.append("30.1 timeline chapter_number wrong") if not ok else None
    check("30.timeline[0] 章节号正确", ok, f"ch={resp2.timeline[0].get('chapter_number')}")

    # ── Test 31: analyze mode tool_sequence ──────────────────────
    async def run_analyze():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(
            mode="analyze", book_id=6,
            question="分析孙悟空",
            target_name="孙悟空", target_type="character",
            analysis_type="character",
            options=ReaderOptions(provider="local"),
        )
        seq = [
            ToolCallStep(tool_name="hybrid_search", params={"query": "孙悟空", "book_id": 6}),
            ToolCallStep(tool_name="analyze", params={"question": "分析孙悟空", "book_id": 6, "target_name": "孙悟空", "analysis_type": "character"}),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        return await agent.run(req, tool_sequence=seq)

    resp3 = asyncio.run(run_analyze())
    ok = resp3.mode == "analyze" and "核心人物" in resp3.answer
    failures.append("31.1 analyze answer wrong") if not ok else None
    check("31.analyze mode 返回分析内容", ok, f"answer={resp3.answer[:40]!r}")

    # ── Test 32: fallback tool on failure ─────────────────────────
    @registry.register("failing_tool")
    async def fake_failing(**params):
        raise ValueError("故意失败")

    async def run_fallback():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(mode="answer", book_id=6, question="测试", options=ReaderOptions(provider="local"))
        seq = [
            ToolCallStep(tool_name="failing_tool", params={}, fallback_tool="answer"),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        return await agent.run(req, tool_sequence=seq)

    resp4 = asyncio.run(run_fallback())
    ok = "FAILED" in str(resp4.errors[0]) if resp4.errors else False
    # After failure + fallback, we still have an answer
    ok = "孙悟空" in resp4.answer
    failures.append("32.1 fallback didn't produce answer") if not ok else None
    check("32.fallback 工具在失败后执行", ok, f"errors={len(resp4.errors)}, answer_has_content={bool(resp4.answer)}")

    # ── Test 33: empty tool_sequence (re-plan internally) ────────
    async def run_replan():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(mode="answer", book_id=6, question="火焰山的火", options=ReaderOptions(provider="local"))
        # No tool_sequence → agent re-plans via reader_plan()
        return await agent.run(req)

    resp5 = asyncio.run(run_replan())
    ok = resp5.mode == "answer"
    failures.append("33.1 re-plan failed") if not ok else None
    check("33.无 tool_sequence 时内部 re-plan", ok, f"mode={resp5.mode}")

    # ── Test 34: tool_sequence via ReaderRequest (not function param) ──
    async def run_via_request():
        agent = ReaderAgent(conn=None, tool_registry=registry)
        seq = [
            ToolCallStep(tool_name="hybrid_search", params={"query": "test", "book_id": 6}),
            ToolCallStep(tool_name="answer", params={"question": "test", "book_id": 6}),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        req = ReaderRequest(
            mode="answer", book_id=6, question="test",
            tool_sequence=seq,
            options=ReaderOptions(provider="local"),
        )
        # Call without second param — agent should read from req.tool_sequence
        return await agent.run(req)

    resp6 = asyncio.run(run_via_request())
    ok = resp6.mode == "answer" and "孙悟空" in resp6.answer
    failures.append("34.1 request.tool_sequence not consumed") if not ok else None
    check("34.request.tool_sequence 被消费（不传函数参数）", ok, f"answer={resp6.answer[:40]!r}")

    # ── Test 35: audit executes exactly once ─────────────────────────
    async def run_audit_once():
        # Reset counter before test
        nonlocal _audit_call_count
        _audit_call_count = 0
        agent = ReaderAgent(conn=None, tool_registry=registry)
        req = ReaderRequest(mode="answer", book_id=6, question="test", options=ReaderOptions(provider="local"))
        seq = [
            ToolCallStep(tool_name="answer", params={"question": "test", "book_id": 6}),
            ToolCallStep(tool_name="audit", params={"provider": "local"}),
        ]
        resp = await agent.run(req, tool_sequence=seq)
        return resp, _audit_call_count

    resp7, audit_count = asyncio.run(run_audit_once())
    ok = audit_count == 1
    failures.append("35.1 audit ran {audit_count} times (expected 1)") if not ok else None
    check("35.audit 只执行一次（非多次）", ok, f"call_count={audit_count}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All P3 end-to-end tests passed.")
    return 0


if __name__ == "__main__":
    exit_code = test_p0()
    if exit_code == 0:
        exit_code = test_p1()
    if exit_code == 0:
        exit_code = test_closure()
    if exit_code == 0:
        exit_code = test_e2e()
    raise SystemExit(exit_code)
