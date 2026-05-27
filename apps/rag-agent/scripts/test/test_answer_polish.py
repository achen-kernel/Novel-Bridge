"""@NB-ENTRYPOINT Stage 6E answer polish function tests.

Run:
    python -B scripts/test/test_answer_polish.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.reader_agent.answer_polish import (
    audit,
    clean_duplicate_punctuation,
    collapse_whitespace,
    count_broad_claims,
    detect_unsupported_claims,
    has_repetition,
    polish,
    polish_deepseek,
    polish_local_9b,
    strip_citation_tags,
    strip_internal_ids,
    strip_trailing_punctuation,
)


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return ok


def test_polish() -> int:
    failures: list[str] = []

    print("Answer polish smoke test")

    # 1. strip citation tags
    result = strip_citation_tags("这是答案<cite>来源: chapter_1</cite>。")
    ok = result == "这是答案。"
    failures.append("case 1: citation tag not removed") if not ok else None
    check("1.去除 <cite> 标签", ok, f"got={result!r}")

    # 2. strip self-closing cite
    result = strip_citation_tags("答案<cite/>。")
    ok = "答案" in result and "<cite" not in result
    failures.append("case 2: self-closing cite not removed") if not ok else None
    check("2.去除 <cite/>", ok, f"got={result!r}")

    # 3. strip internal chunk ids
    result = strip_internal_ids("参见 [chunk_42] 和 run_99")
    ok = "[chunk_42]" not in result and "run_99" not in result
    failures.append("case 3: chunk id not stripped") if not ok else None
    check("3.去除 [chunk_id]", ok, f"got={result!r}")

    # 4. strip id:
    result = strip_internal_ids("id: 123 和 id：456")
    ok = "id:" not in result and "id：" not in result
    failures.append("case 4: id not stripped") if not ok else None
    check("4.去除 id:", ok, f"got={result!r}")

    # 5. clean duplicate periods
    result = clean_duplicate_punctuation("第一。。第二。。第三。")
    ok = result == "第一。第二。第三。"
    failures.append("case 5: duplicate periods not cleaned") if not ok else None
    check("5.重复句号压缩", ok, f"got={result!r}")

    # 6. clean mixed punctuation
    result = clean_duplicate_punctuation("结束；。然后")
    ok = result == "结束。然后"
    failures.append("case 6: mixed punctuation not cleaned") if not ok else None
    check("6.混合标点修复", ok, f"got={result!r}")

    # 7. collapse whitespace
    result = collapse_whitespace("line1   \n\n\nline2")
    ok = result == "line1\n\nline2"
    failures.append("case 7: whitespace not collapsed") if not ok else None
    check("7.空白压缩", ok, f"got={result!r}")

    # 8. strip trailing punctuation
    result = strip_trailing_punctuation("这是答案。")
    ok = result == "这是答案"
    failures.append("case 8: trailing period not stripped") if not ok else None
    check("8.末尾句号去除", ok, f"got={result!r}")

    # 9. full polish pipeline
    result = polish("""
        孙悟空<cite>来源: 第1回</cite>是主角。。他很强。id: 42
    """)
    ok = "<cite" not in result and "。。" not in result and "id:" not in result
    failures.append("case 9: full polish pipeline failed") if not ok else None
    preview = repr(result)[:80]
    check("9.完整 polish 管线", ok, f"got={preview}")

    # 10. empty text returns empty
    result = polish("")
    ok = result == ""
    failures.append("case 10: empty polish failed") if not ok else None
    check("10.空文本处理", ok, f"got={result!r}")

    # 11. None-safe handling
    result = polish(None)  # type: ignore
    ok = result is None
    failures.append("case 11: None handling failed") if not ok else None
    check("11.None 处理", ok, f"got={result!r}")

    # 12. duplicate question marks
    result = clean_duplicate_punctuation("真的吗？？？")
    ok = result == "真的吗？"
    failures.append("case 12: duplicate ? not cleaned") if not ok else None
    check("12.重复问号压缩", ok, f"got={result!r}")

    # ── Stage 6G: provider-aware polish ─────────────────────────────

    # 13. Local 9B polish is stricter
    result_local = polish_local_9b("孙悟空<cite>来源: 第1回</cite>是主角。。id: 42")
    result_deepseek = polish_deepseek("孙悟空<cite>来源: 第1回</cite>是主角。。id: 42")
    ok = "<cite" not in result_local and "。。" not in result_local and "id:" not in result_local
    failures.append("case 13: local 9B polish failed") if not ok else None
    check("13.local 9B 严格清理", ok, f"got={result_local!r}")

    # 14. DeepSeek preserves ids (lighter polish)
    ok = "<cite" not in result_deepseek and "id:" in result_deepseek
    failures.append("case 14: deepseek polish too aggressive") if not ok else None
    check("14.DeepSeek 轻量清理（保留 id:）", ok, f"got={result_deepseek!r}")

    # 15. Provider-aware polish function
    result_local = polish("孙悟空<cite>来源: 第1回</cite>是主角。。", provider="local")
    result_ds = polish("孙悟空<cite>来源: 第1回</cite>是主角。。", provider="deepseek")
    ok = "。。" not in result_local and "。。" not in result_ds
    failures.append("case 15: provider-aware polish failed") if not ok else None
    local_preview = repr(result_local)[:40]
    ds_preview = repr(result_ds)[:40]
    check("15.provider-aware polish", ok, f"local={local_preview} ds={ds_preview}")

    # ── Stage 6G: unsupported-claim detection ───────────────────────

    # 16. Detect broad claim
    claims = detect_unsupported_claims("这是最重要的作品，毫无疑问是古代百科全书。")
    ok = len(claims) >= 1
    failures.append("case 16: broad claim not detected") if not ok else None
    check("16.检测 broad claim", ok, f"claims={len(claims)}")

    # 17. No false positive for clean text
    claims = detect_unsupported_claims("孙悟空是西游记中的主要角色。他使用金箍棒。")
    ok = len(claims) == 0
    failures.append("case 17: false positive") if not ok else None
    check("17.正常文本无 false positive", ok, f"claims={len(claims)}")

    # 18. Count broad claims
    count = count_broad_claims("最重要的作品，毫无疑问。巅峰之作。")
    ok = count >= 2
    failures.append("case 18: broad claim count wrong") if not ok else None
    check("18.统计 broad claim 数量", ok, f"count={count}")

    # ── Stage 6G: repetition detection ──────────────────────────────

    # 19. Detect repetition
    ok = has_repetition("孙悟空是西游记的主角。孙悟空是西游记的主角。第二段内容。第三段内容。")
    failures.append("case 19: repetition not detected") if not ok else None
    check("19.检测重复内容", ok)

    # 20. No false positive
    ok = not has_repetition("孙悟空是主角。第二段。第三段。")
    failures.append("case 20: false positive repetition") if not ok else None
    check("20.正常内容无重复误报", ok)

    # ── Stage 6G: full audit ────────────────────────────────────────

    # 21. Audit detects issues
    audit_result = audit("这是毫无疑问最重要的作品。巅峰之作。。 \n\n重复内容。重复内容。")
    ok = len(audit_result.warnings) >= 1 and audit_result.has_broad_claims
    failures.append("case 21: audit missed broad claim") if not ok else None
    check("21.audit 检测 broad claim", ok, f"warnings={len(audit_result.warnings)}")

    # 22. Audit on clean text returns clean
    audit_result = audit("孙悟空是西游记中的主要角色。他保护唐僧去西天取经。")
    ok = len(audit_result.warnings) == 0
    failures.append("case 22: audit false positive") if not ok else None
    check("22.正常文本 audit 无警告", ok, f"warnings={len(audit_result.warnings)}")

    # 23. Audit handles None
    audit_result = audit(None)  # type: ignore
    ok = len(audit_result.warnings) == 0
    failures.append("case 23: audit None crash") if not ok else None
    check("23.audit None 安全", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All answer polish tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_polish())
