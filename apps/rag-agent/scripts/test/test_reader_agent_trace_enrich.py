"""Smoke test for ReaderAgent trace/enrich minimal modes.

Run from apps/rag-agent:
    python -B scripts/test/test_reader_agent_trace_enrich.py
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


def test_trace_character(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "trace",
        "book_id": 6,
        "question": "追踪孙悟空在西游记中的线索",
        "target_name": "孙悟空",
        "trace_target_type": "character",
        "options": {"require_citations": True, "top_k": 5, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESPONDED", data
    assert data["timeline"]
    assert data["evidence"]
    assert data["patches"] == []
    trace = client.get(f"/api/reader-agent/runs/{data['run_id']}/trace")
    assert trace.status_code == 200, trace.text
    assert trace.json()["run"]["run_type"] == "ReaderAgent/trace"
    print("  [PASS] trace character")


def test_trace_relation_change(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "trace",
        "book_id": 6,
        "question": "追踪孙悟空和唐僧关系变化",
        "target_name": "孙悟空,唐僧",
        "trace_target_type": "character",
        "options": {"require_citations": True, "top_k": 6, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESPONDED", data
    assert data["timeline"]
    assert any(
        item.get("kind") in {"relation_state", "relation_context"}
        for item in data["timeline"]
    ), data["timeline"]
    assert data["evidence"]
    print("  [PASS] trace relation change")


def test_trace_insufficient(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "trace",
        "book_id": 6,
        "question": "追踪不存在物件甲乙丙丁戊",
        "target_name": "不存在物件甲乙丙丁戊",
        "trace_target_type": "item",
        "options": {"require_citations": True, "top_k": 3, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE", data
    assert data["answer"] == "INSUFFICIENT_EVIDENCE"
    print("  [PASS] trace insufficient evidence")


def test_enrich_candidate(client: TestClient):
    evidence = [{
        "source_type": "chunk",
        "source_id": 1,
        "chapter_id": 1,
        "excerpt": "用于 enrich smoke test 的引用修复候选证据。",
        "evidence_level": "DIRECT",
        "relevance_score": 1.0,
    }]
    resp = client.post("/api/reader-agent/run", json={
        "mode": "enrich",
        "book_id": 6,
        "question": "为引用问题生成低风险候选补丁",
        "issue_type": "citation_fix",
        "target": "smoke-test-citation",
        "target_type": "citation",
        "evidence": evidence,
        "options": {"require_citations": True, "allow_patch": False},
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESPONDED", data
    assert len(data["patches"]) == 1
    assert data["patches"][0]["patch_type"] == "citation_fix"
    assert data["patches"][0]["status"] == "PENDING_REVIEW"
    print("  [PASS] enrich candidate")


def test_enrich_insufficient(client: TestClient):
    resp = client.post("/api/reader-agent/run", json={
        "mode": "enrich",
        "book_id": 6,
        "question": "缺少证据不应生成补丁",
        "issue_type": "citation_fix",
        "target": "missing-evidence",
        "target_type": "citation",
        "evidence": [],
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "INSUFFICIENT_EVIDENCE", data
    assert data["patches"] == []
    print("  [PASS] enrich insufficient evidence")


def main():
    print("=" * 60)
    print("ReaderAgent trace/enrich smoke test")
    print("=" * 60)
    client, db_client = build_client()
    try:
        db_client.connect().ping(reconnect=True)
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        return
    test_trace_character(client)
    test_trace_relation_change(client)
    test_trace_insufficient(client)
    test_enrich_candidate(client)
    test_enrich_insufficient(client)
    print("All trace/enrich smoke tests passed.")


if __name__ == "__main__":
    main()
