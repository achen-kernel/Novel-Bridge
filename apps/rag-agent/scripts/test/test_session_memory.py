"""@NB-ENTRYPOINT Stage 6F session memory + reference resolution tests.

Run:
    python -B scripts/test/test_session_memory.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.reader_agent.memory.session_memory import SessionMemory, SessionTurn
from app.reader_agent.reference_resolver import resolve_question


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return ok


def test_session_and_references() -> int:
    failures: list[str] = []
    print("Session memory + reference resolver smoke test")

    # ── Session operations ──────────────────────────────────────────

    session = SessionMemory(session_id=1)
    session.book_id = 6
    session.record_turn(SessionTurn(
        mode="analyze",
        question="分析孙悟空的人物形象",
        optimized_question="请基于证据分析孙悟空的人物形象",
        answer_preview="孙悟空是西游记中的核心人物",
        target_name="孙悟空",
        target_type="character",
        book_id=6,
        run_id=101,
        evidence_ids=[1, 2, 3],
    ))
    ok = session.turn_count == 1
    check("1.单轮会话记录", ok, f"turns={session.turn_count}")

    ok = session.current_target_name == "孙悟空"
    check("2.当前目标记录", ok, f"target={session.current_target_name}")

    ok = session.last_turn is not None and session.last_turn.run_id == 101
    check("3.上次 Run ID 记录", ok, f"run_id={session.last_turn.run_id if session.last_turn else 'None'}")

    # ── Multi-turn ──────────────────────────────────────────────────

    session.record_turn(SessionTurn(
        mode="trace",
        question="追踪他和唐僧关系变化",
        optimized_question="请按章节时间线追踪",
        answer_preview="关系变化时间线",
        target_name="孙悟空,唐僧",
        target_type="relation",
        book_id=6,
        run_id=102,
        evidence_ids=[4, 5],
    ))
    ok = len(session.turns) == 2
    check("4.多轮会话记录", ok, f"turns={len(session.turns)}")

    ok = session.recent_questions == ["分析孙悟空的人物形象", "追踪他和唐僧关系变化"]
    check("5.最近问题列表", ok, f"questions={session.recent_questions}")

    ok = "孙悟空" in session.recent_targets and "孙悟空,唐僧" in session.recent_targets
    check("6.最近目标列表", ok, f"targets={session.recent_targets}")

    ok = len(session.get_context_summary()) > 10
    check("7.上下文摘要", ok, f"summary={session.get_context_summary()[:60]}")

    # ── Reference resolution ────────────────────────────────────────

    # 7. Pronoun → target name
    resolved, mode_override = resolve_question("他后来怎么样了", session)
    ok = "孙悟空" in resolved
    check("8.代词消解（他→孙悟空）", ok, f"resolved={resolved}")

    # 8. Relation reference
    resolved, mode_override = resolve_question("分析这段关系", session)
    ok = "孙悟空" in resolved and "关系" in resolved
    check("9.关系引用消解", ok, f"resolved={resolved}")

    # 9. Mode change request
    resolved, mode_override = resolve_question("换成时间线追踪", session)
    ok = mode_override == "trace"
    check("10.模式切换（→trace）", ok, f"mode_override={mode_override}")

    resolved, mode_override = resolve_question("详细分析这个人", session)
    ok = mode_override == "analyze"
    check("11.模式切换（→analyze）", ok, f"mode_override={mode_override}")

    # 10. Empty session → no resolution
    empty = SessionMemory(session_id=99)
    resolved, mode_override = resolve_question("他怎么样了", empty)
    ok = resolved == "他怎么样了" and mode_override is None
    check("12.空会话不做消解", ok, f"resolved={resolved}")

    # 11. No session → no resolution
    resolved, mode_override = resolve_question("他怎么样了", None)
    ok = resolved == "他怎么样了" and mode_override is None
    check("13.None 会话安全处理", ok, f"resolved={resolved}")

    # 12. Evidence reference
    resolved, mode_override = resolve_question("这些证据够吗", session)
    ok = "证据" in resolved
    check("14.证据引用", ok, f"resolved={resolved}")

    # 13. Trace reference with session target
    resolved, mode_override = resolve_question("这条线索后来变了", session)
    ok = "孙悟空" in resolved or "线索" in resolved
    check("15.线索引用", ok, f"resolved={resolved}")

    # ── Context summary ─────────────────────────────────────────────

    ok = "西游记" in session.get_context_summary()
    check("16.上下文含书名", ok, f"summary={session.get_context_summary()}")

    ok = session.get_context_summary().startswith("当前书籍")
    check("17.上下文格式正确", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All session memory tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_session_and_references())
