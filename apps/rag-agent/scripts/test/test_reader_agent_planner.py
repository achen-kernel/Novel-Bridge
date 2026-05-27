"""@NB-ENTRYPOINT Stage 6E ReaderAgent planner tests.

Run:
    python -B scripts/test/test_reader_agent_planner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.reader_agent.planner import plan


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return ok


def test_plan() -> int:
    failures: list[str] = []

    print("ReaderAgent planner smoke test")

    # 1. answer mode — direct factual question
    r = plan(book_id=6, question="火焰山的火是怎么来的？")
    ok = r.mode == "answer"
    failures.append("case 1: expected answer mode") if not ok else None
    check("1.火焰山的火 -> answer", ok, f"got {r.mode}")

    # 2. analyze character
    r = plan(book_id=6, question="分析孙悟空的人物形象")
    ok = r.mode == "analyze" and r.analysis_type == "character"
    failures.append("case 2: expected analyze/character") if not ok else None
    check("2.分析孙悟空 -> analyze character", ok, f"mode={r.mode} analysis_type={r.analysis_type}")

    # 3. analyze relation
    r = plan(book_id=6, question="分析孙悟空和唐僧的关系")
    ok = r.mode == "analyze" and r.target_type == "relation"
    failures.append("case 3: expected analyze relation") if not ok else None
    check("3.分析关系 -> analyze relation", ok, f"mode={r.mode} target_type={r.target_type}")

    # 4. trace relation
    r = plan(book_id=6, question="追踪孙悟空和唐僧关系变化")
    ok = r.mode == "trace" and r.target_type == "relation"
    failures.append("case 4: expected trace relation") if not ok else None
    check("4.追踪关系变化 -> trace relation", ok, f"mode={r.mode} target_type={r.target_type}")

    # 5. trace item
    r = plan(book_id=6, question="追踪芭蕉扇相关线索")
    ok = r.mode == "trace" and r.target_name == "芭蕉扇"
    failures.append("case 5: expected trace item") if not ok else None
    check("5.追踪芭蕉扇 -> trace item", ok, f"mode={r.mode} target_name={r.target_name}")

    # 6. answer — character rise question (not necessarily trace if no "追踪" keyword)
    r = plan(book_id=10, question="宋江为什么能成为梁山核心人物")
    ok = r.mode == "answer"
    failures.append("case 6: expected answer (no trace keyword)") if not ok else None
    check("6.宋江为什么 -> answer", ok, f"mode={r.mode}")

    # 7. trace character — explicit trace keyword
    # Question contains both "宋江" and "梁山" — target_name captures both
    r = plan(book_id=10, question="追踪宋江成为梁山核心的关键线索")
    ok = r.mode == "trace" and "宋江" in r.target_name
    failures.append("case 7: expected trace character") if not ok else None
    check("7.追踪宋江线索 -> trace character", ok, f"mode={r.mode} target_name={r.target_name}")

    # 8. analyze character — 林冲人物转变
    r = plan(book_id=10, question="分析林冲的人物转变")
    ok = r.mode == "analyze" and r.analysis_type == "character"
    failures.append("case 8: expected analyze character") if not ok else None
    check("8.分析林冲转变 -> analyze character", ok, f"mode={r.mode} analysis_type={r.analysis_type}")

    # 9. answer — 山海经组织结构
    r = plan(book_id=9, question="《山海经》如何组织山川地理与神话")
    ok = r.mode == "answer"
    failures.append("case 9: expected answer") if not ok else None
    check("9.山海经组织结构 -> answer", ok, f"mode={r.mode}")

    # 10. trace setting — 昆仑变化
    # The question contains "变化" which triggers trace
    r = plan(book_id=9, question="昆仑在山海经中如何变化")
    ok = r.mode == "trace" and r.target_type == "setting"
    failures.append("case 10: expected trace setting") if not ok else None
    check("10.昆仑变化 -> trace setting", ok, f"mode={r.mode} target_type={r.target_type}")

    # 11. vague question — fallback answer with warnings
    r = plan(book_id=6, question="这个人物怎么样")
    ok = r.mode == "answer" and len(r.warnings) >= 1
    failures.append("case 11: expected fallback answer with warnings") if not ok else None
    check("11.模糊问题 -> answer + warnings", ok, f"mode={r.mode} warnings={len(r.warnings)}")

    # 12. enrich
    r = plan(book_id=6, question="生成一个 KnowledgePatch 修正")
    ok = r.mode == "enrich"
    failures.append("case 12: expected enrich") if not ok else None
    check("12.KnowledgePatch -> enrich", ok, f"mode={r.mode}")

    # 13. 关系变化 traced with explicit trace keyword
    r = plan(book_id=6, question="追踪孙悟空和唐僧的关系演变")
    ok = r.mode == "trace" and r.target_type == "relation"
    failures.append("case 13: expected trace relation") if not ok else None
    check("13.关系演变 -> trace relation", ok, f"mode={r.mode} target_type={r.target_type}")

    # 14. verify confidence is always set
    r = plan(book_id=10, question="林冲")
    ok = r.confidence > 0 and r.confidence <= 1.0
    failures.append("case 14: confidence out of range") if not ok else None
    check("14.单关键词 置信度有效", ok, f"confidence={r.confidence}")

    # 15. explicit mode overrides auto
    r = plan(book_id=6, question="孙悟空和唐僧", preferred_mode="trace")
    ok = r.mode == "trace"
    failures.append("case 15: explicit mode not respected") if not ok else None
    check("15.显式指定 trace -> trace", ok, f"mode={r.mode}")

    # 16. request_patch is present
    r = plan(book_id=6, question="火焰山的火是怎么来的？")
    ok = r.request_patch is not None and r.request_patch.mode == "answer"
    failures.append("case 16: missing request_patch") if not ok else None
    check("16.request_patch 存在", ok, f"patch_mode={r.request_patch.mode if r.request_patch else 'NONE'}")

    # 17. target is recognized for known entity
    r = plan(book_id=6, question="分析猪八戒的人物形象")
    ok = r.target_name == "猪八戒"
    failures.append("case 17: target not detected") if not ok else None
    check("17.猪八戒被识别", ok, f"target_name={r.target_name}")

    # 18. empty question returns answer mode without crashing
    r = plan(book_id=6, question="")
    ok = r.mode == "answer"
    failures.append("case 18: empty question") if not ok else None
    check("18.空问题 -> answer", ok, f"mode={r.mode}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All planner tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_plan())
