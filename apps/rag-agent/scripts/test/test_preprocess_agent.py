"""Smoke test for PreprocessAgent — import, state walk, and action wiring.

Real execution requires MySQL tunnel + existing book data.

Run from apps/rag-agent:
    python scripts/test/test_preprocess_agent.py
"""

import asyncio
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.clients.mysql_client import MysqlClient
from app.preprocess_agent import PreprocessAgent, PreprocessState
from app.preprocess_agent.schemas import PreprocessPlanRequest, PreprocessRequest
from app.preprocess_agent.states import PreprocessState as PS


def test_import_and_schemas():
    """Verify the agent and schemas import correctly."""
    req = PreprocessRequest(book_id=6)
    assert req.start_state == PreprocessState.NEW
    assert req.target_state == PreprocessState.DONE
    print("  [PASS] import and schema validation OK")


def test_noop_same_state():
    """start_state == target_state should return immediately."""
    req = PreprocessRequest(
        book_id=6,
        start_state=PreprocessState.CHAPTER_FACTS_BUILT,
        target_state=PreprocessState.CHAPTER_FACTS_BUILT,
    )
    # We can't create an agent without a DB, but we can validate the request
    assert req.start_state == req.target_state
    print("  [PASS] same-state request validated")


async def test_build_chapter_facts_real(book_id: int):
    """Real BUILD_CHAPTER_FACTS execution against actual data."""
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"  [SKIP] MySQL not available: {e}")
        return

    # Verify the book exists and has chunks
    with conn.cursor() as c:
        c.execute("SELECT id, title FROM novel_book WHERE id = %s", (book_id,))
        book = c.fetchone()
        if not book:
            print(f"  [SKIP] Book {book_id} not found")
            return
        c.execute("SELECT COUNT(*) as n FROM novel_chapter WHERE book_id = %s", (book_id,))
        chapters = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) as n FROM novel_chunk WHERE book_id = %s", (book_id,))
        chunks = c.fetchone()["n"]
        print(f"  Book: {book['title']} ({chapters} chapters, {chunks} chunks)")

    # Run the agent — needs confirm_token for dangerous actions
    agent = PreprocessAgent(db)
    # Get the expected token from plan
    plan = await agent.plan(
        book_id=book_id,
        start_state=PreprocessState.CHAPTER_FACTS_BUILT,
        target_state=PreprocessState.INDEXED,
    )
    result = await agent.run(PreprocessRequest(
        book_id=book_id,
        start_state=PreprocessState.CHAPTER_FACTS_BUILT,
        target_state=PreprocessState.INDEXED,
        confirm_token=plan.required_confirm_token,
    ))

    print(f"  Final status   : {result.status.value}")
    print(f"  Run ID         : {result.run_id}")
    print(f"  Completed      : {result.completed_actions}")
    print(f"  Errors         : {result.errors}")

    if result.status == PreprocessState.INDEXED:
        print("  [PASS] PreprocessAgent completed CHAPTER_FACTS_BUILT -> INDEXED")
    elif result.status == PreprocessState.FAILED:
        print(f"  [FAIL] Step failed: {result.errors}")
    else:
        print(f"  [NOTE] Unexpected status: {result.status}")

    db.close()


async def test_plan_real(book_id: int):
    """Test plan() — dry-run, must not write any data."""
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"  [SKIP] MySQL not available: {e}")
        return

    agent = PreprocessAgent(db)
    try:
        # Plan CHAPTER_FACTS_BUILT -> INDEXED
        plan = await agent.plan(
            book_id=book_id,
            start_state=PreprocessState.CHAPTER_FACTS_BUILT,
            target_state=PreprocessState.INDEXED,
        )
        print(f"  Plan start={plan.start_state} target={plan.target_state}")
        print(f"  Steps: {len(plan.steps)}")
        for s in plan.steps:
            print(f"    {s.action}: will_run={s.will_run} "
                  f"danger={s.danger_level} confirm={s.required_confirmation} "
                  f"skip='{s.skip_reason}'")
            if s.estimated_effect:
                print(f"      effect={s.estimated_effect}")

        # Verify invariants
        assert len(plan.steps) > 0, "Plan should have at least one step"
        for s in plan.steps:
            if s.will_run:
                assert s.danger_level in ("low", "medium", "high", "critical")
                assert s.required_confirmation in (True, False)
            if not s.will_run:
                assert s.skip_reason, "Skipped step must have skip_reason"
        assert plan.has_high_risk or plan.has_critical_risk

        # Verify no AgentRun was created (verify plan is truly dry)
        with conn.cursor() as c:
            c.execute(
                "SELECT COUNT(*) as n FROM novel_agent_run "
                "WHERE run_type LIKE 'PreprocessAgent/plan%'",
            )
            row = c.fetchone()
            plan_runs = row["n"] if row else 0
        print(f"  Plan runs in DB: {plan_runs} (should be 0)")
        assert plan_runs == 0, "plan() must not create AgentRun records"

        # Test reversed states
        plan2 = await agent.plan(
            book_id=book_id,
            start_state=PreprocessState.INDEXED,
            target_state=PreprocessState.CHAPTER_FACTS_BUILT,
        )
        assert len(plan2.warnings) > 0
        assert len(plan2.steps) == 0

        print(f"  [PASS] plan() dry-run confirmed for book {book_id}")
    finally:
        db.close()


async def test_confirm_token_guard(book_id: int):
    """Test confirm token guard: missing, wrong, and correct."""
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"  [SKIP] MySQL not available: {e}")
        return

    agent = PreprocessAgent(db)
    try:
        # 1. No token → NEED_REVIEW
        result_no = await agent.run(PreprocessRequest(
            book_id=book_id,
            start_state=PS.CHAPTER_FACTS_BUILT,
            target_state=PS.INDEXED,
        ))
        assert result_no.status == PS.NEED_REVIEW, (
            f"Expected NEED_REVIEW, got {result_no.status}"
        )
        assert not result_no.run_id, "No AgentRun should be created"
        assert result_no.required_confirm_token, "Expected confirm token hint"
        print(f"  [PASS] No token → NEED_REVIEW (hint={result_no.required_confirm_token[:8]}...)")

        # 2. Wrong token → FAILED
        result_wrong = await agent.run(PreprocessRequest(
            book_id=book_id,
            start_state=PS.CHAPTER_FACTS_BUILT,
            target_state=PS.INDEXED,
            confirm_token="wrong_token",
        ))
        assert result_wrong.status == PS.FAILED, (
            f"Expected FAILED, got {result_wrong.status}"
        )
        assert not result_wrong.run_id, "No AgentRun should be created"
        print(f"  [PASS] Wrong token → FAILED")

        # 3. Correct token → success
        plan = await agent.plan(
            book_id=book_id,
            start_state=PS.CHAPTER_FACTS_BUILT,
            target_state=PS.INDEXED,
        )
        result_ok = await agent.run(PreprocessRequest(
            book_id=book_id,
            start_state=PS.CHAPTER_FACTS_BUILT,
            target_state=PS.INDEXED,
            confirm_token=plan.required_confirm_token,
        ))
        assert result_ok.status == PS.INDEXED, (
            f"Expected INDEXED, got {result_ok.status}"
        )
        assert result_ok.run_id, "AgentRun should be created"
        print(f"  [PASS] Correct token → INDEXED (run_id={result_ok.run_id})")

        # 4. Same-state no-op: no token required
        result_noop = await agent.run(PreprocessRequest(
            book_id=book_id,
            start_state=PS.CHAPTER_FACTS_BUILT,
            target_state=PS.CHAPTER_FACTS_BUILT,
        ))
        assert result_noop.status == PS.CHAPTER_FACTS_BUILT
        print(f"  [PASS] Same-state no-op: no token required")

        print(f"  [PASS] Confirm token guard confirmed for book {book_id}")
    finally:
        db.close()


def main():
    print("=" * 60)
    print("PreprocessAgent smoke test")
    print("=" * 60)

    # 1. Syntax + import tests (no DB needed)
    print("\n--- Static tests ---")
    test_import_and_schemas()
    test_noop_same_state()

    # 2. Confirm token guard (requires MySQL)
    print("\n--- Confirm token guard (book 6) ---")
    asyncio.run(test_confirm_token_guard(book_id=6))

    # 3. Plan test (dry-run, read-only)
    print("\n--- Plan dry-run (book 6) ---")
    asyncio.run(test_plan_real(book_id=6))

    # 4. Real execution (requires MySQL tunnel)
    print("\n--- Real execution (book 6, 西游记) ---")
    asyncio.run(test_build_chapter_facts_real(book_id=6))

    print("\n" + "=" * 60)
    print("Done")


if __name__ == "__main__":
    main()
