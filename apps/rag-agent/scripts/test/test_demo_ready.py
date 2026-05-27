"""Live demo readiness check for Stage 6C.

Run after starting rag-agent:
    python -B scripts/test/test_demo_ready.py
    python -B scripts/test/test_demo_ready.py --include-answer
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:18081"
PORTS = {
    "mysql": 13306,
    "qdrant": 16333,
    "neo4j_http": 17474,
    "neo4j_bolt": 17687,
    "llm_9b": 18080,
    "embedding": 18082,
}


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


async def get_json(client: httpx.AsyncClient, path: str) -> dict[str, Any]:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


async def post_json(client: httpx.AsyncClient, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def mode_payloads(include_answer: bool) -> list[tuple[str, dict[str, Any], str]]:
    payloads: list[tuple[str, dict[str, Any], str]] = []
    if include_answer:
        payloads.append(
            (
                "answer",
                {
                    "mode": "answer",
                    "book_id": 6,
                    "question": "火焰山的火是怎么来的？",
                    "options": {"provider": "local", "require_citations": True, "top_k": 8},
                },
                "RESPONDED",
            )
        )
    payloads.extend(
        [
            (
                "analyze_character",
                {
                    "mode": "analyze",
                    "book_id": 6,
                    "question": "分析孙悟空的人物形象。",
                    "analysis_type": "character",
                    "target_name": "孙悟空",
                    "target_type": "character",
                    "options": {"provider": "local", "require_citations": True, "top_k": 10},
                },
                "RESPONDED",
            ),
            (
                "trace_relation",
                {
                    "mode": "trace",
                    "book_id": 6,
                    "question": "追踪孙悟空和唐僧关系变化。",
                    "trace_target_type": "character",
                    "target_name": "孙悟空,唐僧",
                    "target_type": "relation",
                    "options": {"provider": "local", "require_citations": True, "top_k": 10},
                },
                "RESPONDED",
            ),
            (
                "enrich_candidate",
                {
                    "mode": "enrich",
                    "book_id": 6,
                    "question": "基于证据生成一个 citation_fix KnowledgePatch candidate。",
                    "issue_type": "citation_fix",
                    "target": "demo:citation_fix",
                    "target_type": "citation",
                    "evidence": [
                        {
                            "source_type": "citation",
                            "source_id": 1,
                            "chapter_id": 1,
                            "excerpt": "用于演示低风险 KnowledgePatch candidate，不自动 merge。",
                            "evidence_level": "DIRECT",
                            "relevance_score": 1.0,
                        }
                    ],
                    "options": {"provider": "local", "require_citations": True, "top_k": 5},
                },
                "RESPONDED",
            ),
        ]
    )
    return payloads


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--include-answer", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    print("NovelBridge demo readiness")
    for name, port in PORTS.items():
        ok = tcp_open("127.0.0.1", port)
        print(f"[{'PASS' if ok else 'FAIL'}] port {name}: 127.0.0.1:{port}")
        if not ok:
            failures.append(f"port {name} closed")

    async with httpx.AsyncClient(base_url=args.base_url, timeout=45.0, follow_redirects=True) as client:
        for path in ["/demo", "/browse", "/agent-runs"]:
            try:
                response = await client.get(path)
                ok = response.status_code == 200 and "NovelBridge" in response.text
            except Exception as exc:
                ok = False
                response = None
                failures.append(f"{path} failed: {exc}")
            print(f"[{'PASS' if ok else 'FAIL'}] page {path}")
            if not ok and response is not None:
                failures.append(f"{path} status={response.status_code}")

        for service in ["mysql", "qdrant", "neo4j", "llm", "embedding"]:
            try:
                data = await get_json(client, f"/health/{service}")
                ok = data.get("status") == "ok"
            except Exception as exc:
                ok = False
                data = {"detail": str(exc)}
            print(f"[{'PASS' if ok else 'FAIL'}] health {service}: {data.get('status')} {data.get('detail', '')[:120]}")
            if not ok:
                failures.append(f"health {service} not ok")

        for name, payload, expected in mode_payloads(args.include_answer):
            try:
                data = await post_json(client, "/api/reader-agent/run", payload)
                status = data.get("status")
                run_id = data.get("run_id")
                ok = status == expected and bool(run_id)
            except Exception as exc:
                status = "error"
                run_id = None
                ok = False
                failures.append(f"mode {name} failed: {exc}")
            print(f"[{'PASS' if ok else 'FAIL'}] mode {name}: status={status} run_id={run_id}")
            if not ok:
                failures.append(f"mode {name} status={status} run_id={run_id}")

    if failures:
        print("\nDemo readiness failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nDemo readiness passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
