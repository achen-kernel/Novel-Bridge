"""
Qdrant 向量数据库客户端。
用于 chunk 和 ChapterFact 的索引与检索。
"""
import logging
from typing import List, Optional, Dict, Any

from qdrant_client import QdrantClient as Qdrant
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from app.config import settings

logger = logging.getLogger(__name__)

# 集合名称
COLLECTION_CHUNKS = "novel_chunks"
COLLECTION_FACTS = "novel_chapter_facts"


class QdrantClient:
    def __init__(self):
        self.client = Qdrant(url=settings.qdrant_url, timeout=30)
        self.vector_size = settings.embedding_dim
        self.distance = Distance.COSINE

    # ---- 集合管理 ----

    def ensure_collections(self):
        """确保需要的集合存在，不存在则创建"""
        for name in [COLLECTION_CHUNKS, COLLECTION_FACTS]:
            try:
                collections = self.client.get_collections().collections
                existing = {c.name for c in collections}
                if name not in existing:
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(size=self.vector_size, distance=self.distance)
                    )
                    logger.info(f"Created Qdrant collection: {name}")
            except Exception as e:
                logger.error(f"Failed to ensure collection {name}: {e}")

    def delete_collection(self, name: str):
        """删除集合（重建时用）"""
        try:
            self.client.delete_collection(name)
            logger.info(f"Deleted Qdrant collection: {name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {name}: {e}")

    # ---- 写入 ----

    def upsert_chunks(self, points: List[PointStruct]):
        """批量写入 chunk 向量"""
        if not points:
            return
        self.client.upsert(collection_name=COLLECTION_CHUNKS, points=points)
        logger.info(f"Upserted {len(points)} chunk vectors")

    def upsert_facts(self, points: List[PointStruct]):
        """批量写入 ChapterFact 向量"""
        if not points:
            return
        self.client.upsert(collection_name=COLLECTION_FACTS, points=points)
        logger.info(f"Upserted {len(points)} fact vectors")

    # ---- 检索 ----

    def search_chunks(self, vector: List[float], book_id: Optional[int] = None,
                      limit: int = 10) -> List[Dict[str, Any]]:
        """稠密检索 chunks (qdrant-client 1.x query_points API)"""
        filter_ = None
        if book_id is not None:
            filter_ = models.Filter(
                must=[models.FieldCondition(key="book_id", match=models.MatchValue(value=book_id))]
            )

        result = self.client.query_points(
            collection_name=COLLECTION_CHUNKS,
            query=vector,
            query_filter=filter_,
            limit=limit,
            with_payload=True,
        )
        return [self._point_to_dict(p) for p in result.points]

    def search_facts(self, vector: List[float], book_id: Optional[int] = None,
                     limit: int = 5) -> List[Dict[str, Any]]:
        """稠密检索 ChapterFacts (qdrant-client 1.x query_points API)"""
        filter_ = None
        if book_id is not None:
            filter_ = models.Filter(
                must=[models.FieldCondition(key="book_id", match=models.MatchValue(value=book_id))]
            )

        result = self.client.query_points(
            collection_name=COLLECTION_FACTS,
            query=vector,
            query_filter=filter_,
            limit=limit,
            with_payload=True,
        )
        return [self._point_to_dict(p) for p in result.points]

    @staticmethod
    def _point_to_dict(point) -> Dict[str, Any]:
        """qdrant-client 1.x query_points 返回点转换为 dict"""
        return {
            "id": point.id,
            "score": point.score,
            "payload": point.payload or {},
        }

    async def health_check(self) -> dict:
        try:
            info = self.client.get_collections()
            return {"status": "ok", "detail": f"Qdrant reachable, {len(info.collections)} collections"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:100]}


# 单例
qdrant_client = QdrantClient()
