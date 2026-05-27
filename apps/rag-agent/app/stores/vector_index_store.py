"""
向量索引存储。
从 MySQL 读取 chunks/ChapterFacts → 生成 embedding → 写入 Qdrant。

超长 chunk 处理：如果 chunk 内容超过 embedding 模型最大字符数，
会在 ~50% 位置智能截断（优先自然边界），拆分后每个 segment 单独
生成 embedding 并写入 Qdrant，通过 parent_chunk_id + split_index
追踪亲缘关系。
"""
import logging
from typing import List, Optional

import pymysql
from qdrant_client.http.models import PointStruct

from app.clients.embedding_client import embedding_client
from app.clients.qdrant_client import qdrant_client, COLLECTION_CHUNKS, COLLECTION_FACTS
from app.utils.text_splitter import smart_split_text

logger = logging.getLogger(__name__)

# 为拆分后的 segment 生成唯一 Qdrant point ID
# 使用 chunk_id * 10000 + split_index，确保不冲突
_ID_MULTIPLIER = 10000


class VectorIndexStore:
    """向量索引操作"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    async def index_book_chunks(self, book_id: int) -> dict:
        """将一本书的所有 chunks 索引到 Qdrant（小批次 embedding）"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, chapter_id, content, char_count, content_hash FROM novel_chunk WHERE book_id = %s ORDER BY id",
                (book_id,)
            )
            chunks = cursor.fetchall()

        if not chunks:
            return {"indexed": 0, "failed": 0, "total": 0}

        # 小批次生成 embedding（每次 5 条，避免 OOM）
        BATCH_SIZE = 2  # Small batch to avoid GPU OOM
        points = []
        failed = 0

        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            texts = [ck['content'] for ck in batch]
            vectors = await embedding_client.embed_batch(texts)

            for i, ck in enumerate(batch):
                vec = vectors[i]
                if vec is None:
                    failed += 1
                    continue

                points.append(PointStruct(
                    id=ck['id'],
                    vector=vec,
                    payload={
                        "book_id": book_id,
                        "chapter_id": ck['chapter_id'],
                        "chunk_id": ck['id'],
                        "content_preview": ck['content'][:200],
                        "char_count": ck['char_count'],
                    }
                ))

                # 每 100 条批量写入 Qdrant
                if len(points) >= 100:
                    qdrant_client.upsert_chunks(points)
                    points = []

        # 剩余
        if points:
            qdrant_client.upsert_chunks(points)

        return {
            "indexed": len(chunks) - failed,
            "failed": failed,
            "total": len(chunks)
        }

    async def index_book_facts(self, book_id: int) -> dict:
        """将一本书的所有 ChapterFacts 索引到 Qdrant（小批次 embedding）"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, chapter_id, summary, fact_json, review_status FROM novel_chapter_fact WHERE book_id = %s",
                (book_id,)
            )
            facts = cursor.fetchall()

        if not facts:
            return {"indexed": 0, "failed": 0, "total": 0}

        points = []
        failed = 0
        BATCH_SIZE = 2  # Small batch to avoid GPU OOM

        for start in range(0, len(facts), BATCH_SIZE):
            batch = facts[start:start + BATCH_SIZE]

            # 准备这一批的 embedding 文本
            texts = []
            valid_indices = []
            for i, f in enumerate(batch):
                text = f.get('summary', '') or ''
                if not text:
                    text = self._fact_embedding_text(f)
                if not text:
                    failed += 1
                    continue
                texts.append(text)
                valid_indices.append(i)

            if not texts:
                failed += len(batch) - len(valid_indices)
                continue

            vectors = await embedding_client.embed_batch(texts)

            for j, idx in enumerate(valid_indices):
                vec = vectors[j]
                if vec is None:
                    failed += 1
                    continue

                f = batch[idx]
                points.append(PointStruct(
                    id=f['id'],
                    vector=vec,
                    payload={
                        "book_id": book_id,
                        "chapter_id": f['chapter_id'],
                        "chapter_fact_id": f['id'],
                        "review_status": f['review_status'],
                    }
                ))

        if points:
            qdrant_client.upsert_facts(points)

        return {
            "indexed": len(facts) - failed,
            "failed": failed,
            "total": len(facts)
        }

    # ---- 同步版本（给 IndexRunner 线程池内用） ----

    def index_book_chunks_sync(self, book_id: int) -> dict:
        """
        同步索引所有 chunks 到 Qdrant。

        超长 chunk（> MAX_CHARS）自动在 ~50% 位置智能拆分，
        拆分后的 segments 通过 parent_chunk_id + split_index 追踪亲缘关系。
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, chapter_id, content, char_count, content_hash FROM novel_chunk WHERE book_id = %s ORDER BY id",
                (book_id,)
            )
            chunks = cursor.fetchall()

        if not chunks:
            return {"indexed": 0, "failed": 0, "total": 0}

        BATCH_SIZE = 2  # Small batch to avoid GPU OOM on large chunks
        failed = 0
        total_items = 0  # Total items to index (chunks + split segments)

        # --- Build flat items list ---
        # Each item is (text, chunk_id, chapter_id, char_count, parent_chunk_id, split_index, total_splits, split_strategy)
        items = []  # List[dict]
        for ck in chunks:
            content = ck['content']
            char_count = ck['char_count'] or len(content)
            chunk_id = ck['id']
            chapter_id = ck['chapter_id']

            if len(content) > embedding_client.MAX_CHARS:
                # Smart split at ~half, prefer natural boundaries
                segments = smart_split_text(
                    content,
                    max_chars=embedding_client.MAX_CHARS,
                    parent_chunk_id=chunk_id,
                )
                for seg in segments:
                    items.append({
                        "text": seg.text,
                        "chunk_id": chunk_id,
                        "chapter_id": chapter_id,
                        "char_count": len(seg.text),
                        "parent_chunk_id": seg.parent_chunk_id,
                        "split_index": seg.split_index,
                        "total_splits": seg.total_splits,
                        "split_strategy": seg.split_strategy,
                        "is_split": True,
                    })
                total_items += len(segments)
                logger.info(
                    f"Chunk {chunk_id} split into {len(segments)} segments "
                    f"(strategy={segments[0].split_strategy}, "
                    f"original={char_count} chars)"
                )
            else:
                items.append({
                    "text": content,
                    "chunk_id": chunk_id,
                    "chapter_id": chapter_id,
                    "char_count": char_count,
                    "parent_chunk_id": chunk_id,  # Self-referencing for non-split
                    "split_index": 0,
                    "total_splits": 1,
                    "split_strategy": "none",
                    "is_split": False,
                })
                total_items += 1

        # --- Batch embed all items ---
        points = []
        for start in range(0, len(items), BATCH_SIZE):
            batch = items[start:start + BATCH_SIZE]
            texts = [it["text"] for it in batch]
            vectors = embedding_client.embed_batch_sync(texts)

            for i, it in enumerate(batch):
                vec = vectors[i]
                if vec is None:
                    failed += 1
                    continue

                # Build unique Qdrant point ID
                if it["is_split"]:
                    point_id = it["chunk_id"] * _ID_MULTIPLIER + it["split_index"]
                else:
                    point_id = it["chunk_id"]

                preview = it["text"][:200] if it["is_split"] else it["text"][:200]

                points.append(PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "book_id": book_id,
                        "chapter_id": it["chapter_id"],
                        "chunk_id": it["chunk_id"],
                        "content_preview": preview,
                        "char_count": it["char_count"],
                        "parent_chunk_id": it["parent_chunk_id"],
                        "split_index": it["split_index"],
                        "total_splits": it["total_splits"],
                        "split_strategy": it["split_strategy"],
                        "is_split": it["is_split"],
                    }
                ))

                if len(points) >= 100:
                    qdrant_client.upsert_chunks(points)
                    points = []

        if points:
            qdrant_client.upsert_chunks(points)

        return {"indexed": total_items - failed, "failed": failed, "total": total_items}

    def index_book_facts_sync(self, book_id: int) -> dict:
        """同步版本 — 同 index_book_facts 但用 embed_batch_sync"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, chapter_id, summary, fact_json, review_status FROM novel_chapter_fact WHERE book_id = %s",
                (book_id,)
            )
            facts = cursor.fetchall()

        if not facts:
            return {"indexed": 0, "failed": 0, "total": 0}

        points = []
        failed = 0
        BATCH_SIZE = 2

        for start in range(0, len(facts), BATCH_SIZE):
            batch = facts[start:start + BATCH_SIZE]
            texts = []
            valid_indices = []
            for i, f in enumerate(batch):
                text = f.get('summary', '') or ''
                if not text:
                    text = self._fact_embedding_text(f)
                if not text:
                    failed += 1
                    continue
                texts.append(text)
                valid_indices.append(i)

            if not texts:
                failed += len(batch) - len(valid_indices)
                continue

            vectors = embedding_client.embed_batch_sync(texts)

            for j, idx in enumerate(valid_indices):
                vec = vectors[j]
                if vec is None:
                    failed += 1
                    continue
                f = batch[idx]
                points.append(PointStruct(
                    id=f['id'], vector=vec,
                    payload={
                        "book_id": book_id, "chapter_id": f['chapter_id'],
                        "chapter_fact_id": f['id'], "review_status": f['review_status'],
                    }
                ))

        if points:
            qdrant_client.upsert_facts(points)

        return {"indexed": len(facts) - failed, "failed": failed, "total": len(facts)}

    def _fact_embedding_text(self, fact: dict) -> str:
        raw = fact.get('fact_json') or {}
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}
        if not isinstance(raw, dict):
            return ""
        parts = []
        summary = raw.get('chapter_summary') or raw.get('summary')
        if summary:
            parts.append(str(summary))
        for evt in raw.get('events', [])[:5]:
            text = evt.get('summary') or evt.get('description') or evt.get('evidence_text')
            if text:
                parts.append(str(text))
        for ent in raw.get('characters', [])[:8]:
            name = ent.get('display_name') or ent.get('name')
            if name:
                parts.append(str(name))
        return " ".join(parts)[:1000]

    def delete_book_vectors(self, book_id: int):
        """删除一本书的所有向量（重建时用）"""
        from qdrant_client.http import models as qdrant_models

        for collection in [COLLECTION_CHUNKS, COLLECTION_FACTS]:
            try:
                qdrant_client.client.delete(
                    collection_name=collection,
                    points_selector=qdrant_models.FilterSelector(
                        filter=qdrant_models.Filter(
                            must=[qdrant_models.FieldCondition(
                                key="book_id", match=qdrant_models.MatchValue(value=book_id)
                            )]
                        )
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to delete vectors for book {book_id} in {collection}: {e}")
