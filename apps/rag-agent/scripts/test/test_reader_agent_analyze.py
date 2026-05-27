"""Smoke test for ReaderAgent analyze mode.

Run from apps/rag-agent:
    python -B scripts/test/test_reader_agent_analyze.py
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


def build_client():
    db_client = MysqlClient()
    reader_agent_api.init_router(db_client)
    app = FastAPI()
    app.include_router(reader_agent_api.router)
    return TestClient(app), db_client


def test_character(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析孙悟空这个人物",
        "analysis_type": "character",
        "target_name": "孙悟空",
        "options": {"require_citations": True, "top_k": 6, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESPONDED", data
    assert data["analysis"]["analysis_type"] == "character"
    assert data["evidence"]
    assert data["patches"] == []
    trace = client.get(f"/api/reader-agent/runs/{data['run_id']}/trace")
    assert trace.status_code == 200, trace.text
    assert trace.json()["run"]["run_type"] == "ReaderAgent/analyze"
    print("  [PASS] analyze character")


def test_relation(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析孙悟空和唐僧的关系",
        "analysis_type": "relation",
        "target_name": "孙悟空,唐僧",
        "options": {"require_citations": True, "top_k": 6, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESPONDED", data
    assert data["analysis"]["analysis_type"] == "relation"
    assert data["evidence"]
    assert data["patches"] == []
    print("  [PASS] analyze relation")


def test_insufficient(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "analyze",
        "book_id": 6,
        "question": "分析一个不存在的测试人物甲乙丙丁戊",
        "analysis_type": "character",
        "target_name": "测试人物甲乙丙丁戊",
        "options": {"require_citations": True, "top_k": 3, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE", data
    assert data["answer"] == "INSUFFICIENT_EVIDENCE"
    assert data["patches"] == []
    print("  [PASS] analyze insufficient evidence")


def main():
    print("=" * 60)
    print("ReaderAgent analyze smoke test")
    print("=" * 60)
    client, db_client = build_client()
    try:
        db_client.connect().ping(reconnect=True)
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        return
    test_character(client)
    test_relation(client)
    test_insufficient(client)
    print("All analyze smoke tests passed.")


if __name__ == "__main__":
    main()
