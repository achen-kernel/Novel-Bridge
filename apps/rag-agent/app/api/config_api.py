"""
NovelBridge 服务配置 API。

提供可视化的服务连接配置管理，支持：
- 读取/写入配置（密钥掩码）
- 逐个服务连接测试
- 配置应用与重启提示
"""
import json
import logging
import socket
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.stores.config_store import config_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


# ── Models ──

class ServiceConfig(BaseModel):
    deepseek: dict[str, Any] = {}
    mysql: dict[str, Any] = {}
    qdrant: dict[str, Any] = {}
    neo4j: dict[str, Any] = {}
    llama: dict[str, Any] = {}
    embedding: dict[str, Any] = {}
    ssh: dict[str, Any] = {}


class TestResult(BaseModel):
    service: str
    success: bool
    message: str = ""
    latency_ms: float = 0.0


class ApplyResult(BaseModel):
    status: str  # "restart_required" | "applied" | "error"
    message: str = ""
    changed_services: list[str] = []


# ── Endpoints ──

@router.get("", response_model=ServiceConfig)
async def get_config():
    """读取当前配置（敏感字段已掩码）。"""
    return ServiceConfig(**config_store.load_public())


@router.put("", response_model=dict)
async def save_config(config: ServiceConfig):
    """保存完整配置。"""
    raw = config.model_dump()
    # 保留未修改的密钥：前端密码框对掩码值显示为空，用户没重新输入则传空字符串。
    # 此时不能覆盖真实 key，需要从当前保存的配置中保留旧值。
    current = config_store.load()
    for section, fields in raw.items():
        if isinstance(fields, dict):
            for key, value in fields.items():
                if key in ("api_key", "password"):
                    if not value or "*" in str(value):
                        # 值为空 或 仍是掩码 → 保留旧值
                        raw[section][key] = current.get(section, {}).get(key, "")
    ok = config_store.save(raw)
    return {"status": "ok" if ok else "error", "message": "配置已保存" if ok else "保存失败"}


@router.post("/test/{service}", response_model=TestResult)
async def test_connection(service: str):
    """测试指定服务的连接。支持的 service: mysql, qdrant, neo4j, llama, embedding, ssh"""
    config = config_store.load()
    service_config = config.get(service)
    if not service_config:
        return TestResult(service=service, success=False, message=f"未知服务: {service}")

    import time
    t0 = time.time()

    try:
        if service == "mysql":
            return await _test_mysql(service_config)
        elif service == "qdrant":
            return await _test_qdrant(service_config)
        elif service == "neo4j":
            return await _test_neo4j(service_config)
        elif service == "llama":
            return await _test_llama(service_config)
        elif service == "embedding":
            return await _test_embedding(service_config)
        elif service == "deepseek":
            return await _test_deepseek(service_config)
        elif service == "ssh":
            return await _test_ssh(service_config)
        else:
            return TestResult(service=service, success=False, message=f"不支持的服务: {service}")
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service=service, success=False, message=str(e), latency_ms=round(elapsed, 1))


@router.post("/apply", response_model=ApplyResult)
async def apply_config():
    """应用配置，检测哪些服务配置有变化，返回重启建议。"""
    config = config_store.load()
    changed = []

    # 检测各服务配置是否与当前运行的 settings 一致
    from app.config import settings

    # MySQL
    mysql = config.get("mysql", {})
    if mysql.get("host") and f"{mysql['host']}:{mysql.get('port')}" != f"{settings.mysql_host}:{settings.mysql_port}":
        changed.append("mysql")

    # Qdrant
    qdrant = config.get("qdrant", {})
    if qdrant.get("host"):
        expected_qdrant = f"http://{qdrant['host']}:{qdrant.get('port', 16333)}"
        if expected_qdrant != settings.qdrant_url:
            changed.append("qdrant")

    # DeepSeek
    deepseek = config.get("deepseek", {})
    if deepseek.get("api_key") and deepseek["api_key"] != settings.deepseek_api_key:
        changed.append("deepseek")

    if changed:
        return ApplyResult(
            status="restart_required",
            message=f"以下服务配置已变更，请重启生效: {', '.join(changed)}",
            changed_services=changed,
        )
    return ApplyResult(status="applied", message="配置已应用，无需重启。")


# ── Test helpers ──

async def _test_mysql(cfg: dict) -> TestResult:
    """测试 MySQL TCP 连接。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 13306))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.close()
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="mysql", success=True,
                          message=f"TCP 连接成功 ({host}:{port})",
                          latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="mysql", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_qdrant(cfg: dict) -> TestResult:
    """测试 Qdrant — 用 collections 列表检查（Qdrant 无 /health 端点）。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 16333))
    url = f"http://{host}:{port}/collections"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            elapsed = (time.time() - t0) * 1000
            if r.status_code == 200:
                return TestResult(service="qdrant", success=True,
                                  message=f"Qdrant 可访问 ({host}:{port})",
                                  latency_ms=round(elapsed, 1))
            else:
                return TestResult(service="qdrant", success=False,
                                  message=f"返回状态码 {r.status_code}",
                                  latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="qdrant", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_neo4j(cfg: dict) -> TestResult:
    """测试 Neo4j Bolt 连接。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("bolt_port", 17687))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.close()
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="neo4j", success=True,
                          message=f"TCP 连接成功 ({host}:{port})",
                          latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="neo4j", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_llama(cfg: dict) -> TestResult:
    """测试 llama-server 健康检查。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 18080))
    url = f"http://{host}:{port}/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            elapsed = (time.time() - t0) * 1000
            if r.status_code == 200:
                return TestResult(service="llama", success=True,
                                  message=f"llama-server 健康检查通过 ({host}:{port})",
                                  latency_ms=round(elapsed, 1))
            else:
                return TestResult(service="llama", success=False,
                                  message=f"返回状态码 {r.status_code}",
                                  latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="llama", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_embedding(cfg: dict) -> TestResult:
    """测试 embedding 服务健康检查。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "127.0.0.1")
    port = int(cfg.get("port", 18082))
    path = cfg.get("api_path", "/v1/embeddings")
    url = f"http://{host}:{port}{path}"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # 发一个空 embedding 请求来测试
            r = await client.post(url, json={"input": "test", "model": "default"})
            elapsed = (time.time() - t0) * 1000
            if r.status_code in (200, 404, 422):
                return TestResult(service="embedding", success=True,
                                  message=f"Embedding 服务可访问 ({host}:{port})",
                                  latency_ms=round(elapsed, 1))
            else:
                return TestResult(service="embedding", success=False,
                                  message=f"返回状态码 {r.status_code}",
                                  latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="embedding", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_ssh(cfg: dict) -> TestResult:
    """测试 SSH TCP 连接（不实际认证，只测端口通）。"""
    import time
    t0 = time.time()
    host = cfg.get("host", "")
    port = int(cfg.get("port", 22))
    if not host:
        return TestResult(service="ssh", success=False, message="SSH 主机地址为空")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.close()
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="ssh", success=True,
                          message=f"SSH 端口可访问 ({host}:{port})",
                          latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="ssh", success=False,
                          message=f"连接失败: {e}", latency_ms=round(elapsed, 1))


async def _test_deepseek(cfg: dict) -> TestResult:
    """测试 DeepSeek API — 发一个简单请求验证 API Key 有效性。"""
    import time
    t0 = time.time()
    api_key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "https://api.deepseek.com")
    model = cfg.get("model", "deepseek-v4-flash")

    if not api_key:
        return TestResult(service="deepseek", success=False, message="API Key 为空")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload, headers=headers)
            elapsed = (time.time() - t0) * 1000
            if r.status_code == 200:
                return TestResult(service="deepseek", success=True,
                                  message=f"DeepSeek API 可用 ({model})",
                                  latency_ms=round(elapsed, 1))
            elif r.status_code == 401:
                return TestResult(service="deepseek", success=False,
                                  message="API Key 无效 (401)",
                                  latency_ms=round(elapsed, 1))
            elif r.status_code == 429:
                return TestResult(service="deepseek", success=False,
                                  message="请求频率超限 (429)",
                                  latency_ms=round(elapsed, 1))
            else:
                data = r.text[:200]
                return TestResult(service="deepseek", success=False,
                                  message=f"返回 {r.status_code}: {data}",
                                  latency_ms=round(elapsed, 1))
    except httpx.ConnectError:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="deepseek", success=False,
                          message=f"无法连接 {base_url}",
                          latency_ms=round(elapsed, 1))
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        return TestResult(service="deepseek", success=False,
                          message=str(e), latency_ms=round(elapsed, 1))
