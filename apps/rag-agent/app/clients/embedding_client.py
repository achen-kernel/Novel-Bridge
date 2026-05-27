"""
Qwen3-Embedding-0.6B embedding 客户端。
使用 sentence-transformers 加载本地模型，不依赖外部服务。

同步模型推理通过 asyncio.to_thread() 卸到线程池，
避免阻塞 uvicorn 事件循环。

超长文本处理：使用 app.utils.text_splitter 在 ~50% 位置智能截断，
优先自然边界（段落→句子→行→词），必要时递归截断，LLM 兜底。
截断后的多个 segment 会记录 parent_chunk_id + split_index 追踪亲缘关系。
"""
import asyncio
import logging
from typing import Any, List, Optional

import httpx
import numpy as np

from app.config import settings
from app.utils.text_splitter import DEFAULT_MAX_CHARS, smart_split_text, truncate_head

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Embedding 向量生成客户端（本地模型）"""

    # Qwen3-Embedding-0.6B supports ~48K tokens; we cap at 50K chars
    MAX_CHARS = DEFAULT_MAX_CHARS  # 50000

    def __init__(self):
        self.provider = (settings.embedding_provider or "local").lower()
        self.api_url = settings.embedding_api_url or ""
        self.base_url = settings.embedding_base_url or settings.llama_base_url
        self.model_name = settings.embedding_model
        self.model_path = settings.embedding_model_local_path
        self.dim = settings.embedding_dim
        self.timeout = settings.embedding_timeout
        self.health_timeout = settings.embedding_health_timeout
        self._model = None
        self._http_client = None
        self._last_error = ""

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client

    def _load_model(self):
        """延迟加载 embedding 模型"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model from {self.model_path} ...")
            self._model = SentenceTransformer(self.model_path, device=settings.embedding_device)
            logger.info(f"Embedding model loaded, dim={self.dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _truncate(self, text: str) -> str:
        """简单头部截断（单文本备用方案，max_chars=50000）"""
        return truncate_head(text, self.MAX_CHARS)

    def smart_split(self, text: str, parent_id: Optional[int] = None):
        """智能拆分超长文本（≈half + 自然边界 + LLM 兜底）"""
        return smart_split_text(text, max_chars=self.MAX_CHARS, parent_chunk_id=parent_id)

    async def embed(self, text: str) -> Optional[List[float]]:
        """生成单个文本的 embedding 向量（线程池）"""
        if self.provider == "llama":
            return await self._embed_llama(text)
        try:
            self._load_model()
            model = self._model
            text = self._truncate(text)
            vec = await asyncio.to_thread(
                lambda: model.encode(text, normalize_embeddings=True)
            )
            return vec.tolist()
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量生成 embedding（线程池）"""
        if self.provider == "llama":
            return await self._embed_batch_llama(texts)
        try:
            self._load_model()
            model = self._model
            texts = [self._truncate(t) for t in texts]
            vecs = await asyncio.to_thread(
                lambda: model.encode(texts, normalize_embeddings=True)
            )
            return [v.tolist() for v in vecs]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [None] * len(texts)

    def embed_sync(self, text: str) -> Optional[List[float]]:
        """同步版本 — 在已卸到线程池的上下文里直接调用"""
        if self.provider == "llama":
            logger.error("Embedding sync is unavailable for provider=llama; use async embed().")
            return None
        try:
            self._load_model()
            text = self._truncate(text)
            vec = self._model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        except Exception as e:
            logger.error(f"Embedding sync failed: {e}")
            return None

    def embed_batch_sync(self, texts: List[str]) -> List[Optional[List[float]]]:
        """同步批量版本"""
        if self.provider == "llama":
            logger.error("Embedding batch sync is unavailable for provider=llama; use async embed_batch().")
            return [None] * len(texts)
        try:
            self._load_model()
            texts = [self._truncate(t) for t in texts]
            vecs = self._model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vecs]
        except Exception as e:
            logger.error(f"Batch embedding sync failed: {e}")
            return [None] * len(texts)

    async def _embed_llama(self, text: str) -> Optional[List[float]]:
        """OpenAI-compatible llama-server /v1/embeddings call."""
        try:
            payload = {
                "model": self.model_name,
                "input": self._truncate(text),
            }
            data = await self._post_embedding(payload)
            embedding = (data.get("data") or [{}])[0].get("embedding")
            if isinstance(embedding, list):
                return embedding
            self._last_error = "response missing data[0].embedding"
            logger.error("Embedding response missing data[0].embedding")
            return None
        except Exception as e:
            self._last_error = self._format_error(e)
            logger.error(f"Embedding llama-server failed: {e}")
            return None

    async def _embed_batch_llama(self, texts: List[str]) -> List[Optional[List[float]]]:
        try:
            payload = {
                "model": self.model_name,
                "input": [self._truncate(t) for t in texts],
            }
            data = await self._post_embedding(payload)
            rows = data.get("data") or []
            embeddings: list[Optional[List[float]]] = [None] * len(texts)
            for i, row in enumerate(rows[:len(texts)]):
                emb = row.get("embedding") if isinstance(row, dict) else None
                if isinstance(emb, list):
                    index = row.get("index", i)
                    if isinstance(index, int) and 0 <= index < len(embeddings):
                        embeddings[index] = emb
            return embeddings
        except Exception as e:
            self._last_error = self._format_error(e)
            logger.error(f"Batch embedding llama-server failed: {e}")
            return [None] * len(texts)

    async def health_check(self) -> dict:
        try:
            if self.provider == "llama":
                vec = await self._embed_llama_health("ping")
                if vec and len(vec) == self.dim:
                    return {
                        "status": "ok",
                        "detail": f"llama embedding ready, dim={self.dim}, url={self._embedding_url()}",
                    }
                if self._last_error:
                    return {
                        "status": "error",
                        "detail": f"llama embedding unavailable at {self._embedding_url()}: {self._last_error[:160]}",
                    }
                return {"status": "error", "detail": f"Unexpected dim: {len(vec) if vec else 0}"}
            self._load_model()
            vec = await self.embed("ping")
            if vec and len(vec) == self.dim:
                return {"status": "ok", "detail": f"Embedding model ready, dim={self.dim}"}
            return {"status": "error", "detail": f"Unexpected dim: {len(vec) if vec else 0}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:100]}

    def _embedding_url(self) -> str:
        if self.api_url:
            return self.api_url
        return f"{self.base_url.rstrip('/')}/v1/embeddings"

    async def _embed_llama_health(self, text: str) -> Optional[List[float]]:
        # Try configured model name first, then fallback to common aliases
        for model_name in [self.model_name, "default", self.model_name.split("/")[-1]]:
            try:
                payload = {"model": model_name, "input": self._truncate(text)}
                data = await self._post_embedding(payload, timeout=self.health_timeout)
                embedding = (data.get("data") or [{}])[0].get("embedding")
                if isinstance(embedding, list):
                    return embedding
            except Exception:
                continue
        self._last_error = "response missing data[0].embedding"
        return None

    async def _post_embedding(self, payload: dict[str, Any], timeout: Optional[float] = None) -> dict:
        client = self._get_client()
        resp = await client.post(self._embedding_url(), json=payload, timeout=timeout or self.timeout)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = resp.text[:300].replace("\n", " ")
            raise RuntimeError(f"HTTP {resp.status_code} from embedding server: {body}") from exc
        try:
            return resp.json()
        except Exception as exc:
            body = resp.text[:300].replace("\n", " ")
            raise RuntimeError(f"invalid JSON from embedding server: {body}") from exc

    def _format_error(self, exc: Exception) -> str:
        message = str(exc) or repr(exc)
        return message[:500]


# 单例
embedding_client = EmbeddingClient()
