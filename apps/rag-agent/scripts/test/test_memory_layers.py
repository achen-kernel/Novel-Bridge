"""@NB-ENTRYPOINT Stage 6H memory layer tests.

Tests MemoryManager, L0/L1/L2 layers, and extensibility interface.

Run:
    python -B scripts/test/test_memory_layers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.agent_runtime.schemas import EvidenceItem, EvidenceLevel
from app.reader_agent.memory import MemoryManager, EvidenceMemory, SessionMemory, WorkingMemory
from app.reader_agent.memory.base import MemoryInterface
from app.reader_agent.memory.session_memory import SessionTurn, UserPreferences
from app.reader_agent.memory.working_memory import ToolCallRecord


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return ok


def create_sample_turn() -> SessionTurn:
    return SessionTurn(
        mode="analyze",
        question="分析孙悟空的人物形象",
        optimized_question="请基于证据分析孙悟空的人物形象",
        answer_preview="孙悟空是核心人物",
        target_name="孙悟空",
        target_type="character",
        book_id=6,
        run_id=101,
        evidence_ids=[1, 2, 3],
    )


def test_memory_layers() -> int:
    failures: list[str] = []
    print("Memory layer smoke test")

    # ── L0: SessionMemory ──────────────────────────────────────────

    sm = SessionMemory(session_id=42)
    ok = sm.empty()
    check("L0.空会话 isEmpty", ok, f"session_id={sm.session_id}")

    turn = create_sample_turn()
    sm.record_turn(turn)

    ok = sm.turn_count == 1 and sm.current_target_name == "孙悟空"
    check("L0.记录轮次", ok, f"turns={sm.turn_count} target={sm.current_target_name}")

    ok = sm.book_id == 6
    check("L0.book_id 继承", ok, f"book_id={sm.book_id}")

    ok = sm.last_turn is not None and sm.last_turn.run_id == 101
    check("L0.last_turn", ok, f"run_id={sm.last_turn.run_id}")

    ok = "西游记" in sm.get_context_summary()
    check("L0.上下文摘要", ok)

    ok = sm.recent_questions == ["分析孙悟空的人物形象"]
    check("L0.recent_questions", ok)

    sm.clear()
    ok = sm.empty()
    check("L0.clear", ok)

    # ── Serialization ──────────────────────────────────────────────

    sm2 = SessionMemory(session_id=43)
    sm2.record_turn(create_sample_turn())
    d = sm2.to_dict()
    ok = d["turn_count"] == 1 and d["current_target_name"] == "孙悟空"
    check("L0.to_dict", ok, f"target={d.get('current_target_name')}")

    # ── Preferences ────────────────────────────────────────────────

    prefs = UserPreferences(provider="deepseek", concise=True)
    sm3 = SessionMemory(session_id=44)
    sm3.preferences = prefs
    ok = sm3.preferences.provider == "deepseek" and sm3.preferences.concise
    check("L0.偏好设置", ok, f"provider={sm3.preferences.provider}")

    # ── L1: WorkingMemory ──────────────────────────────────────────

    wm = WorkingMemory()
    ok = wm.empty()
    check("L1.空状态", ok)

    wm.set_plan({"mode": "trace", "target": "孙悟空"})
    ok = wm.plan is not None and wm.plan["mode"] == "trace"
    check("L1.设置 plan", ok, f"mode={wm.plan['mode']}")

    wm.record_tool_call(ToolCallRecord(
        tool_name="hybrid_search", status="success", duration_ms=320.0
    ))
    wm.record_tool_call(ToolCallRecord(
        tool_name="entity_lookup", status="failed", error="not found"
    ))
    ok = len(wm.tool_calls) == 2
    check("L1.工具调用记录", ok, f"calls={len(wm.tool_calls)}")

    wm.add_observation("找到 5 条证据")
    wm.add_observation("实体孙悟空已确认")
    ok = len(wm.observations) == 2
    check("L1.观察记录", ok, f"obs={len(wm.observations)}")

    wm.add_clarification("您指的是哪个角色？", options=["孙悟空", "唐僧"])
    ok = len(wm.pending_clarifications) == 1
    check("L1.待澄清问题", ok, f"clarifications={len(wm.pending_clarifications)}")

    # Resolve clarification
    wm.resolve_clarification()
    ok = len(wm.pending_clarifications) == 0
    check("L1.澄清已解决", ok)

    wm.clear()
    ok = wm.empty() and wm.status == "idle"
    check("L1.clear", ok)

    # ── Serialization ──────────────────────────────────────────────

    wm2 = WorkingMemory()
    wm2.set_plan({"mode": "answer"})
    d = wm2.to_dict()
    ok = d["status"] == "planning" and d["plan"]["mode"] == "answer"
    check("L1.to_dict", ok, f"status={d['status']}")

    # ── L2: EvidenceMemory ─────────────────────────────────────────

    em = EvidenceMemory()
    ok = em.empty()
    check("L2.空状态", ok)

    item = EvidenceItem(
        source_type="chunk",
        source_id=1,
        chapter_id=10,
        excerpt="孙悟空被压五行山下",
        evidence_level=EvidenceLevel.DIRECT,
        relevance_score=0.95,
    )
    em.add_item(item)

    ok = len(em.items) == 1 and len(em.citations) == 1
    check("L2.添加证据项", ok, f"items={len(em.items)} citations={len(em.citations)}")

    em.trace_id = 42
    em.query = "孙悟空"
    ok = em.trace_id == 42 and em.query == "孙悟空"
    check("L2.trace_id + query", ok, f"trace_id={em.trace_id}")

    em.clear()
    ok = em.empty()
    check("L2.clear", ok)

    # ── Serialization ──────────────────────────────────────────────

    em2 = EvidenceMemory()
    em2.add_item(item)
    d = em2.to_dict()
    ok = d["item_count"] == 1 and d["citation_count"] == 1
    check("L2.to_dict", ok, f"items={d['item_count']} citations={d['citation_count']}")

    # ── MemoryManager facade ───────────────────────────────────────

    mm = MemoryManager(session_id=99)
    ok = mm.l0.session_id == 99
    check("MM.创建", ok, f"session_id={mm.l0.session_id}")

    # Record turn via facade
    mm.l0.record_turn(create_sample_turn())
    ok = mm.l0.turn_count == 1
    check("MM.记录轮次", ok)

    # Working memory
    mm.l1.set_plan({"mode": "analyze"})
    ok = mm.l1.plan is not None
    check("MM.working memory", ok, f"plan_mode={mm.l1.plan['mode']}")

    # Evidence memory
    mm.l2.add_item(item)
    ok = len(mm.l2.items) == 1
    check("MM.evidence memory", ok)

    # Reset run clears L1+L2 but preserves L0
    mm.reset_run()
    ok = mm.l0.turn_count == 1 and mm.l1.empty() and mm.l2.empty()
    check("MM.reset_run 保留 L0", ok, f"L0={mm.l0.turn_count} L1_empty={mm.l1.empty()} L2_empty={mm.l2.empty()}")

    # ── Interface contract ─────────────────────────────────────────

    for name, instance in [("SessionMemory", sm), ("WorkingMemory", wm), ("EvidenceMemory", em)]:
        ok = isinstance(instance, MemoryInterface)
        check(f"Interface.{name} 实现 MemoryInterface", ok)
        ok = instance.namespace != ""
        check(f"Interface.{name}.namespace", ok, f"ns={instance.namespace}")

    # ── Multi-turn ─────────────────────────────────────────────────

    mm2 = MemoryManager(session_id=100)
    mm2.l0.record_turn(create_sample_turn())
    turn2 = SessionTurn(
        mode="trace",
        question="追踪他和唐僧关系变化",
        optimized_question="请按章节时间线追踪",
        answer_preview="关系变化时间线",
        target_name="孙悟空,唐僧",
        target_type="relation",
        book_id=6,
        run_id=102,
        evidence_ids=[4, 5],
    )
    mm2.l0.record_turn(turn2)
    ok = mm2.l0.turn_count == 2
    check("MM.多轮记录", ok)

    ok = mm2.l0.recent_questions == ["分析孙悟空的人物形象", "追踪他和唐僧关系变化"]
    check("MM.最近问题", ok, f"questions={mm2.l0.recent_questions}")

    ok = "孙悟空" in mm2.l0.recent_targets
    check("MM.最近目标", ok, f"targets={mm2.l0.recent_targets}")

    # ── to_dict ────────────────────────────────────────────────────

    mm3 = MemoryManager(session_id=101)
    mm3.l0.record_turn(create_sample_turn())
    mm3.l1.set_plan({"mode": "answer"})
    d = mm3.to_dict()
    ok = d["l0"] is not None and d["l1"] is not None
    check("MM.to_dict", ok, f"keys={list(d.keys())}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All memory layer tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_memory_layers())
