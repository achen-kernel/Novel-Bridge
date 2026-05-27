"""Compare eval results between Local 9B and DeepSeek providers.

Runs all 37 eval cases through QaRunner with both providers,
then outputs a side-by-side comparison table.

Usage:
    python -B scripts/test/test_provider_comparison.py

Requires: MySQL + llama-server (for local 9B).
DeepSeek run is optional — skipped if DEEPSEEK_API_KEY not set.
"""

import asyncio
import sys
import time
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.clients.mysql_client import MysqlClient
from app.config import settings
from app.qa.qa_runner import QaRunner
from app.stores.eval_store import EvalStore


def _check_deepseek_available() -> bool:
    """Return True if DeepSeek API key is configured."""
    key = settings.deepseek_api_key
    return bool(key and key.strip())


def _short(s: str, max_len: int = 40) -> str:
    """Truncate string for display."""
    if not s:
        return ""
    s = s.replace("\n", " ")
    return s if len(s) <= max_len else s[:max_len] + "..."


async def _run_cases(db, use_deepseek: bool) -> list[dict]:
    """Run all eval cases through QaRunner and return per-case results."""
    conn = db.connect()
    store = EvalStore(conn)
    cases = store.find_cases()
    runner = QaRunner(conn)

    tag = "DeepSeek" if use_deepseek else "Local 9B"
    print(f"\n  Running {len(cases)} cases with {tag} ...")

    results = []
    for i, case in enumerate(cases):
        cid = case["id"]
        book_id = case["book_id"]
        question = case["question"]
        print(f"    [{i+1}/{len(cases)}] book={book_id} q={_short(question)} ... ", end="", flush=True)

        t0 = time.time()
        try:
            result = await runner.answer(
                session_id=0,
                book_id=book_id,
                question=question,
                use_deepseek=use_deepseek,
            )
            elapsed = time.time() - t0
            answer = result.get("answer", "") or ""
            citations = result.get("citations", [])
            is_empty = not answer or "无法回答" in answer or answer.startswith("抱歉")
            passed = bool(answer.strip()) and len(citations) > 0 and not is_empty

            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {elapsed:.1f}s ans={len(answer)}c cit={len(citations)}")
            results.append({
                "case_id": cid,
                "book_id": book_id,
                "question": question,
                "answer": answer,
                "citations": citations,
                "passed": passed,
                "answer_length": len(answer),
                "citation_count": len(citations),
                "error": None,
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"[ERROR] {elapsed:.1f}s {e}")
            results.append({
                "case_id": cid,
                "book_id": book_id,
                "question": question,
                "answer": "",
                "citations": [],
                "passed": False,
                "answer_length": 0,
                "citation_count": 0,
                "error": str(e),
            })

    return results


def _compute_metrics(results: list[dict]) -> dict:
    """Compute aggregate metrics from per-case results."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    total_citations = sum(r["citation_count"] for r in results)
    total_length = sum(r["answer_length"] for r in results)

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0.0,
        "avg_citations": round(total_citations / total, 1) if total else 0.0,
        "avg_answer_length": round(total_length / total, 1) if total else 0.0,
        "total_citations": total_citations,
        "total_answer_length": total_length,
    }


def _delta_str(local_val, deepseek_val, is_pct: bool = False) -> str:
    """Format delta between two values."""
    diff = deepseek_val - local_val
    if abs(diff) < 0.05:
        return "—"
    sign = "+" if diff > 0 else ""
    if is_pct:
        return f"{sign}{diff:.1f}pp"
    return f"{sign}{diff:.1f}"


def _print_table(local_metrics: dict, deepseek_metrics: dict | None):
    """Print markdown comparison table."""
    print()
    print("## Provider Comparison")
    print()
    print("| Metric | Local 9B | DeepSeek | Delta |")
    print("|--------|----------|----------|-------|")

    # Pass rate
    lr = local_metrics["pass_rate"]
    dr = deepseek_metrics["pass_rate"] if deepseek_metrics else lr
    delta = _delta_str(lr, dr, is_pct=True)
    d_label = f"{dr}%" if deepseek_metrics else "N/A (skipped)"
    print(f"| Pass rate | {lr}% | {d_label} | {delta} |")

    # Total passed / total
    lp = local_metrics["passed"]
    dp = deepseek_metrics["passed"] if deepseek_metrics else lp
    d_label = f"{dp}/{deepseek_metrics['total']}" if deepseek_metrics else "N/A"
    print(f"| Passed | {lp}/{local_metrics['total']} | {d_label} | — |")

    # Avg citations
    lc = local_metrics["avg_citations"]
    dc = deepseek_metrics["avg_citations"] if deepseek_metrics else lc
    delta = _delta_str(lc, dc)
    d_label = f"{dc}" if deepseek_metrics else "N/A"
    print(f"| Avg citations | {lc} | {d_label} | {delta} |")

    # Avg answer length
    ll = local_metrics["avg_answer_length"]
    dl = deepseek_metrics["avg_answer_length"] if deepseek_metrics else ll
    delta = _delta_str(ll, dl)
    d_label = f"{dl}" if deepseek_metrics else "N/A"
    print(f"| Avg answer length | {ll} | {d_label} | {delta} |")

    print()


def _print_case_table(local_results: list[dict], deepseek_results: list[dict] | None):
    """Print per-case comparison."""
    print("## Per-Case Results")
    print()
    print(f"| {'Case':<5} | {'Book':<5} | {'Local':<6} | {'DS':<6} | {'Δ':<6} | {'Question':<50} |")
    print(f"|{'':->5}|{'':->5}|{'':->6}|{'':->6}|{'':->6}|{'':->50}|")

    diffs = 0
    for i in range(len(local_results)):
        lr = local_results[i]
        dr = deepseek_results[i] if deepseek_results else lr
        local_tag = "PASS" if lr["passed"] else "FAIL"
        ds_tag = "PASS" if dr["passed"] else "FAIL"
        diff = "SAME" if lr["passed"] == dr["passed"] else "DIFF"
        if diff == "DIFF":
            diffs += 1
        q_short = _short(lr["question"], 48)
        print(f"| {lr['case_id']:<5} | {lr['book_id']:<5} | {local_tag:<6} | {ds_tag:<6} | {diff:<6} | {q_short:<50} |")

    print(f"|{'':->5}|{'':->5}|{'':->6}|{'':->6}|{'':->6}|{'':->50}|")
    total = len(local_results)
    print(f"\nTotal: {total} cases, {diffs} differences")
    print()


async def main():
    print("=" * 70)
    print("Provider Comparison: Local 9B vs DeepSeek")
    print("=" * 70)

    # 1. Connect to MySQL
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"[ERROR] MySQL not available: {e}")
        print("Make sure MySQL is running and .env is configured.")
        return

    # 2. Check DeepSeek availability
    deepseek_available = _check_deepseek_available()
    if deepseek_available:
        print(f"  DeepSeek API: available (model={settings.deepseek_model})")
    else:
        print("  DeepSeek API: NOT configured — skipping DeepSeek runs")
        print("  Set DEEPSEEK_API_KEY in .env to enable comparison.")
    print()

    # 3. Run local 9B
    print("-" * 70)
    print("PHASE 1: Local 9B")
    print("-" * 70)
    t0 = time.time()
    local_results = await _run_cases(db, use_deepseek=False)
    local_elapsed = time.time() - t0
    local_metrics = _compute_metrics(local_results)
    print(f"\n  Local 9B done: {local_metrics['passed']}/{local_metrics['total']} passed "
          f"({local_metrics['pass_rate']}%) in {local_elapsed:.0f}s")

    # 4. Run DeepSeek (if available)
    deepseek_results = None
    deepseek_metrics = None
    deepseek_elapsed = 0
    if deepseek_available:
        print()
        print("-" * 70)
        print("PHASE 2: DeepSeek")
        print("-" * 70)
        t0 = time.time()
        deepseek_results = await _run_cases(db, use_deepseek=True)
        deepseek_elapsed = time.time() - t0
        deepseek_metrics = _compute_metrics(deepseek_results)
        print(f"\n  DeepSeek done: {deepseek_metrics['passed']}/{deepseek_metrics['total']} passed "
              f"({deepseek_metrics['pass_rate']}%) in {deepseek_elapsed:.0f}s")

    # 5. Print comparison
    print()
    print("=" * 70)
    _print_table(local_metrics, deepseek_metrics)
    print(f"Timing: Local 9B={local_elapsed:.0f}s", end="")
    if deepseek_elapsed:
        print(f", DeepSeek={deepseek_elapsed:.0f}s", end="")
    print()

    # 6. Per-case detail
    _print_case_table(local_results, deepseek_results)

    # 7. Summary row
    print("## Quick Summary")
    print()
    lm = local_metrics
    if deepseek_metrics:
        dm = deepseek_metrics
        print(f"| Provider | Pass Rate | Avg Citations | Avg Answer Len | Time |")
        print(f"|----------|-----------|---------------|----------------|------|")
        print(f"| Local 9B | {lm['pass_rate']}% | {lm['avg_citations']} | {lm['avg_answer_length']} | {local_elapsed:.0f}s |")
        print(f"| DeepSeek | {dm['pass_rate']}% | {dm['avg_citations']} | {dm['avg_answer_length']} | {deepseek_elapsed:.0f}s |")
    else:
        print(f"| Provider | Pass Rate | Avg Citations | Avg Answer Len | Time |")
        print(f"|----------|-----------|---------------|----------------|------|")
        print(f"| Local 9B | {lm['pass_rate']}% | {lm['avg_citations']} | {lm['avg_answer_length']} | {local_elapsed:.0f}s |")
        print(f"| DeepSeek | skipped (API key not configured) |")
    print()

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
