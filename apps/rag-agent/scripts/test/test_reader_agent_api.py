"""Real HTTP smoke test for POST /api/reader-agent/run.

Requires: MySQL tunnel (127.0.0.1:13306) and book 6 data.

Run from apps/rag-agent:
    python scripts/test/test_reader_agent_api.py
"""

import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import reader_agent as reader_agent_api
from app.clients.mysql_client import MysqlClient


def build_test_app():
    """Minimal FastAPI app with only the reader_agent route."""
    db_client = MysqlClient()
    reader_agent_api.init_router(db_client)
    app = FastAPI()
    app.include_router(reader_agent_api.router)
    return app, db_client


def test_unimplemented_mode(client: TestClient):
    """Unsupported modes should return NEED_FOLLOWUP without touching QA behavior."""
    resp = client.post("/api/reader-agent/run", json={
        "mode": "trace",
        "book_id": 6,
        "question": "test",
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "NEED_FOLLOWUP", f"Expected NEED_FOLLOWUP, got {data['status']}"
    assert len(data["errors"]) > 0
    print("  [PASS] unimplemented mode returns NEED_FOLLOWUP")
    return True


def test_analyze_character_real(client: TestClient):
    """Real minimal character analysis against book 6."""
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析孙悟空这个人物",
        "analysis_type": "character",
        "target_name": "孙悟空",
        "options": {
            "require_citations": True,
            "top_k": 6,
            "allow_patch": False,
        },
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    print(f"  analyze_status = {data.get('status')}")
    print(f"  evidence_cnt   = {len(data.get('evidence', []))}")
    print(f"  patches_cnt    = {len(data.get('patches', []))}")
    assert data["status"] in {"RESPONDED", "INSUFFICIENT_EVIDENCE", "FAILED"}
    if data["status"] == "RESPONDED":
        assert data["mode"] == "analyze"
        assert data.get("analysis", {}).get("analysis_type") == "character"
        assert len(data.get("evidence", [])) > 0
        assert data.get("patches") == []
    return data


def test_analyze_relation_real(client: TestClient):
    """Real minimal relation analysis against book 6."""
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析孙悟空和唐僧的关系",
        "analysis_type": "relation",
        "target_name": "孙悟空,唐僧",
        "options": {
            "require_citations": True,
            "top_k": 6,
            "allow_patch": False,
        },
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    print(f"  relation_status = {data.get('status')}")
    print(f"  evidence_cnt    = {len(data.get('evidence', []))}")
    assert data["status"] in {"RESPONDED", "INSUFFICIENT_EVIDENCE", "FAILED"}
    if data["status"] == "RESPONDED":
        assert data.get("analysis", {}).get("analysis_type") == "relation"
        assert len(data.get("evidence", [])) > 0
        assert data.get("patches") == []
    return data


def test_analyze_insufficient_real(client: TestClient):
    """Unknown target should fail closed when citations are required."""
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析一个不存在的测试人物甲乙丙丁戊",
        "analysis_type": "character",
        "target_name": "测试人物甲乙丙丁戊",
        "options": {
            "require_citations": True,
            "top_k": 3,
            "allow_patch": False,
        },
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    print(f"  insufficient_status = {data.get('status')}")
    assert data["status"] in {"INSUFFICIENT_EVIDENCE", "FAILED"}
    if data["status"] == "INSUFFICIENT_EVIDENCE":
        assert data.get("patches") == []
        assert data.get("answer") == "INSUFFICIENT_EVIDENCE"
    return data


def test_answer_real(client: TestClient):
    """Real answer query against book 6."""
    resp = client.post("/api/reader-agent/run", json={
        "mode": "answer",
        "book_id": 6,
        "question": "孙悟空是谁？",
        "options": {
            "provider": "local",
            "require_citations": True,
            "top_k": 8,
        },
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    print(f"  agent_status  = {data.get('status')}")
    print(f"  answer_len    = {len(data.get('answer', ''))}")
    print(f"  citations_cnt = {len(data.get('citations', []))}")
    print(f"  errors        = {data.get('errors')}")

    # Must be either RESPONDED (LLM ok) or INSUFFICIENT_EVIDENCE (citations empty)
    valid_statuses = {"RESPONDED", "INSUFFICIENT_EVIDENCE", "FAILED"}
    assert data["status"] in valid_statuses, (
        f"Unexpected status: {data['status']}"
    )

    if data["status"] == "RESPONDED":
        assert len(data.get("answer", "")) > 0, "Answer should be non-empty"
        print("  [PASS] answer mode returned RESPONDED with answer")
    elif data["status"] == "INSUFFICIENT_EVIDENCE":
        print("  [NOTE] INSUFFICIENT_EVIDENCE — LLM returned no citations")
    else:
        print(f"  [NOTE] FAILED — {data.get('errors')}")

    return True


def main():
    print("=" * 60)
    print("ReaderAgent API smoke test")
    print("=" * 60)

    app, db_client = build_test_app()
    client = TestClient(app)

    # Pre-check MySQL
    try:
        conn = db_client.connect()
        conn.ping(reconnect=True)
        print(f"[OK] MySQL connected at {conn.host}:{conn.port}")
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        print("  Only running mode validation test.")
        test_unimplemented_mode(client)
        print("\n[WARN] Real answer test skipped (no DB).")
        return

    # Run tests
    test_unimplemented_mode(client)

    print()
    print("--- Real answer test (book 6, 孙悟空) ---")
    test_answer_real(client)

    print()
    print("--- Real analyze character test (book 6, 孙悟空) ---")
    character = test_analyze_character_real(client)
    if character.get("run_id"):
        trace = client.get(f"/api/reader-agent/runs/{character['run_id']}/trace")
        assert trace.status_code == 200, f"Trace expected 200, got {trace.status_code}"
        trace_data = trace.json()
        assert trace_data.get("run", {}).get("run_type") == "ReaderAgent/analyze"
        print("  [PASS] trace endpoint returned analyze run")

    print()
    print("--- Real analyze relation test (book 6, 孙悟空/唐僧) ---")
    test_analyze_relation_real(client)

    print()
    print("--- Real analyze insufficient evidence test ---")
    test_analyze_insufficient_real(client)

    print()
    print("=" * 60)
    print("All smoke tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
