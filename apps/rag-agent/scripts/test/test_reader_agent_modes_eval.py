"""Small eval slice for ReaderAgent analyze/trace/enrich modes.

This does not replace the 37-case answer eval. It guards the new modes with
fast, evidence-focused checks.

Run from apps/rag-agent:
    python -B scripts/test/test_reader_agent_modes_eval.py
"""

import json
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import reader_agent as reader_agent_api
from app.clients.mysql_client import MysqlClient


CASES = [
    {
        "id": "analyze_character_sunwukong",
        "mode": "analyze",
        "payload": {
            "mode": "analyze",
            "book_id": 6,
            "question": "分析孙悟空这个人物",
            "analysis_type": "character",
            "target_name": "孙悟空",
            "options": {"require_citations": True, "top_k": 6},
        },
        "expect_status": "RESPONDED",
        "require_evidence": True,
        "require_patch": False,
    },
    {
        "id": "analyze_relation_sun_tang",
        "mode": "analyze",
        "payload": {
            "mode": "analyze",
            "book_id": 6,
            "question": "分析孙悟空和唐僧的关系",
            "analysis_type": "relation",
            "target_name": "孙悟空,唐僧",
            "options": {"require_citations": True, "top_k": 6},
        },
        "expect_status": "RESPONDED",
        "require_evidence": True,
        "require_patch": False,
    },
    {
        "id": "trace_character_sunwukong",
        "mode": "trace",
        "payload": {
            "mode": "trace",
            "book_id": 6,
            "question": "追踪孙悟空在西游记中的线索",
            "target_name": "孙悟空",
            "trace_target_type": "character",
            "options": {"require_citations": True, "top_k": 5},
        },
        "expect_status": "RESPONDED",
        "require_evidence": True,
        "require_timeline": True,
        "require_patch": False,
    },
    {
        "id": "trace_relation_sun_tang",
        "mode": "trace",
        "payload": {
            "mode": "trace",
            "book_id": 6,
            "question": "追踪孙悟空和唐僧关系变化",
            "target_name": "孙悟空,唐僧",
            "trace_target_type": "character",
            "options": {"require_citations": True, "top_k": 6},
        },
        "expect_status": "RESPONDED",
        "require_evidence": True,
        "require_timeline": True,
        "require_relation_timeline": True,
        "require_patch": False,
    },
    {
        "id": "trace_missing_item",
        "mode": "trace",
        "payload": {
            "mode": "trace",
            "book_id": 6,
            "question": "追踪不存在物件甲乙丙丁戊",
            "target_name": "不存在物件甲乙丙丁戊",
            "trace_target_type": "item",
            "options": {"require_citations": True, "top_k": 3},
        },
        "expect_status": "INSUFFICIENT_EVIDENCE",
        "require_evidence": False,
        "require_patch": False,
    },
    {
        "id": "enrich_citation_fix",
        "mode": "enrich",
        "payload": {
            "mode": "enrich",
            "book_id": 6,
            "question": "生成引用修复候选",
            "issue_type": "citation_fix",
            "target": "mode-eval-citation",
            "target_type": "citation",
            "evidence": [{
                "source_type": "chunk",
                "source_id": 1,
                "chapter_id": 1,
                "excerpt": "用于 ReaderAgent modes eval 的引用修复候选证据。",
                "evidence_level": "DIRECT",
                "relevance_score": 1.0,
            }],
            "options": {"require_citations": True},
        },
        "expect_status": "RESPONDED",
        "require_evidence": True,
        "require_patch": True,
    },
    {
        "id": "enrich_missing_evidence",
        "mode": "enrich",
        "payload": {
            "mode": "enrich",
            "book_id": 6,
            "question": "缺少证据不应生成补丁",
            "issue_type": "citation_fix",
            "target": "mode-eval-missing-evidence",
            "target_type": "citation",
            "evidence": [],
        },
        "expect_status": "INSUFFICIENT_EVIDENCE",
        "require_evidence": False,
        "require_patch": False,
    },
]


def build_client():
    db_client = MysqlClient()
    reader_agent_api.init_router(db_client)
    app = FastAPI()
    app.include_router(reader_agent_api.router)
    return TestClient(app), db_client


def run_case(client: TestClient, case: dict) -> dict:
    resp = client.post("/api/reader-agent/run", json=case["payload"])
    assert resp.status_code == 200, f"{case['id']} HTTP {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == case["expect_status"], f"{case['id']} got {data['status']}: {data}"
    if case.get("require_evidence"):
        assert data.get("evidence"), f"{case['id']} expected evidence"
    if case.get("require_timeline"):
        assert data.get("timeline"), f"{case['id']} expected timeline"
    if case.get("require_relation_timeline"):
        assert any(
            item.get("kind") in {"relation_state", "relation_context"}
            for item in data.get("timeline", [])
        ), f"{case['id']} expected relation timeline item"
    if case.get("require_patch"):
        assert data.get("patches"), f"{case['id']} expected patch candidate"
    if case.get("require_patch") is False:
        assert data.get("patches") == [], f"{case['id']} should not produce patches"
    return {
        "case_id": case["id"],
        "mode": case["mode"],
        "status": data["status"],
        "evidence_count": len(data.get("evidence") or []),
        "timeline_count": len(data.get("timeline") or []),
        "patch_count": len(data.get("patches") or []),
        "run_id": data.get("run_id"),
    }


def main():
    print("=" * 60)
    print("ReaderAgent modes eval")
    print("=" * 60)
    client, db_client = build_client()
    try:
        db_client.connect().ping(reconnect=True)
    except Exception as e:
        print(f"[SKIP] MySQL not available: {e}")
        return

    results = [run_case(client, case) for case in CASES]
    print(json.dumps({
        "total": len(results),
        "passed": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2))
    print("ReaderAgent modes eval passed.")


if __name__ == "__main__":
    main()
