"""
DeepSeek API 客户端。
使用 httpx 直接调用 DeepSeek Chat API (兼容 OpenAI 格式)。
"""
import json
import logging
import time
from typing import Optional, AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeekClient:
    """DeepSeek API 调用客户端"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url or "https://api.deepseek.com"
        self.model = settings.deepseek_model or DEEPSEEK_MODEL
        ds_timeout = settings.deepseek_timeout
        self.http_client = httpx.AsyncClient(
            timeout=ds_timeout,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        )

    async def chat(self, messages: list, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """普通对话，返回文本"""
        if not self.api_key:
            logger.warning("DeepSeek API key not configured, returning mock")
            return json.dumps({"error": "DeepSeek API key not configured"})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            resp = await self.http_client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            raise

    async def chat_json(self, messages: list, temperature: float = 0.3, max_tokens: int = 4096) -> dict:
        """返回 JSON 格式的结构化输出"""
        # 在 system prompt 中要求 JSON 输出
        content = await self.chat(messages, temperature, max_tokens)
        # 尝试解析 JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试从 ```json ... ``` 中提取
            import re
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                return json.loads(match.group(1))
            logger.error(f"Failed to parse JSON from DeepSeek response: {content[:200]}")
            return {"error": "parse_failed", "raw": content[:500]}

    async def health_check(self) -> dict:
        if not self.api_key:
            return {"status": "unavailable", "detail": "DeepSeek API key not configured"}
        try:
            start = time.time()
            await self.chat([{"role": "user", "content": "ping"}], max_tokens=10)
            return {"status": "ok", "detail": f"DeepSeek API reachable ({int((time.time()-start)*1000)}ms)"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:100]}


# 单例
deepseek_client = DeepSeekClient()
