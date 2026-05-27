"""@NB-ENTRYPOINT P1 Quality Gate tests.

Run:
    python -B scripts/test/test_quality_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.qa.quality_gate import GateDecision, evaluate as gate_evaluate


def check(name: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")


def test_gate() -> int:
    failures = []
    print("Quality Gate smoke test")

    # 1. Sufficient high-quality contexts → PASS
    ctx = [{"score": 0.6}, {"score": 0.7}, {"score": 0.5}, {"score": 0.8}]
    r = gate_evaluate(ctx)
    ok = r.decision == GateDecision.PASS
    failures.append("1: expected PASS") if not ok else None
    check("1.足够的高分上下文 → PASS", ok, f"decision={r.decision}")

    # 2. Empty contexts → RETRY_BROADER (first time)
    r = gate_evaluate([])
    ok = r.decision == GateDecision.RETRY_BROADER
    failures.append("2: expected RETRY_BROADER") if not ok else None
    check("2.空上下文第一次 → RETRY_BROADER", ok, f"decision={r.decision}")

    # 3. Empty contexts after retry → FAIL
    r = gate_evaluate([], retry_count=1)
    ok = r.decision == GateDecision.FAIL_INSUFFICIENT
    failures.append("3: expected FAIL") if not ok else None
    check("3.空上下文已重试 → FAIL_INSUFFICIENT", ok, f"decision={r.decision}")

    # 4. Low scores with entity → RETRY_ENTITY
    ctx = [{"score": 0.2}, {"score": 0.3}]
    r = gate_evaluate(ctx, entity_name="孙悟空")
    ok = r.decision == GateDecision.RETRY_ENTITY and r.entity_name == "孙悟空"
    failures.append("4: expected RETRY_ENTITY") if not ok else None
    check("4.低分+实体名 → RETRY_ENTITY", ok, f"decision={r.decision} entity={r.entity_name}")

    # 5. Low scores without entity → RETRY_BROADER (first time)
    ctx = [{"score": 0.2}, {"score": 0.3}]
    r = gate_evaluate(ctx)
    ok = r.decision == GateDecision.RETRY_BROADER
    failures.append("5: expected RETRY_BROADER") if not ok else None
    check("5.低分无实体名 → RETRY_BROADER", ok, f"decision={r.decision}")

    # 6. MIN_CONTEXTS = 3, 2 contexts → RETRY_BROADER
    ctx = [{"score": 0.6}, {"score": 0.7}]
    r = gate_evaluate(ctx)
    ok = r.decision == GateDecision.RETRY_BROADER
    failures.append("6: expected RETRY_BROADER") if not ok else None
    check("6.上下文不足3条 → RETRY_BROADER", ok, f"decision={r.decision}")

    # 7. Enough contexts but all scores low, no entity → RETRY_BROADER
    ctx = [{"score": 0.2}, {"score": 0.25}, {"score": 0.3}, {"score": 0.35}]
    r = gate_evaluate(ctx, retry_count=1)  # Already retried
    ok = r.decision == GateDecision.FAIL_INSUFFICIENT
    failures.append("7: expected FAIL after retry") if not ok else None
    check("7.已重试+低分无实体 → FAIL_INSUFFICIENT", ok, f"decision={r.decision}")

    # 8. needs_broader flag
    r = gate_evaluate([])
    ok = r.needs_broader is True
    failures.append("8: needs_broader not set") if not ok else None
    check("8.空结果标记 needs_broader", ok)

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All Quality Gate tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_gate())
