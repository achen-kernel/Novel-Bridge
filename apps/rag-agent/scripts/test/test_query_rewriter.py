"""@NB-ENTRYPOINT P1 QueryRewriter tests.

Run:
    python -B scripts/test/test_query_rewriter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.qa.query_rewriter import RewriteRequest, _fallback


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")


def test_rewriter_smoke() -> int:
    failures = []
    print("QueryRewriter smoke test")

    # 1. Fallback returns identity
    req = RewriteRequest(question="火焰山的火是怎么来的？", book_id=6)
    result = _fallback(req)
    ok = result.rewritten_query == req.question and result.intent == "factual"
    failures.append("1: fallback changed question") if not ok else None
    check("1.fallback 返回原问题", ok)

    # 2. Entities passthrough in fallback
    req = RewriteRequest(question="分析孙悟空", book_id=6, entities=["孙悟空"])
    result = _fallback(req)
    ok = "孙悟空" in result.explicit_entities
    failures.append("2: entities not passed") if not ok else None
    check("2.fallback 保留 entities", ok)

    # 3. Schema validation
    req = RewriteRequest(question="测试", book_id=6)
    ok = req.book_id == 6 and req.question == "测试"
    failures.append("3: schema broken") if not ok else None
    check("3.RewriteRequest schema", ok)

    # 4. Fallback handles previous_fail
    req = RewriteRequest(question="测试", book_id=6, previous_fail=True)
    ok = req.previous_fail
    failures.append("4: previous_fail not set") if not ok else None
    check("4.RewriteRequest previous_fail", ok)

    # 5. History passthrough
    req = RewriteRequest(question="他后来怎么样了", book_id=6, history=[{"role": "user", "content": "分析孙悟空"}])
    ok = len(req.history) == 1
    failures.append("5: history not passed") if not ok else None
    check("5.RewriteRequest history", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All QueryRewriter tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_rewriter_smoke())
