"""
索引运行器。
将一本书的 chunks + ChapterFacts 向量化并存入 Qdrant。

!!! 整个 index 流程通过 asyncio.to_thread 扔到线程池执行，
避免 embedding 推理 + Qdrant 写入阻塞 uvicorn 事件循环。!!!
"""
import asyncio
import logging
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.clients.qdrant_client import qdrant_client
from app.stores.vector_index_store import VectorIndexStore

logger = logging.getLogger(__name__)


class IndexRunner:
    def __init__(self, db: MysqlClient):
        self.db = db

    async def index_book(self, book_id: int, reindex: bool = False) -> dict:
        """索引一本书到 Qdrant"""
        conn = self.db.connect()

        def _run():
            store = VectorIndexStore(conn)

            # 确保集合存在
            qdrant_client.ensure_collections()

            # 如果需要重建索引，先删除旧的
            if reindex:
                store.delete_book_vectors(book_id)

            # 索引 chunks
            chunks_result = store.index_book_chunks_sync(book_id)

            # 索引 ChapterFacts
            facts_result = store.index_book_facts_sync(book_id)

            logger.info(f"Indexed book {book_id}: {chunks_result['indexed']} chunks, {facts_result['indexed']} facts")

            return {
                "status": "success",
                "book_id": book_id,
                "chunks_indexed": chunks_result['indexed'],
                "facts_indexed": facts_result['indexed'],
                "failed": chunks_result['failed'] + facts_result['failed']
            }

        return await asyncio.to_thread(_run)
