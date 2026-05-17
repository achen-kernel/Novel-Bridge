"""
Health check endpoints.
Moved from monolithic main.py to separate module.
"""

import os
import socket
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

LLAMA_HOST = os.getenv("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.getenv("LLAMA_PORT", "18080"))
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "13306"))
NEO4J_HOST = os.getenv("NEO4J_HOST", "127.0.0.1")
NEO4J_HTTP_PORT = int(os.getenv("NEO4J_HTTP_PORT", "17474"))
NEO4J_BOLT_PORT = int(os.getenv("NEO4J_BOLT_PORT", "17687"))
VECTOR_DB_HOST = os.getenv("VECTOR_DB_HOST", "127.0.0.1")
VECTOR_DB_PORT = int(os.getenv("VECTOR_DB_PORT", "16333"))


class ServiceHealth(BaseModel):
    status: str
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


def _check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _get_service_health(host: str, port: int, mock: bool = False) -> str:
    if mock:
        return "MOCK"
    try:
        if _check_tcp(host, port):
            return "UP"
        return "DOWN"
    except Exception:
        return "DOWN"


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_root():
    llama_status = _get_service_health(LLAMA_HOST, LLAMA_PORT, mock=False)
    if llama_status == "DOWN":
        llama_status = "MOCK"
    return HealthResponse(
        status="UP",
        llama_cpp=llama_status,
        mysql=_get_service_health(MYSQL_HOST, MYSQL_PORT),
        neo4j=_get_service_health(NEO4J_HOST, NEO4J_HTTP_PORT),
        vector=_get_service_health(VECTOR_DB_HOST, VECTOR_DB_PORT, mock=True),
        model=os.getenv("NB_MODEL_NAME", "Qwen3.6-35B-A3B"),
        grammar_enabled=True,
    )


@router.get("/health/llm", response_model=ServiceHealth)
async def health_llm():
    return ServiceHealth(
        status=_get_service_health(LLAMA_HOST, LLAMA_PORT, mock=False),
        host=LLAMA_HOST, port=LLAMA_PORT,
        detail="llama.cpp OpenAI-compatible endpoint",
    )


@router.get("/health/mysql", response_model=ServiceHealth)
async def health_mysql():
    status = _get_service_health(MYSQL_HOST, MYSQL_PORT)
    return ServiceHealth(
        status=status, host=MYSQL_HOST, port=MYSQL_PORT,
        detail="MySQL via Docker" if status == "UP" else "unreachable",
    )


@router.get("/health/neo4j", response_model=ServiceHealth)
async def health_neo4j():
    status = _get_service_health(NEO4J_HOST, NEO4J_HTTP_PORT)
    return ServiceHealth(
        status=status, host=NEO4J_HOST, port=NEO4J_HTTP_PORT,
        detail="Neo4j HTTP endpoint" if status == "UP" else "unreachable",
    )


@router.get("/health/vector", response_model=ServiceHealth)
async def health_vector():
    return ServiceHealth(
        status=_get_service_health(VECTOR_DB_HOST, VECTOR_DB_PORT, mock=True),
        host=VECTOR_DB_HOST, port=VECTOR_DB_PORT,
        detail="Demo 5A: service started, retrieval not required",
    )
