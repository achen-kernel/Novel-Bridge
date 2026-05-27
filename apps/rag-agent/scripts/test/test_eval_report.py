"""Enhanced eval report — Stage 5D: Alpha + observability + patch metrics.

Runs 37 eval cases through OLD (QaRunner) and NEW (ReaderAgent) paths,
then generates a JSON/Markdown report with:
- Baseline pass rate comparison (allow_patch=false)
- Observability metrics: model_call_visible, tool_call_visible, trace_complete
- Citation stats, refusal status
- Separate patch candidate eval section (allow_patch=true on failing cases)

Usage:
    python scripts/test/test_eval_report.py                    # full run
    python scripts/test/test_eval_report.py --quick            # 5 cases, new path only
    python scripts/test/test_eval_report.py --smoke            # 3 cases, new path only
    python scripts/test/test_eval_report.py --limit 10         # first N cases
    python scripts/test/test_eval_report.py --cache            # from DB cache (no LLM)

Output: stdout + training/data/eval_report_latest.json
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.clients.mysql_client import MysqlClient
from app.qa.qa_runner import QaRunner
from app.reader_agent.agent import ReaderAgent
from app.reader_agent.schemas import ReaderRequest, ReaderOptions
from app.stores.eval_store import EvalStore

REPORT_DIR = os.environ.get(
    "TRAINING_DATA_DIR",
    os.path.join(str(RAG_ROOT), "training", "data"),
)
REPORT_SCHEMA_VERSION = "eval-report-v2-stage5"
OBSERVABILITY_SCHEMA_VERSION = "observability-v1"

# ── Judgment helpers ──────────────────────────────────────────


def _judge_citation_correctness(citations: list) -> str:
    if not citations:
        return "fail"
    valid = 0
    for c in citations:
        sid = c.get("source_id", 0) if isinstance(c, dict) else 0
        src = c.get("source_type", "") if isinstance(c, dict) else ""
        if sid > 0 or src in ("entity", "relation", "event", "citation"):
            valid += 1
    if valid == len(citations):
        return "ok"
    return "pending" if valid > 0 else "fail"


def _judge_evidence_coverage(citations: list) -> str:
    if not citations:
        return "fail"
    types = set()
    for c in citations:
        st = c.get("source_type", "") if isinstance(c, dict) else ""
        if st:
            types.add(st)
    return "ok" if len(types) >= 2 else "pending"


def _judge_refusal_status(answer: str, status: str) -> str:
    """Refusal correctness: if status is INSUFFICIENT_EVIDENCE it's correct refusal."""
    if status == "INSUFFICIENT_EVIDENCE":
        return "ok"
    if not answer or "无法回答" in answer or answer.startswith("抱歉"):
        return "manual_required"
    return "ok"


def _judge_trace_complete(has_run: bool, citations: list,
                          model_visible: bool) -> str:
    if has_run and citations and model_visible:
        return "ok"
    if has_run:
        return "pending"
    return "fail"


def _judge_patch_quality(patch_info: dict | None) -> str:
    """Patch quality: if generated with valid evidence, pending review."""
    if patch_info is None:
        return "not_applicable"
    if patch_info.get("ok") and patch_info.get("status") in ("PENDING_REVIEW", "PROPOSED"):
        return "pending"
    return "manual_required"


def _diagnose_failed_case(result: dict) -> list[str]:
    """Rule-based failed-case diagnosis for fast triage."""
    reasons: list[str] = []
    if result.get("error"):
        reasons.append(f"error: {result['error']}")
    if not result.get("answer_length", 0):
        reasons.append("empty_answer")
    if result.get("citation_count", 0) == 0:
        reasons.append("no_citations")
    if result.get("model_call_visible") == "fail":
        reasons.append("model_call_missing")
    if result.get("tool_call_visible") == "fail":
        reasons.append("tool_call_missing")
    if result.get("retrieval_visible") == "fail":
        reasons.append("retrieval_trace_missing")
    if result.get("status") == "INSUFFICIENT_EVIDENCE":
        reasons.append("insufficient_evidence")
    return reasons or ["manual_review_required"]


def _collect_observability(conn, run_id: int | None) -> dict:
    """Quick store queries for observability metrics (no LLM)."""
    if run_id is None:
        return {"model_call_visible": "fail", "tool_call_visible": "fail"}

    from app.agent_runtime.model_call_store import MysqlModelCallStore
    from app.agent_runtime.tool_call_store import MysqlToolCallStore
    from app.agent_runtime.trace_store import MysqlRetrievalTraceStore
    mcs = MysqlModelCallStore(conn)
    tcs = MysqlToolCallStore(conn, auto_create=True)
    rts = MysqlRetrievalTraceStore(conn, auto_create=False)

    mc = mcs.get_model_calls_for_run(run_id)
    tc = tcs.get_tool_calls_for_run(run_id)
    rt = rts.get_traces_for_run(run_id)
    return {
        "model_call_visible": "ok" if mc else "fail",
        "tool_call_visible": "ok" if tc else "fail",
        "retrieval_visible": "ok" if rt else "fail",
        "model_call_count": len(mc),
        "tool_call_count": len(tc),
        "retrieval_count": len(rt),
    }


# ── Case runners ──────────────────────────────────────────────


async def _run_old(case: dict, db) -> dict:
    conn = db.connect()
    runner = QaRunner(conn)
    result = await runner.answer(
        session_id=0, book_id=case["book_id"],
        question=case["question"], use_deepseek=False,
    )
    answer = result.get("answer", "") or ""
    citations = result.get("citations", [])
    passed = bool(answer.strip()) and len(citations) > 0
    return {
        "case_id": case["id"], "book_id": case["book_id"],
        "question": case["question"],
        "answer": answer[:500], "citations": citations,
        "passed": passed, "answer_length": len(answer),
        "citation_count": len(citations),
    }


async def _run_new(case: dict, db, *, allow_patch: bool = False) -> dict:
    conn = db.connect()
    reader = ReaderAgent(conn)
    req = ReaderRequest(
        book_id=case["book_id"], question=case["question"],
        options=ReaderOptions(
            provider="local", require_citations=True,
            top_k=12, allow_patch=allow_patch,
        ),
    )
    resp = await reader.run(req)
    answer = resp.answer or ""
    citations_raw = resp.citations or []
    citations = [
        {"source_type": c.source_type, "source_id": c.source_id,
         "excerpt": c.excerpt[:200] if c.excerpt else ""}
        for c in citations_raw
    ]
    passed = resp.status.value == "RESPONDED" and bool(answer.strip()) and len(citations) > 0

    # Collect observability from stores
    obs = _collect_observability(conn, resp.run_id)

    result = {
        "case_id": case["id"], "book_id": case["book_id"],
        "question": case["question"],
        "answer": answer[:500], "citations": citations,
        "passed": passed, "answer_length": len(answer),
        "citation_count": len(citations),
        "run_id": resp.run_id, "status": resp.status.value,
        "patches": [dict(p) for p in (resp.patches or [])],
        **obs,
    }
    return result


async def run_main_eval(use_new_path: bool, db, *, limit: int | None = None) -> list[dict]:
    """Run all eval cases through either OLD or NEW path."""
    conn = db.connect()
    store = EvalStore(conn)
    cases = store.find_cases()
    if limit is not None:
        cases = cases[:limit]
    results: list[dict] = []

    for case in cases:
        try:
            result = await (_run_new(case, db) if use_new_path else _run_old(case, db))
            results.append(result)
        except Exception as e:
            results.append({
                "case_id": case["id"], "book_id": case["book_id"],
                "question": case["question"],
                "answer": "", "citations": [], "passed": False,
                "error": str(e),
            })
    return results


async def run_patch_eval(db) -> dict:
    """Run allow_patch=true on selected failing / edge cases.

    Does not affect the 37-case baseline pass rate.
    """
    conn = db.connect()
    store = EvalStore(conn)
    all_cases = store.find_cases()

    # Select cases likely to fail: book 9 (山海经) keyword/entity questions
    # and book 10 character analysis questions
    target_ids = {5, 7, 8, 16, 20}  # past failing case_ids
    target_cases = [c for c in all_cases if c["id"] in target_ids]
    if not target_cases:
        # Fallback: pick cases 5, 10, 15, 20, 25 modulo
        target_cases = all_cases[::7][:5]

    patch_results = []
    for case in target_cases:
        try:
            result = await _run_new(case, db, allow_patch=True)
            has_patch = bool(result.get("patches"))
            pt = ""
            ps = ""
            if has_patch:
                p = result["patches"][0]
                pt = p.get("patch_type", "")
                ps = p.get("status", "")
            patch_results.append({
                "case_id": case["id"],
                "book_id": case["book_id"],
                "question": case["question"][:60],
                "passed": result["passed"],
                "status": result.get("status", ""),
                "has_patch": has_patch,
                "patch_type": pt,
                "patch_status": ps,
                "model_call_visible": result.get("model_call_visible", "?"),
                "tool_call_visible": result.get("tool_call_visible", "?"),
            })
        except Exception as e:
            patch_results.append({
                "case_id": case["id"], "error": str(e),
                "has_patch": False, "patch_type": "",
            })

    patches_generated = sum(1 for r in patch_results if r.get("has_patch"))
    return {
        "description": "allow_patch=true on select failing/edge cases",
        "cases_tested": len(patch_results),
        "patches_generated": patches_generated,
        "cases": patch_results,
    }


# ── Report builder ────────────────────────────────────────────


def build_report(old_results: list[dict], new_results: list[dict],
                 patch_section: dict | None = None) -> dict:
    old_passed = sum(1 for r in old_results if r.get("passed"))
    new_passed = sum(1 for r in new_results if r.get("passed"))
    total = max(len(old_results), len(new_results))

    case_details = []
    obs_model_ok = 0
    obs_tool_ok = 0
    obs_retrieval_ok = 0
    refusal_ok = 0
    refusal_manual = 0
    trace_ok = 0

    for i in range(total):
        o = old_results[i] if i < len(old_results) else {}
        n = new_results[i] if i < len(new_results) else {}
        oc = o.get("citations", []) or []
        nc = n.get("citations", []) or []

        model_vis = n.get("model_call_visible", "?")
        tool_vis = n.get("tool_call_visible", "?")
        ret_vis = n.get("retrieval_visible", "?")
        refusal = _judge_refusal_status(n.get("answer", ""), n.get("status", ""))
        trace_c = _judge_trace_complete(
            bool(n.get("run_id")), nc, model_vis == "ok")

        if model_vis == "ok":
            obs_model_ok += 1
        if tool_vis == "ok":
            obs_tool_ok += 1
        if ret_vis == "ok":
            obs_retrieval_ok += 1
        if refusal == "ok":
            refusal_ok += 1
        elif refusal == "manual_required":
            refusal_manual += 1
        if trace_c == "ok":
            trace_ok += 1

        case_details.append({
            "case_id": o.get("case_id") or n.get("case_id"),
            "book_id": o.get("book_id") or n.get("book_id"),
            "question": (o.get("question") or n.get("question", ""))[:60],
            "old_passed": o.get("passed", False),
            "new_passed": n.get("passed", False),
            "new_metrics": {
                "answer_correctness": "ok" if n.get("passed") else "fail",
                "citation_present": len(nc) > 0,
                "citation_count": len(nc),
                "citation_issue_count": sum(
                    1 for c in nc
                    if isinstance(c, dict) and c.get("source_id", 0) <= 0
                    and c.get("source_type", "") not in ("entity", "relation", "event", "citation")
                ),
                "citation_correctness": _judge_citation_correctness(nc),
                "model_call_visible": model_vis,
                "tool_call_visible": tool_vis,
                "retrieval_visible": ret_vis,
                "refusal_status": refusal,
                "trace_complete": trace_c,
                "patch_generated": bool(n.get("patches")),
                "patch_type": (n.get("patches") or [{}])[0].get("patch_type", "")
                if n.get("patches") else "",
                "patch_status": (n.get("patches") or [{}])[0].get("status", "")
                if n.get("patches") else "",
                "patch_quality": _judge_patch_quality(
                    (n.get("patches") or [None])[0]
                ),
            },
            "diagnosis": _diagnose_failed_case(n) if not n.get("passed") else [],
        })

    total_citations = sum(
        d["new_metrics"]["citation_count"] for d in case_details
    )
    cases_with_cit = sum(
        1 for d in case_details if d["new_metrics"]["citation_present"]
    )

    report: dict = {
        "report_meta": {
            "generated_at": datetime.utcnow().isoformat(),
            "schema_version": REPORT_SCHEMA_VERSION,
            "observability_schema_version": OBSERVABILITY_SCHEMA_VERSION,
            "total_cases": total,
        },
        "summary": {
            "old_path": {
                "passed": old_passed, "total": total,
                "rate": f"{old_passed/total*100:.1f}%" if total else "0%",
            },
            "new_path": {
                "passed": new_passed, "total": total,
                "rate": f"{new_passed/total*100:.1f}%" if total else "0%",
            },
            "delta": new_passed - old_passed,
        },
        "observability": {
            "model_call_visible": f"{obs_model_ok}/{total}",
            "tool_call_visible": f"{obs_tool_ok}/{total}",
            "retrieval_visible": f"{obs_retrieval_ok}/{total}",
            "trace_complete": f"{trace_ok}/{total}",
            "refusal_ok": refusal_ok,
            "refusal_manual_required": refusal_manual,
        },
        "citation_stats": {
            "total_citations": total_citations,
            "cases_with_citations": cases_with_cit,
            "cases_without_citations": total - cases_with_cit,
            "avg_citations_per_case": round(total_citations / total, 2) if total else 0,
        },
        "failed_cases_new_path": [
            d for d in case_details if not d["new_passed"]
        ],
        "failed_case_diagnosis": [
            {
                "case_id": d["case_id"],
                "book_id": d["book_id"],
                "question": d["question"],
                "diagnosis": d["diagnosis"],
                "metrics": d["new_metrics"],
            }
            for d in case_details if not d["new_passed"]
        ],
        "cache_notes": [],
        "case_details": case_details,
    }

    if patch_section:
        report["patch_candidate_eval"] = patch_section

    return report


# ── Markdown printer ──────────────────────────────────────────


def print_report_markdown(report: dict):
    s = report["summary"]
    obs = report["observability"]
    cs = report["citation_stats"]

    print("# Eval Report — Stage 5D Alpha + Observability")
    print(f"\nGenerated: {report['report_meta']['generated_at']}")
    print(f"Total cases: {report['report_meta']['total_cases']}")
    print()
    print("## Summary")
    print("| Path | Passed | Rate |")
    print("|------|--------|------|")
    print(f"| Old (QaRunner) | {s['old_path']['passed']}/{s['old_path']['total']} | {s['old_path']['rate']} |")
    print(f"| New (ReaderAgent) | {s['new_path']['passed']}/{s['new_path']['total']} | {s['new_path']['rate']} |")
    print(f"| Delta | | {s['delta']:+d} |")
    print()
    print("## Observability (ReaderAgent path)")
    print(f"| Metric | Coverage |")
    print(f"|--------|----------|")
    print(f"| model_call_visible | {obs['model_call_visible']} |")
    print(f"| tool_call_visible | {obs['tool_call_visible']} |")
    print(f"| retrieval_visible | {obs['retrieval_visible']} |")
    print(f"| trace_complete | {obs['trace_complete']} |")
    print(f"| refusal_ok | {obs['refusal_ok']} |")
    print(f"| refusal_manual_required | {obs['refusal_manual_required']} |")
    print()
    print("## Citation Stats (New Path)")
    print(f"- Total citations: {cs['total_citations']}")
    print(f"- Cases with citations: {cs['cases_with_citations']}/{report['report_meta']['total_cases']}")
    print(f"- Avg citations/case: {cs['avg_citations_per_case']}")
    print()

    if "patch_candidate_eval" in report:
        pe = report["patch_candidate_eval"]
        print("## Patch Candidate Eval (allow_patch=true)")
        print(f"Description: {pe['description']}")
        print(f"Cases tested: {pe['cases_tested']}")
        print(f"Patches generated: {pe['patches_generated']}")
        print()
        print("| Case | Book | Status | Patch | Type | Status | ModelVis | ToolVis |")
        print("|------|------|--------|-------|------|--------|----------|---------|")
        for r in pe["cases"]:
            hp = "YES" if r.get("has_patch") else "no"
            pt = r.get("patch_type", "") or ""
            ps = r.get("patch_status", "") or ""
            mv = r.get("model_call_visible", "") or ""
            tv = r.get("tool_call_visible", "") or ""
            st = r.get("status", "") or ""
            print(f"| {r['case_id']} | {r['book_id']} | {st} | {hp} | {pt} | {ps} | {mv} | {tv} |")
        print()

    print("## Failed Cases (New Path)")
    for d in report["failed_cases_new_path"]:
        q = d["question"]
        diagnosis = ", ".join(d.get("diagnosis", [])) or "manual_review_required"
        print(f"- Case {d['case_id']} (book {d['book_id']}): {q} [{diagnosis}]")
    print()
    print("## Notes")
    print("- Observability requires Stage 5A model/tool call integration")
    print("- Patch eval is separate from 37-case baseline")
    print("- refusal=manual_required means human check needed")


# ── Main ──────────────────────────────────────────────────────


async def main():
    mode = "run"
    limit: int | None = None
    if "--cache" in sys.argv:
        mode = "cache"
    elif "--smoke" in sys.argv:
        mode = "smoke"
    elif "--quick" in sys.argv:
        mode = "quick"
    elif "--baseline" in sys.argv:
        mode = "baseline"  # new path + patch eval only (skip old)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        try:
            limit = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("[ERROR] --limit requires an integer", file=sys.stderr)
            return

    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        return

    print(f"[INFO] Running eval... (mode={mode})", file=sys.stderr)

    if mode == "cache":
        store = EvalStore(conn)
        runs = store.find_runs()
        old_run = next((r for r in runs if r["run_type"] == "QA_EVAL_OLD"), None)
        new_run = next((r for r in runs if r["run_type"] == "QA_EVAL_NEW"), None)
        old_results: list[dict] = []
        new_results: list[dict] = []
        for run_id, target in [(old_run["id"] if old_run else None, old_results),
                                (new_run["id"] if new_run else None, new_results)]:
            if run_id:
                for res in store.find_results(run_id):
                    target.append({
                        "case_id": res["case_id"],
                        "book_id": res.get("book_id", 0),
                        "question": res.get("question", ""),
                        "answer": res.get("actual_answer", ""),
                        "citations": json.loads(res.get("citations_json", "[]"))
                        if isinstance(res.get("citations_json"), str)
                        else (res.get("citations_json") or []),
                        "passed": res.get("status") == "done" and bool(res.get("actual_answer")),
                        "model_call_visible": "unknown_cache_v1",
                        "tool_call_visible": "unknown_cache_v1",
                        "retrieval_visible": "unknown_cache_v1",
                        "cache_observability_missing": True,
                    })
        print(f"[INFO] Loaded {len(old_results)} old + {len(new_results)} new from cache",
              file=sys.stderr)
        patch_section = None
    elif mode in ("quick", "smoke"):
        default_limit = 3 if mode == "smoke" else 5
        case_limit = limit or default_limit
        print(f"[INFO] {mode} mode: {case_limit} ReaderAgent cases only", file=sys.stderr)
        store = EvalStore(conn)
        cases = store.find_cases()[:case_limit]
        new_results = []
        for case in cases:
            r = await _run_new(case, db)
            new_results.append(r)
        old_results = []
        print(f"[INFO] Quick done: {sum(1 for r in new_results if r.get('passed'))}/{len(new_results)}",
              file=sys.stderr)
        patch_section = None
    elif mode == "baseline":
        print("[INFO] Baseline mode: NEW path + patch eval only", file=sys.stderr)
        old_results = []  # will be shown as 0/0
        print("[INFO] Running NEW path (allow_patch=false)...", file=sys.stderr)
        new_results = await run_main_eval(use_new_path=True, db=db, limit=limit)
        print(f"[INFO] NEW: {sum(1 for r in new_results if r.get('passed'))}/{len(new_results)}",
              file=sys.stderr)
        print("[INFO] Running patch candidate eval...", file=sys.stderr)
        patch_section = await run_patch_eval(db)
        print(f"[INFO] Patch eval: {patch_section['patches_generated']}/{patch_section['cases_tested']} patches",
              file=sys.stderr)
    else:
        print("[INFO] Running OLD path...", file=sys.stderr)
        old_results = await run_main_eval(use_new_path=False, db=db, limit=limit)
        print(f"[INFO] OLD: {sum(1 for r in old_results if r.get('passed'))}/{len(old_results)}",
              file=sys.stderr)

        print("[INFO] Running NEW path (allow_patch=false)...", file=sys.stderr)
        new_results = await run_main_eval(use_new_path=True, db=db, limit=limit)
        print(f"[INFO] NEW: {sum(1 for r in new_results if r.get('passed'))}/{len(new_results)}",
              file=sys.stderr)

        print("[INFO] Running patch candidate eval...", file=sys.stderr)
        patch_section = await run_patch_eval(db)
        print(f"[INFO] Patch eval: {patch_section['patches_generated']}/{patch_section['cases_tested']} patches",
              file=sys.stderr)

    report = build_report(old_results, new_results, patch_section)
    if mode == "cache":
        report["cache_notes"].append(
            "Cache mode uses legacy eval_result rows; observability fields are unknown_cache_v1 unless the cache was generated by Stage 5D+."
        )
    if limit is not None:
        report["report_meta"]["case_limit"] = limit
    report["report_meta"]["mode"] = mode

    report_path = os.path.join(REPORT_DIR, "eval_report_latest.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Report saved to {report_path}", file=sys.stderr)

    print_report_markdown(report)
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
