"""
Browse API — 只读 GET 端点，用于快速浏览已建库的数据。

保持 read-only，与 pipeline POST 端点分离。
将来 Java 重构时，这些端点直接替换为 Spring Boot Controller。
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.clients.mysql_client import MysqlClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["browse"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


# ── Response Models ──

class BookSummary(BaseModel):
    id: int
    title: str
    author: str = ""
    status: str = ""
    chapter_count: int = 0
    chunk_count: int = 0
    raw_length: int = 0
    language: str = "zh"


class ChapterItem(BaseModel):
    id: int
    chapter_number: int
    title: str = ""
    raw_length: int = 0
    status: str = ""
    chunk_count: int = 0


class EntityItem(BaseModel):
    id: int
    canonical_name: str
    entity_type: str = ""
    aliases: list = []
    mention_count: int = 0
    description: str = ""


class RelationItem(BaseModel):
    id: int
    source_name: str = ""
    target_name: str = ""
    relation_type: str = ""
    confidence: float = 0.0


class EventItem(BaseModel):
    id: int
    summary: str = ""
    subtype: str = ""
    participants: list = []


class BookDetail(BaseModel):
    id: int
    title: str
    author: str = ""
    status: str = ""
    chapter_count: int = 0
    chunk_count: int = 0
    raw_length: int = 0
    language: str = "zh"
    fact_count: int = 0
    entity_count: int = 0
    relation_count: int = 0
    event_count: int = 0
    alias_count: int = 0


# ── Endpoints ──

@router.get("/books", response_model=list[BookSummary])
async def list_books():
    """列出所有书及概要统计"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT b.id, b.title, COALESCE(b.author,'') as author,
                       b.status, b.chapter_count, b.chunk_count,
                       LENGTH(COALESCE(b.raw_text,'')) as raw_length,
                       COALESCE(b.language,'zh') as language
                FROM novel_book b
                ORDER BY b.id
            """)
            rows = c.fetchall()
            return [BookSummary(
                id=r['id'], title=r['title'], author=r['author'],
                status=r['status'], chapter_count=r['chapter_count'],
                chunk_count=r['chunk_count'], raw_length=r['raw_length'],
                language=r['language'],
            ) for r in rows]
    finally:
        conn.close()


@router.get("/books/{book_id}", response_model=BookDetail)
async def get_book(book_id: int):
    """获取单本书的详细信息（含各维度数据量）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT b.id, b.title, COALESCE(b.author,'') as author,
                       b.status, b.chapter_count, b.chunk_count,
                       LENGTH(COALESCE(b.raw_text,'')) as raw_length,
                       COALESCE(b.language,'zh') as language
                FROM novel_book b WHERE b.id=%s
            """, (book_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Book not found")

            # Counts
            c.execute("SELECT COUNT(*) FROM novel_chapter_fact WHERE book_id=%s", (book_id,))
            fact_count = c.fetchone()['COUNT(*)']
            c.execute("SELECT COUNT(*) FROM novel_entity_profile WHERE book_id=%s", (book_id,))
            entity_count = c.fetchone()['COUNT(*)']
            c.execute("SELECT COUNT(*) FROM novel_relation_fact WHERE book_id=%s", (book_id,))
            relation_count = c.fetchone()['COUNT(*)']
            c.execute("SELECT COUNT(*) FROM novel_event_fact WHERE book_id=%s", (book_id,))
            event_count = c.fetchone()['COUNT(*)']
            c.execute("SELECT COUNT(*) FROM novel_alias_decision WHERE book_id=%s", (book_id,))
            alias_count = c.fetchone()['COUNT(*)']

            return BookDetail(
                id=row['id'], title=row['title'], author=row['author'],
                status=row['status'], chapter_count=row['chapter_count'],
                chunk_count=row['chunk_count'], raw_length=row['raw_length'],
                language=row['language'],
                fact_count=fact_count, entity_count=entity_count,
                relation_count=relation_count, event_count=event_count,
                alias_count=alias_count,
            )
    finally:
        conn.close()


@router.get("/books/{book_id}/chapters", response_model=list[ChapterItem])
async def list_chapters(book_id: int):
    """列出某本书的所有章节"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT ch.id, ch.chapter_number, COALESCE(ch.title,'') as title,
                       LENGTH(COALESCE(ch.raw_content,'')) as raw_length,
                       COALESCE(ch.status,'') as status
                FROM novel_chapter ch
                WHERE ch.book_id=%s
                ORDER BY ch.chapter_number
            """, (book_id,))
            rows = c.fetchall()
            # Get chunk counts per chapter
            c.execute("""
                SELECT chapter_id, COUNT(*) as cnt
                FROM novel_chunk WHERE book_id=%s
                GROUP BY chapter_id
            """, (book_id,))
            chunk_map = {r['chapter_id']: r['cnt'] for r in c.fetchall()}

            return [ChapterItem(
                id=r['id'], chapter_number=r['chapter_number'],
                title=r['title'], raw_length=r['raw_length'],
                status=r['status'], chunk_count=chunk_map.get(r['id'], 0),
            ) for r in rows]
    finally:
        conn.close()


@router.get("/books/{book_id}/entities", response_model=list[EntityItem])
async def list_entities(book_id: int, min_mentions: int = 1,
                        limit: int = Query(default=50, le=500),
                        offset: int = Query(default=0, ge=0)):
    """列出某本书的所有实体画像（按提及数降序，支持分页）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        # Get total count for pagination
        total = 0
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM novel_entity_profile WHERE book_id=%s AND mention_count>=%s",
                      (book_id, min_mentions))
            total = c.fetchone()['cnt']

        with conn.cursor() as c:
            c.execute("""
                SELECT ep.id, ep.canonical_name,
                       COALESCE(ep.entity_type,'') as entity_type,
                       COALESCE(ep.aliases_json,'[]') as aliases_json,
                       ep.mention_count,
                       COALESCE(ep.description,'') as description
                FROM novel_entity_profile ep
                WHERE ep.book_id=%s AND ep.mention_count>=%s
                ORDER BY ep.mention_count DESC
                LIMIT %s OFFSET %s
            """, (book_id, min_mentions, limit, offset))
            rows = c.fetchall()
            result = []
            for r in rows:
                aliases = r['aliases_json']
                if isinstance(aliases, str):
                    try:
                        aliases = json.loads(aliases)
                    except json.JSONDecodeError:
                        aliases = []
                if not isinstance(aliases, list):
                    aliases = []
                result.append(EntityItem(
                    id=r['id'], canonical_name=r['canonical_name'],
                    entity_type=r['entity_type'], aliases=aliases,
                    mention_count=r['mention_count'],
                    description=r['description'],
                ))
            return result
    finally:
        conn.close()


@router.get("/books/{book_id}/relations", response_model=list[RelationItem])
async def list_relations(book_id: int):
    """列出某本书的所有关系事实（按置信度降序）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT rf.id,
                       COALESCE(rf.source_entity_name,'') as source_name,
                       COALESCE(rf.target_entity_name,'') as target_name,
                       COALESCE(rf.relation_type,'') as relation_type,
                       COALESCE(rf.confidence,0) as confidence,
                       COALESCE(rf.polarity,'') as polarity
                FROM novel_relation_fact rf
                WHERE rf.book_id=%s
                ORDER BY rf.confidence DESC, rf.id
                LIMIT 500
            """, (book_id,))
            rows = c.fetchall()
            return [RelationItem(
                id=r['id'], source_name=r['source_name'],
                target_name=r['target_name'], relation_type=r['relation_type'],
                confidence=r['confidence'],
            ) for r in rows]
    finally:
        conn.close()


@router.get("/books/{book_id}/events", response_model=list[EventItem])
async def list_events(book_id: int):
    """列出某本书的所有事件"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT ef.id,
                       COALESCE(ef.summary,'') as summary,
                       COALESCE(ef.event_type,'') as event_type,
                       COALESCE(ef.participants_json,'[]') as participants_json,
                       COALESCE(ef.location,'') as location
                FROM novel_event_fact ef
                WHERE ef.book_id=%s
                ORDER BY ef.id
                LIMIT 500
            """, (book_id,))
            rows = c.fetchall()
            result = []
            for r in rows:
                participants = r['participants_json']
                if isinstance(participants, str):
                    try:
                        participants = json.loads(participants)
                    except json.JSONDecodeError:
                        participants = []
                if not isinstance(participants, list):
                    participants = []
                result.append(EventItem(
                    id=r['id'], summary=r['summary'],
                    subtype=r['event_type'],
                    participants=participants,
                ))
            return result
    finally:
        conn.close()


class ChapterFactDetail(BaseModel):
    chapter_id: int
    chapter_number: int = 0
    chapter_title: str = ""
    summary: str = ""
    characters: list = []
    relations: list = []
    events: list = []
    quality_flags: list = []
    evidence_records: list = []
    evidence_status: str = ""
    review_status: str = ""


@router.get("/chapters/{chapter_id}/fact", response_model=ChapterFactDetail)
async def get_chapter_fact(chapter_id: int):
    """获取某个章节的 ChapterFact 详情（含所有提取的人物、关系、事件、证据）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT ch.id, ch.chapter_number, COALESCE(ch.title,'') as title,
                       cf.fact_json, cf.evidence_json, cf.evidence_status,
                       cf.review_status, cf.summary
                FROM novel_chapter ch
                LEFT JOIN novel_chapter_fact cf ON ch.id = cf.chapter_id
                WHERE ch.id = %s
            """, (chapter_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Chapter not found")

            fact_json = row.get('fact_json') or {}
            if isinstance(fact_json, str):
                try:
                    fact_json = json.loads(fact_json)
                except (json.JSONDecodeError, TypeError):
                    fact_json = {}

            evidence_json = row.get('evidence_json') or {}
            if isinstance(evidence_json, str):
                try:
                    evidence_json = json.loads(evidence_json)
                except (json.JSONDecodeError, TypeError):
                    evidence_json = {}

            evidence_records = []
            if isinstance(evidence_json, dict):
                evidence_records = evidence_json.get('evidence_records', [])
            elif isinstance(evidence_json, list):
                evidence_records = evidence_json

            return ChapterFactDetail(
                chapter_id=row['id'],
                chapter_number=row['chapter_number'],
                chapter_title=row['title'],
                summary=row.get('summary', '') or '',
                characters=fact_json.get('characters', []) if isinstance(fact_json, dict) else [],
                relations=fact_json.get('relations', []) if isinstance(fact_json, dict) else [],
                events=fact_json.get('events', []) if isinstance(fact_json, dict) else [],
                quality_flags=fact_json.get('quality_flags', []) if isinstance(fact_json, dict) else [],
                evidence_records=evidence_records,
                evidence_status=row.get('evidence_status', ''),
                review_status=row.get('review_status', ''),
            )
    finally:
        conn.close()


# ── Entity Detail ──

class EntityDetail(BaseModel):
    id: int
    book_id: int
    canonical_name: str
    entity_type: str = ""
    aliases: list = []
    mention_count: int = 0
    description: str = ""
    relations: list = []


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def get_entity_detail(entity_id: int):
    """获取实体详细资料（含关系列表）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT id, book_id, canonical_name, COALESCE(entity_type,'') as entity_type,
                       COALESCE(aliases_json,'[]') as aliases_json, mention_count,
                       COALESCE(description,'') as description
                FROM novel_entity_profile WHERE id=%s
            """, (entity_id,))
            row = c.fetchone()
            if not row:
                raise HTTPException(404, "Entity not found")

            aliases = row['aliases_json']
            if isinstance(aliases, str):
                try:
                    aliases = json.loads(aliases)
                except json.JSONDecodeError:
                    aliases = []
            if not isinstance(aliases, list):
                aliases = []

            # Get relations involving this entity
            name = row['canonical_name']
            c.execute("""
                SELECT source_entity_name, relation_type, target_entity_name, confidence
                FROM novel_relation_fact
                WHERE book_id=%s AND status='ACTIVE'
                  AND (source_entity_name=%s OR target_entity_name=%s)
                ORDER BY confidence DESC LIMIT 50
            """, (row['book_id'], name, name))
            relations = [
                {"source": r['source_entity_name'], "relation": r['relation_type'],
                 "target": r['target_entity_name'], "confidence": r['confidence']}
                for r in c.fetchall()
            ]

            return EntityDetail(
                id=row['id'], book_id=row['book_id'],
                canonical_name=row['canonical_name'],
                entity_type=row['entity_type'], aliases=aliases,
                mention_count=row['mention_count'],
                description=row['description'],
                relations=relations,
            )
    finally:
        conn.close()


# ── Search ──

class SearchResult(BaseModel):
    type: str = ""  # chunk | entity | event
    id: int = 0
    book_id: int = 0
    title: str = ""
    snippet: str = ""
    score: float = 0.0


@router.get("/search", response_model=dict)
async def search(q: str = Query(..., min_length=1),
                 book_id: Optional[int] = None,
                 limit: int = Query(default=20, le=100)):
    """全文搜索：搜索原文段落 + 实体 + 事件"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    conn = db_client.connect()
    try:
        results = []
        pattern = f"%{q}%"

        with conn.cursor() as c:
            # Search chunks
            sql = "SELECT ch.id, ch.book_id, LEFT(ch.content, 200) as snippet FROM novel_chunk ch WHERE ch.content LIKE %s"
            params = [pattern]
            if book_id:
                sql += " AND ch.book_id = %s"
                params.append(book_id)
            sql += " LIMIT %s"
            params.append(limit)
            c.execute(sql, params)
            for r in c.fetchall():
                results.append(SearchResult(
                    type="chunk", id=r['id'], book_id=r['book_id'],
                    title=f"Chunk #{r['id']}",
                    snippet=r.get('snippet', '')[:200],
                ))

            # Search entities
            sql = """SELECT ep.id, ep.book_id, ep.canonical_name, ep.entity_type,
                            LEFT(COALESCE(ep.description,''), 200) as snippet
                     FROM novel_entity_profile ep
                     WHERE (ep.canonical_name LIKE %s OR ep.aliases_json LIKE %s)"""
            params = [pattern, pattern]
            if book_id:
                sql += " AND ep.book_id = %s"
                params.append(book_id)
            sql += " LIMIT %s"
            params.append(limit // 2)
            c.execute(sql, params)
            for r in c.fetchall():
                results.append(SearchResult(
                    type="entity", id=r['id'], book_id=r['book_id'],
                    title=r['canonical_name'],
                    snippet=r.get('snippet', '')[:200],
                ))

        return {"query": q, "total": len(results), "results": [r.dict() for r in results]}
    finally:
        conn.close()
