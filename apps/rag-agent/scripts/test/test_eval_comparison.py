"""Compare 37 eval cases: old /api/qa/ask (QaRunner) vs new /api/reader-agent/run.

Requires: SSH tunnel + llama-server + MySQL.

Run from apps/rag-agent:
    python scripts/test/test_eval_comparison.py
"""

import asyncio
import json
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.clients.mysql_client import MysqlClient
from app.qa.qa_runner import QaRunner
from app.reader_agent.agent import ReaderAgent
from app.reader_agent.schemas import ReaderRequest, ReaderOptions
from app.stores.eval_store import EvalStore


async def main():
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"[ERROR] MySQL not available: {e}")
        return

    store = EvalStore(conn)

    # 1. Load all active eval cases
    cases = store.find_cases()
    print(f"Found {len(cases)} eval cases\n")

    # 2. Run through OLD path (QaRunner)
    print("=" * 70)
    print("OLD PATH — QaRunner.answer()")
    print("=" * 70)
    old_results = []
    qa_runner = QaRunner(conn)

    for i, case in enumerate(cases):
        cid = case["id"]
        book_id = case["book_id"]
        question = case["question"]
        print(f"  [{i+1}/{len(cases)}] book={book_id} q={question[:40]}... ", end="")

        try:
            result = await qa_runner.answer(
                session_id=0,
                book_id=book_id,
                question=question,
                use_deepseek=False,
            )
            answer = result.get("answer", "") or ""
            citations = result.get("citations", [])
            passed = bool(answer.strip()) and len(citations) > 0
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] answer={len(answer)}c cit={len(citations)}")
            old_results.append({
                "case_id": cid, "question": question, "book_id": book_id,
                "answer": answer[:200], "citations": len(citations),
                "passed": passed,
            })
        except Exception as e:
            print(f"[ERROR] {e}")
            old_results.append({
                "case_id": cid, "question": question, "book_id": book_id,
                "answer": "", "citations": 0, "passed": False,
            })

    old_passed = sum(1 for r in old_results if r["passed"])
    old_total = len(old_results)
    print(f"\nOLD PATH: {old_passed}/{old_total} passed ({old_passed/old_total*100:.1f}%)\n")

    # 3. Run through NEW path (ReaderAgent)
    print("=" * 70)
    print("NEW PATH — ReaderAgent.answer")
    print("=" * 70)
    new_results = []
    reader = ReaderAgent(conn)

    for i, case in enumerate(cases):
        cid = case["id"]
        book_id = case["book_id"]
        question = case["question"]
        print(f"  [{i+1}/{len(cases)}] book={book_id} q={question[:40]}... ", end="")

        try:
            req = ReaderRequest(
                book_id=book_id,
                question=question,
                options=ReaderOptions(provider="local", require_citations=True, top_k=12),
            )
            response = await reader.run(req)
            answer = response.answer or ""
            citations = response.citations or []
            passed = response.status.value in ("RESPONDED",) and bool(answer.strip()) and len(citations) > 0
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] answer={len(answer)}c cit={len(citations)}")
            new_results.append({
                "case_id": cid, "question": question, "book_id": book_id,
                "answer": answer[:200], "citations": len(citations),
                "passed": passed,
            })
        except Exception as e:
            print(f"[ERROR] {e}")
            new_results.append({
                "case_id": cid, "question": question, "book_id": book_id,
                "answer": "", "citations": 0, "passed": False,
            })

    new_passed = sum(1 for r in new_results if r["passed"])
    new_total = len(new_results)
    print(f"\nNEW PATH: {new_passed}/{new_total} passed ({new_passed/new_total*100:.1f}%)\n")

    # 4. Comparison
    print("=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Case':<5} {'Book':<5} {'Old':<6} {'New':<6} {'Diff':<6} Question")
    print("-" * 70)
    diffs = 0
    for i in range(len(cases)):
        o = old_results[i]
        n = new_results[i]
        old_tag = "PASS" if o["passed"] else "FAIL"
        new_tag = "PASS" if n["passed"] else "FAIL"
        diff = "SAME" if o["passed"] == n["passed"] else "DIFF"
        if diff == "DIFF":
            diffs += 1
        q_short = o["question"][:40]
        print(f"{o['case_id']:<5} {o['book_id']:<5} {old_tag:<6} {new_tag:<6} {diff:<6} {q_short}")

    print("-" * 70)
    print(f"Total: {old_total} cases, {diffs} differences")
    print(f"Old pass rate: {old_passed}/{old_total} ({old_passed/old_total*100:.1f}%)")
    print(f"New pass rate: {new_passed}/{new_total} ({new_passed/new_total*100:.1f}%)")
    print()

    # 5. Also store results in eval DB tables for traceability
    old_run_id = store.create_run("QA_EVAL_OLD")
    for r in old_results:
        store.insert_result(old_run_id, r["case_id"], r["question"],
                            actual_answer=r["answer"],
                            citations=[], scores={"passed": 1 if r["passed"] else 0},
                            error_type="" if r["passed"] else "failed")
    store.update_run(old_run_id, "SUCCESS", {"total": old_total, "passed": old_passed})

    new_run_id = store.create_run("QA_EVAL_NEW")
    for r in new_results:
        store.insert_result(new_run_id, r["case_id"], r["question"],
                            actual_answer=r["answer"],
                            citations=[], scores={"passed": 1 if r["passed"] else 0},
                            error_type="" if r["passed"] else "failed")
    store.update_run(new_run_id, "SUCCESS", {"total": new_total, "passed": new_passed})

    print(f"Old path run ID: {old_run_id}, New path run ID: {new_run_id}")
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
