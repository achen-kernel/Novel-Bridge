"""Smoke test for KnowledgePatch propose + review flow with full review_logs.

Requires MySQL tunnel.
Run from apps/rag-agent:
    python scripts/test/test_knowledge_patch.py
"""
import asyncio, sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import knowledge_patch as kp_api
from app.clients.mysql_client import MysqlClient


async def main():
    db = MysqlClient()
    try:
        conn = db.connect()
        conn.ping(reconnect=True)
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        return

    kp_api.init_router(db)
    app = FastAPI()
    app.include_router(kp_api.router)
    client = TestClient(app)

    # ======== 1. Propose low-risk patch ========
    r1 = client.post("/api/knowledge-patches", json={
        "book_id": 6,
        "patch_type": "citation_fix",
        "target_type": "chunk",
        "target_id": 123,
        "payload": {"original": "text", "suggested": "new text"},
        "evidence": [{"source_type": "chunk", "source_id": 123, "excerpt": "test evidence", "evidence_level": "DIRECT"}],
        "risk_level": "low",
        "created_by": "smoke_test",
    })
    d1 = r1.json()
    print(f"[PASS] Propose low-risk: ok={d1['ok']} id={d1['patch_id']} status={d1['status']}")
    assert d1["ok"]
    assert d1["status"] == "PENDING_REVIEW"
    patch_id = d1["patch_id"]

    # ======== 2. Propose high-risk patch (critical) ========
    r2 = client.post("/api/knowledge-patches", json={
        "book_id": 6,
        "patch_type": "entity_merge",
        "target_type": "entity",
        "target_id": 1,
        "payload": {"merge_with": 2},
        "evidence": [{"source_type": "chunk", "source_id": 1, "excerpt": "merge evidence", "evidence_level": "DIRECT"}],
        "risk_level": "critical",
        "created_by": "smoke_test",
    })
    d2 = r2.json()
    print(f"[PASS] Propose critical: ok={d2['ok']} id={d2['patch_id']} status={d2['status']}")
    assert d2["ok"]
    assert d2["status"] in ("PROPOSED", "PENDING_REVIEW")

    # ======== 3. List patches (check review_count) ========
    r3 = client.get("/api/knowledge-patches?book_id=6")
    patches = r3.json()
    print(f"[PASS] List patches: {len(patches)} found")
    assert len(patches) >= 2
    # Check review_count field exists
    if patches:
        assert "review_count" in patches[0], "list must return review_count"
        assert "evidence_count" in patches[0], "list must return evidence_count"

    # ======== 4. Get single patch (check review_logs) ========
    r4 = client.get(f"/api/knowledge-patches/{patch_id}")
    d4 = r4.json()
    print(f"[PASS] Get patch {patch_id}: type={d4['patch_type']}")
    assert d4["patch_type"] == "citation_fix"
    assert "review_logs" in d4, "get_patch must return review_logs"
    assert "evidence" in d4, "get_patch must return evidence"
    print(f"  review_logs count: {len(d4.get('review_logs', []))}")
    print(f"  evidence count: {len(d4.get('evidence', []))}")

    # ======== 5. Review with action=ACCEPT ========
    r5 = client.post(f"/api/knowledge-patches/{patch_id}/review", json={
        "action": "ACCEPT",
        "note": "Looks good",
        "reviewed_by": "smoke_test",
    })
    d5 = r5.json()
    print(f"[PASS] Review ACCEPT: ok={d5['ok']} status={d5['status']}")
    assert d5["ok"]
    assert d5["status"] == "ACCEPTED"

    # Verify review_logs now has an entry
    r5b = client.get(f"/api/knowledge-patches/{patch_id}")
    d5b = r5b.json()
    logs = d5b.get("review_logs", [])
    assert len(logs) >= 1, "Review should create a review_log entry"
    last = logs[-1]
    print(f"  Review log: action={last.get('action')} from={last.get('previous_status')} to={last.get('new_status')}")
    assert last.get("action") == "ACCEPT"
    assert last.get("previous_status") in ("PENDING_REVIEW", "PROPOSED")
    assert last.get("new_status") == "ACCEPTED"

    # ======== 6. Review with action=REJECT ========
    pid2 = patch_id + 1  # use the critical patch
    r6 = client.post(f"/api/knowledge-patches/{pid2}/review", json={
        "action": "REJECT",
        "note": "Not enough evidence",
        "reviewed_by": "smoke_test",
    })
    d6 = r6.json()
    print(f"[PASS] Review REJECT: ok={d6['ok']} status={d6['status']}")
    assert d6["ok"]
    assert d6["status"] == "REJECTED"

    # ======== 7. Review with action=NEEDS_MORE_EVIDENCE ========
    # Create a new patch for this
    r7a = client.post("/api/knowledge-patches", json={
        "book_id": 6,
        "patch_type": "citation_fix",
        "target_type": "chunk", "target_id": 456,
        "payload": {"note": "test"},
        "evidence": [{"source_type": "chunk", "source_id": 456, "excerpt": "ev", "evidence_level": "DIRECT"}],
        "risk_level": "low", "created_by": "smoke_test",
    })
    pid3 = r7a.json()["patch_id"]
    r7 = client.post(f"/api/knowledge-patches/{pid3}/review", json={
        "action": "NEEDS_MORE_EVIDENCE",
        "note": "Please add chapter context",
        "reviewed_by": "smoke_test",
    })
    d7 = r7.json()
    print(f"[PASS] Review NEEDS_MORE_EVIDENCE: ok={d7['ok']} status={d7['status']}")
    assert d7["ok"]
    assert d7["status"] == "NEEDS_MORE_EVIDENCE"

    # ======== 8. Review with action=SUPERSEDE ========
    r8a = client.post("/api/knowledge-patches", json={
        "book_id": 6,
        "patch_type": "citation_fix",
        "target_type": "chunk", "target_id": 789,
        "payload": {"note": "test"},
        "evidence": [{"source_type": "chunk", "source_id": 789, "excerpt": "ev", "evidence_level": "DIRECT"}],
        "risk_level": "low", "created_by": "smoke_test",
    })
    pid4 = r8a.json()["patch_id"]
    r8 = client.post(f"/api/knowledge-patches/{pid4}/review", json={
        "action": "SUPERSEDE",
        "note": "Replaced by newer patch",
        "reviewed_by": "smoke_test",
    })
    d8 = r8.json()
    print(f"[PASS] Review SUPERSEDE: ok={d8['ok']} status={d8['status']}")
    assert d8["ok"]
    assert d8["status"] == "SUPERSEDED"

    # ======== 9. Review on non-existent patch ========
    r9 = client.post("/api/knowledge-patches/999999/review", json={
        "action": "ACCEPT",
        "note": "Should fail",
        "reviewed_by": "smoke_test",
    })
    d9 = r9.json()
    print(f"[PASS] Review non-existent: ok={d9['ok']} errors={d9['errors']}")
    assert not d9["ok"]
    assert len(d9["errors"]) > 0

    # ======== 10. Backward compat: approved=True ========
    r10a = client.post("/api/knowledge-patches", json={
        "book_id": 6,
        "patch_type": "citation_fix",
        "target_type": "chunk", "target_id": 111,
        "payload": {"note": "compat test"},
        "evidence": [{"source_type": "chunk", "source_id": 111, "excerpt": "ev", "evidence_level": "DIRECT"}],
        "risk_level": "low", "created_by": "smoke_test",
    })
    pid5 = r10a.json()["patch_id"]
    r10 = client.post(f"/api/knowledge-patches/{pid5}/review", json={
        "approved": True,
        "note": "Old-style approve",
        "reviewed_by": "smoke_test",
    })
    d10 = r10.json()
    print(f"[PASS] Backward compat approved=True: ok={d10['ok']} status={d10['status']}")
    assert d10["ok"]
    assert d10["status"] == "ACCEPTED"

    print("\n[PASS] All KnowledgePatch tests passed")
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
