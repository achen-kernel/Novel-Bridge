"""
ChapterFact API 路由。
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.mysql_client import MysqlClient
from app.pipeline.fact_pipeline_runner import FactPipelineRunner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["facts"])

db_client: Optional[MysqlClient] = None


def init_router(db: MysqlClient):
    global db_client
    db_client = db


class ExtractRequest(BaseModel):
    use_model: bool = False


class ExtractResponse(BaseModel):
    status: str
    book_id: int
    run_id: int = 0
    chapters_processed: int = 0
    success_count: int = 0
    error: str = ""


@router.post("/books/{book_id}/extract", response_model=ExtractResponse)
async def extract_book(book_id: int, req: ExtractRequest):
    """触发一整本书的 ChapterFact 提取"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    runner = FactPipelineRunner(db_client, use_model=req.use_model)
    result = await runner.process_book(book_id)

    return ExtractResponse(
        status=result.get('status', 'error'),
        book_id=book_id,
        run_id=result.get('run_id', 0),
        chapters_processed=result.get('chapters_processed', 0),
        success_count=result.get('success_count', 0),
        error=result.get('error', '')
    )


class GovernRequest(BaseModel):
    pass


class GovernResponse(BaseModel):
    status: str
    book_id: int
    mentions: int = 0
    profiles: int = 0
    decisions: int = 0
    run_id: int = 0
    error: str = ""


@router.post("/books/{book_id}/govern", response_model=GovernResponse)
async def govern_book(book_id: int, req: Optional[GovernRequest] = None):
    """触发一本书的实体治理"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    from app.pipeline.entity_governance_runner import EntityGovernanceRunner
    runner = EntityGovernanceRunner(db_client)
    # 治理是同步过程（规则判断，无网络调用）
    result = runner.process_book(book_id)

    if result.get('status') == 'error':
        return GovernResponse(status='error', book_id=book_id, error=result.get('error', ''))

    return GovernResponse(
        status='success',
        book_id=book_id,
        mentions=result.get('mentions', 0),
        profiles=result.get('profiles', 0),
        decisions=result.get('decisions', 0),
        run_id=result.get('run_id', 0),
    )


class ChapterEntityViewResponse(BaseModel):
    chapter_id: int
    entities: List[dict] = []


@router.get("/chapters/{chapter_id}/entity-view", response_model=ChapterEntityViewResponse)
async def get_chapter_entity_view_endpoint(chapter_id: int):
    """获取章节实体视图（只包含本 chapter 的实体）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    from app.stores.entity_mention_store import EntityMentionStore
    from app.validators.alias_validator import get_chapter_entity_view

    conn = db_client.connect()
    store = EntityMentionStore(conn)
    mentions = store.find_by_chapter(chapter_id)
    view = get_chapter_entity_view(mentions)

    return ChapterEntityViewResponse(chapter_id=chapter_id, entities=view)


class NarrativeBuildResponse(BaseModel):
    status: str
    book_id: int
    relation_mentions: int = 0
    event_mentions: int = 0
    relation_facts: int = 0
    event_facts: int = 0
    run_id: int = 0
    error: str = ""


@router.post("/books/{book_id}/narrative", response_model=NarrativeBuildResponse)
async def build_narrative(book_id: int):
    """构建一本书的叙事元素（关系+事件）"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    from app.pipeline.narrative_builder import NarrativeBuilder
    runner = NarrativeBuilder(db_client)
    result = runner.build_from_book(book_id)

    if result.get('status') == 'error':
        return NarrativeBuildResponse(status='error', book_id=book_id, error=result.get('error', ''))

    return NarrativeBuildResponse(
        status='success', book_id=book_id,
        relation_mentions=result.get('relation_mentions', 0),
        event_mentions=result.get('event_mentions', 0),
        relation_facts=result.get('relation_facts', 0),
        event_facts=result.get('event_facts', 0),
        run_id=result.get('run_id', 0),
    )


class PlotStageResponse(BaseModel):
    status: str
    book_id: int
    stages: int = 0
    total_chapters: int = 0
    run_id: int = 0
    error: str = ""


@router.post("/books/{book_id}/plot-stages/detect", response_model=PlotStageResponse)
async def detect_plot_stages(book_id: int):
    """检测一本书的情节阶段"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    from app.pipeline.plot_stage_detector import PlotStageDetector
    detector = PlotStageDetector(db_client)
    result = detector.detect(book_id)

    if result.get('status') == 'error':
        return PlotStageResponse(status='error', book_id=book_id, error=result.get('error', ''))

    return PlotStageResponse(
        status='success', book_id=book_id,
        stages=result.get('stages', 0),
        total_chapters=result.get('total_chapters', 0),
        run_id=result.get('run_id', 0),
    )


class GraphProjectResponse(BaseModel):
    status: str
    book_id: int
    entities: int = 0
    relations: int = 0
    events: int = 0
    plot_stages: int = 0
    error: str = ""


@router.post("/books/{book_id}/graph/project", response_model=GraphProjectResponse)
async def project_graph(book_id: int):
    """将一本书的叙事数据投影到 Neo4j"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    from app.pipeline.graph_projector import GraphProjector
    projector = GraphProjector(conn)

    try:
        result = projector.project_book(book_id, clear_first=True)
        return GraphProjectResponse(
            status='success', book_id=book_id,
            entities=result.get('entities', 0),
            relations=result.get('relations', 0),
            events=result.get('events', 0),
            plot_stages=result.get('plot_stages', 0),
        )
    except Exception as e:
        logger.error(f"Graph projection failed: {e}")
        return GraphProjectResponse(status='error', book_id=book_id, error=str(e))


class IndexRequest(BaseModel):
    reindex: bool = False


class IndexResponse(BaseModel):
    status: str
    book_id: int
    chunks_indexed: int = 0
    facts_indexed: int = 0
    failed: int = 0
    error: str = ""


@router.post("/books/{book_id}/index", response_model=IndexResponse)
async def index_book(book_id: int, req: Optional[IndexRequest] = None):
    """将一本书的 chunks + ChapterFacts 索引到 Qdrant"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    from app.pipeline.index_runner import IndexRunner
    runner = IndexRunner(db_client)
    try:
        result = await runner.index_book(book_id, reindex=(req.reindex if req else False))
        return IndexResponse(
            status='success', book_id=book_id,
            chunks_indexed=result.get('chunks_indexed', 0),
            facts_indexed=result.get('facts_indexed', 0),
            failed=result.get('failed', 0),
        )
    except Exception as e:
        logger.error(f"Index failed: {e}")
        return IndexResponse(status='error', book_id=book_id, error=str(e))


class PriorHintRequest(BaseModel):
    pass


class PriorHintResponse(BaseModel):
    status: str
    book_id: int
    book_title: str = ""
    prior_hint: dict = {}
    error: str = ""


@router.post("/books/{book_id}/prior-hint", response_model=PriorHintResponse)
async def get_book_prior_hint(book_id: int, req: PriorHintRequest = None):
    """调用 DeepSeek 生成小说梗概和先验知识"""
    if db_client is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    conn = db_client.connect()
    try:
        # 读取书名和作者
        with conn.cursor() as cursor:
            cursor.execute("SELECT title, author, language FROM novel_book WHERE id = %s", (book_id,))
            book = cursor.fetchone()

        if not book:
            return PriorHintResponse(status='error', book_id=book_id, error='Book not found')

        book_title = book['title']
        author = book.get('author', '') or ''
        language = book.get('language', 'zh')

        # 读取提示词模板
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'book_prior_hint.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 填充模板（用 replace 避免与 JSON 花括号冲突）
        prompt = prompt_template.replace('{book_title}', book_title) \
            .replace('{author}', author) \
            .replace('{language}', language)

        # 调 DeepSeek
        from app.clients.deepseek_client import deepseek_client
        import json as json_lib
        result = await deepseek_client.chat_json([
            {"role": "user", "content": prompt}
        ], temperature=0.5, max_tokens=65536)

        prior_hint_dict = result if isinstance(result, dict) else {"raw": result}

        # 存入数据库供后续阶段使用
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE novel_book SET prior_hint_json = %s WHERE id = %s",
                (json_lib.dumps(prior_hint_dict, ensure_ascii=False), book_id)
            )
        conn.commit()
        logger.info(f"Prior hint saved to novel_book {book_id}")

        return PriorHintResponse(
            status='success',
            book_id=book_id,
            book_title=book_title,
            prior_hint=prior_hint_dict
        )
    except Exception as e:
        logger.error(f"Prior hint failed for book {book_id}: {e}")
        return PriorHintResponse(status='error', book_id=book_id, error=str(e))
