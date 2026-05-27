from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

from app.clients.mysql_client import MysqlClient
from app.schemas.health import HealthResponse, HealthSummary

router = APIRouter()
db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


def _ok(service: str, detail: str = "") -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=service,
        detail=detail or f"{service} is configured",
        timestamp=datetime.now(timezone.utc),
    )


def _unavailable(service: str, detail: str = "") -> HealthResponse:
    return HealthResponse(
        status="unavailable",
        service=service,
        detail=detail or f"{service} is not available",
        timestamp=datetime.now(timezone.utc),
    )


def _from_check(service: str, check: dict) -> HealthResponse:
    status = check.get("status", "unavailable")
    if status == "configured":
        status = "unavailable"
    return HealthResponse(
        status=status,
        service=service,
        detail=check.get("detail", ""),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health", response_model=HealthSummary)
async def health_overall():
    """Overall health summary of all services."""
    checks = {
        "app": _ok("app", "rag-agent is running"),
        "mysql": await health_mysql(),
        "qdrant": await health_qdrant(),
        "neo4j": await health_neo4j(),
        "llm": await health_llm(),
        "embedding": await health_embedding(),
    }
    overall = "ok" if all(c.status == "ok" for c in checks.values()) else "degraded"
    return HealthSummary(status=overall, services=checks)


@router.get("/health/mysql", response_model=HealthResponse)
async def health_mysql():
    """Check MySQL connectivity."""
    if db_client is None:
        return _unavailable("mysql", "MySQL client not initialized")
    return _from_check("mysql", await db_client.health_check())


@router.get("/health/qdrant", response_model=HealthResponse)
async def health_qdrant():
    """Check Qdrant connectivity."""
    from app.clients.qdrant_client import qdrant_client

    return _from_check("qdrant", await qdrant_client.health_check())


@router.get("/health/neo4j", response_model=HealthResponse)
async def health_neo4j():
    """Check Neo4j connectivity."""
    from app.clients.neo4j_client import neo4j_client

    return _from_check("neo4j", await neo4j_client.health_check())


@router.get("/health/llm", response_model=HealthResponse)
async def health_llm():
    """Check llama-server connectivity."""
    from app.clients.llama_cpp_client import llama_client

    return _from_check("llm", await llama_client.health_check())


@router.get("/health/embedding", response_model=HealthResponse)
async def health_embedding():
    """Check embedding llama-server or local embedding model connectivity."""
    from app.clients.embedding_client import embedding_client

    return _from_check("embedding", await embedding_client.health_check())
