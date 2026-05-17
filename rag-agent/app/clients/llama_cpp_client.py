"""
NovelBridge — llama.cpp OpenAI-compatible client.

Calls llama-server at LLAMA_HOST:LLAMA_PORT.
Supports chat completions with grammar/response_format.
"""

import os
import time
import json
from typing import Optional

import httpx

LLAMA_HOST = os.getenv("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = int(os.getenv("LLAMA_PORT", "18080"))
LLAMA_BASE = f"http://{LLAMA_HOST}:{LLAMA_PORT}"
LLAMA_MODEL = os.getenv("NB_MODEL_NAME", "Qwen3.6-35B-A3B")

# Default generation parameters
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 512


class LlamaCppClient:
    """Synchronous client for llama.cpp llama-server."""

    def __init__(self, base_url: str = LLAMA_BASE, timeout: float = 600.0):
        self.base_url = base_url
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                timeout,        # overall timeout
                connect=30.0,   # connect timeout
                read=timeout,   # read timeout (model generation)
                write=30.0,     # write timeout
                pool=30.0,      # pool timeout
            )
        )

    def health(self) -> bool:
        """Check if llama-server is reachable via /v1/models."""
        try:
            resp = self._client.get(f"{self.base_url}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    def chat_completion(
        self,
        messages: list,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        grammar: Optional[str] = None,
        response_format: Optional[dict] = None,
        stop: Optional[list] = None,
    ) -> dict:
        """
        Call /v1/chat/completions.

        Args:
            messages: OpenAI-style messages list.
            temperature: Sampling temperature.
            max_tokens: Max output tokens.
            grammar: GBNF grammar string (optional).
            response_format: e.g. {"type": "json_object", "schema": {...}} (optional).
            stop: Stop sequences.

        Returns:
            Full API response dict.
        """
        payload = {
            "model": LLAMA_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if grammar:
            payload["grammar"] = grammar
        if response_format:
            payload["response_format"] = response_format
        if stop:
            payload["stop"] = stop

        start = time.time()
        try:
            resp = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            duration_ms = int((time.time() - start) * 1000)
            result = resp.json()
            result["_duration_ms"] = duration_ms
            result["_status_code"] = resp.status_code
            return result
        except httpx.RequestError as e:
            duration_ms = int((time.time() - start) * 1000)
            return {
                "error": str(e),
                "_duration_ms": duration_ms,
                "_status_code": 0,
            }

    def extract_text(self, response: dict) -> str:
        """Extract text content from chat completion response."""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return response.get("error", "NO_CONTENT")

    def close(self):
        self._client.close()

    def __del__(self):
        self.close()
