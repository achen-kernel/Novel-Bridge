"""
本地 llama-server 客户端。
llama-server 提供 OpenAI-compatible API。

!!! 连接复用：使用 lazy singleton httpx.AsyncClient，避免每次调用创建新连接。 !!!
"""
import json
import logging
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LlamaCppClient:
    """本地 llama-server 调用客户端 (OpenAI-compatible API)"""

    def __init__(self):
        self.base_url = settings.llama_base_url or "http://127.0.0.1:18080"
        self._http_client = None

    def _get_client(self) -> httpx.AsyncClient:
        """延迟创建 / 复用 httpx 连接"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=300.0)
        return self._http_client

    async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 4096, grammar: str = None) -> str:
        """普通对话"""
        payload = {
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if grammar:
            payload["grammar"] = grammar

        try:
            client = self._get_client()
            resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"llama-server call failed: {e}")
            raise

    async def chat_json(self, messages: list, temperature: float = 0.3, max_tokens: int = 4096, grammar: str = None) -> dict:
        """返回 JSON 格式的结构化输出"""
        content = await self.chat(messages, temperature, max_tokens, grammar=grammar)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                return json.loads(match.group(1))
            logger.error(f"Failed to parse JSON from llama response: {content[:200]}")
            return {"error": "parse_failed", "raw": content[:500]}

    async def health_check(self) -> dict:
        try:
            client = self._get_client()
            resp = await client.get(f"{self.base_url}/v1/models")
            resp.raise_for_status()
            data = resp.json()
            return {"status": "ok", "detail": f"llama-server reachable"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:100]}


# 单例
llama_client = LlamaCppClient()
