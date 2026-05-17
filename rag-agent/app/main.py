"""
NovelBridge — rag-agent 最小服务

Demo 5A 职责：
- 提供 /health 及子路径健康检查端点
- 提供 Spring Boot 的 HTTP 调用入口

后续 Demo 5B+ 扩展：
- POST /extract/entities — 实体抽取
- POST /extract/events — 事件抽取（Demo 6）
- POST /extract/relations — 关系抽取（Demo 6）
- POST /extract/claims — Claim 抽取（Demo 6）
- POST /qa/answer — 问答（Demo 7）
- POST /admin/reload-prompts — 重载 Prompt
- POST /admin/reload-grammars — 重载 Grammar
"""

import argparse
import os
import socket
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

# ---- 健康检查模型 ----

class ServiceHealth(BaseModel):
    status: str  # "UP" | "DOWN" | "MOCK"
    host: str
    port: int
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "UP"
    llama_cpp: str = "MOCK"
    mysql: str = "MOCK"
    neo4j: str = "MOCK"
    vector: str = "MOCK"
    model: str = "N/A"
    grammar_enabled: bool = False


# ---- 服务状态（Demo 5A 从环境变量读取） ----

LLAMA_HOST = os.getenv("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.getenv("LLAMA_PORT", "18080"))
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "13306"))
NEO4J_HOST = os.getenv("NEO4J_HOST", "127.0.0.1")
NEO4J_HTTP_PORT = int(os.getenv("NEO4J_HTTP_PORT", "17474"))
NEO4J_BOLT_PORT = int(os.getenv("NEO4J_BOLT_PORT", "17687"))
VECTOR_DB_HOST = os.getenv("VECTOR_DB_HOST", "127.0.0.1")
VECTOR_DB_PORT = int(os.getenv("VECTOR_DB_PORT", "16333"))

# 本服务端口
RAG_AGENT_PORT = int(os.getenv("RAG_AGENT_PORT", "18081"))


# ---- 工具函数 ----

def _check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    """检查 TCP 端口是否可连接。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _get_service_health(name: str, host: str, port: int, mock: bool = False) -> str:
    """返回服务状态: UP / DOWN / MOCK。"""
    if mock:
        return "MOCK"
    try:
        if _check_tcp(host, port):
            return "UP"
        return "DOWN"
    except Exception:
        return "DOWN"


# ---- 应用生命周期 ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    print(f"[rag-agent] 启动于端口 {RAG_AGENT_PORT}")
    print(f"[rag-agent] 健康检查目标: llama={LLAMA_HOST}:{LLAMA_PORT}, "
          f"mysql={MYSQL_HOST}:{MYSQL_PORT}, "
          f"neo4j={NEO4J_HOST}:{NEO4J_HTTP_PORT}, "
          f"vector={VECTOR_DB_HOST}:{VECTOR_DB_PORT}")
    yield
    # 关闭时
    print("[rag-agent] 关闭")


app = FastAPI(
    title="NovelBridge rag-agent",
    version="0.1.0",
    description="模型编排与检索服务 — Demo 5A",
    lifespan=lifespan,
)


# ---- 健康检查端点 ----

@app.get("/health", response_model=HealthResponse)
async def health_root():
    """聚合健康检查。"""
    llama_status = _get_service_health("llama", LLAMA_HOST, LLAMA_PORT, mock=False)
    # 如果 llama-server 未运行但端口不通，记为 DOWN
    if llama_status == "DOWN":
        # 但 llama-server 在 Demo 5A 可以是 mock
        llama_status = "MOCK"

    return HealthResponse(
        status="UP",
        llama_cpp=llama_status,
        mysql=_get_service_health("mysql", MYSQL_HOST, MYSQL_PORT),
        neo4j=_get_service_health("neo4j", NEO4J_HOST, NEO4J_HTTP_PORT),
        vector=_get_service_health("vector", VECTOR_DB_HOST, VECTOR_DB_PORT, mock=True),
        model=os.getenv("NB_MODEL_NAME", "Qwen3.6-35B-A3B"),
        grammar_enabled=True,
    )


@app.get("/health/llm", response_model=ServiceHealth)
async def health_llm():
    """LLM 服务健康检查。"""
    return ServiceHealth(
        status=_get_service_health("llama", LLAMA_HOST, LLAMA_PORT, mock=False),
        host=LLAMA_HOST,
        port=LLAMA_PORT,
        detail="llama.cpp OpenAI-compatible endpoint",
    )


@app.get("/health/mysql", response_model=ServiceHealth)
async def health_mysql():
    """MySQL 健康检查。"""
    status = _get_service_health("mysql", MYSQL_HOST, MYSQL_PORT)
    return ServiceHealth(
        status=status,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        detail="MySQL via Docker" if status == "UP" else "unreachable",
    )


@app.get("/health/neo4j", response_model=ServiceHealth)
async def health_neo4j():
    """Neo4j 健康检查。"""
    status = _get_service_health("neo4j", NEO4J_HOST, NEO4J_HTTP_PORT)
    return ServiceHealth(
        status=status,
        host=NEO4J_HOST,
        port=NEO4J_HTTP_PORT,
        detail="Neo4j HTTP endpoint" if status == "UP" else "unreachable",
    )


@app.get("/health/vector", response_model=ServiceHealth)
async def health_vector():
    """向量库健康检查（Demo 5A Mock）。"""
    return ServiceHealth(
        status=_get_service_health("vector", VECTOR_DB_HOST, VECTOR_DB_PORT, mock=True),
        host=VECTOR_DB_HOST,
        port=VECTOR_DB_PORT,
        detail="Demo 5A: service started, retrieval not required",
    )


# ---- 预留端点桩 ----

@app.post("/extract/entities")
async def extract_entities():
    """实体抽取（Demo 5B 实现）。"""
    return {"status": "NOT_IMPLEMENTED", "detail": "Demo 5B"}


@app.post("/admin/reload-prompts")
async def reload_prompts():
    """重载 Prompt 模板（Demo 5B 实现）。"""
    return {"status": "NOT_IMPLEMENTED", "detail": "Demo 5B"}


@app.post("/admin/reload-grammars")
async def reload_grammars():
    """重载 GBNF Grammar（Demo 5B 实现）。"""
    return {"status": "NOT_IMPLEMENTED", "detail": "Demo 5B"}


# ---- 入口 ----

def main():
    parser = argparse.ArgumentParser(description="NovelBridge rag-agent")
    parser.add_argument("--port", type=int, default=RAG_AGENT_PORT,
                        help=f"监听端口（默认 {RAG_AGENT_PORT}）")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="监听地址（默认 0.0.0.0）")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
