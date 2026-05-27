"""
ChapterFact 提取管线编排器。
对整个 book 的所有章节执行提取，生成 ChapterFact。
"""
import json
import logging
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.pipeline.chapter_fact_builder import build_chapter_fact
from app.pipeline.extraction_runner import extract_chunk
from app.stores.chapter_fact_store import ChapterFactStore
from app.stores.chapter_store import ChapterStore
from app.stores.chunk_store import ChunkStore
from app.stores.model_run_store import ModelRunStore
from app.validators.evidence_validator import validate_chapter_fact

logger = logging.getLogger(__name__)


class FactPipelineRunner:
    """ChapterFact 提取管线"""

    STEP_EXTRACT = "EXTRACT_MENTIONS"
    STEP_BUILD_FACT = "BUILD_CHAPTER_FACT"
    STEP_VALIDATE = "VALIDATE_EVIDENCE"

    def __init__(self, db: MysqlClient, use_model: bool = False, provider: str = "local"):
        self.db = db
        self.use_model = use_model
        self.provider = provider

    async def process_book(self, book_id: int, run_id: Optional[int] = None) -> dict:
        """处理一本书的所有章节"""
        conn = self.db.connect()
        run_store = ModelRunStore(conn)
        chapter_store = ChapterStore(conn)
        chapter_fact_store = ChapterFactStore(conn)

        # 读取 prior_hint（DeepSeek 梗概），用于辅助提取
        prior_hint = None
        with conn.cursor() as cursor:
            cursor.execute("SELECT prior_hint_json FROM novel_book WHERE id = %s", (book_id,))
            row = cursor.fetchone()
            if row and row.get('prior_hint_json'):
                try:
                    prior_hint = json.loads(row['prior_hint_json']) if isinstance(row['prior_hint_json'], str) else row['prior_hint_json']
                except json.JSONDecodeError:
                    logger.warning(f"Invalid prior_hint_json for book {book_id}")

        # 如果没传入 run_id，自行创建
        if run_id is None:
            run_id = run_store.create_run('CHAPTER_FACT_BUILD', book_id, {'book_id': book_id, 'mode': 'model' if self.use_model else 'rule'})

        try:
            # 1. 读取所有章节
            chapters = chapter_store.get_chapters_by_book(book_id)
            logger.info(f"Building ChapterFacts for book {book_id}: {len(chapters)} chapters")

            results = []
            for ch in chapters:
                fact = await self._process_chapter(
                    conn, book_id, ch, run_id, run_store,
                    chapter_store, chapter_fact_store,
                    prior_hint=prior_hint
                )
                results.append(fact)

            # 更新 run 状态
            success_count = sum(1 for r in results if r.get('status') == 'success')
            run_store.update_run_status(run_id, 'SUCCESS', {
                'book_id': book_id,
                'total_chapters': len(chapters),
                'success_count': success_count,
                'failed_count': len(chapters) - success_count
            })

            return {
                'status': 'success',
                'book_id': book_id,
                'chapters_processed': len(results),
                'success_count': success_count,
                'run_id': run_id
            }

        except Exception as e:
            logger.error(f"Fact pipeline failed for book {book_id}: {e}")
            run_store.update_run_status(run_id, 'FAILED', error_type=type(e).__name__, error_message=str(e))
            return {'status': 'error', 'book_id': book_id, 'error': str(e)}

    async def _process_chapter(self, conn, book_id: int, chapter: dict,
                                run_id: int, run_store, chapter_store, chapter_fact_store,
                                prior_hint: dict = None) -> dict:
        """处理单个章节"""
        chapter_id = chapter['id']
        chapter_title = chapter.get('title', '')

        try:
            # 1. 读取该章节的所有 chunks
            chunk_store = ChunkStore(conn)
            chunks = chunk_store.find_by_chapter(chapter_id)

            if not chunks:
                logger.warning(f"No chunks for chapter {chapter_id}")
                return {'chapter_id': chapter_id, 'status': 'skipped', 'reason': 'no chunks'}

            # 2. 创建 AgentStep
            step_id = run_store.create_step(run_id, self.STEP_EXTRACT, 1, {
                'book_id': book_id, 'chapter_id': chapter_id, 'chunk_count': len(chunks)
            })

            # 3. 对每个 chunk 做提取
            # 获取本书标题
            book_title = ''
            with conn.cursor() as cursor:
                cursor.execute("SELECT title FROM novel_book WHERE id = %s", (book_id,))
                bt = cursor.fetchone()
                if bt:
                    book_title = bt.get('title', '') or ''

            chunk_results = []
            for ck in chunks:
                result = await extract_chunk(
                    chunk_text=ck['content'],
                    chapter_title=chapter_title,
                    book_title=book_title,
                    chapter_id=chapter_id,
                    chunk_id=ck['id'],
                    use_model=self.use_model,
                    prior_hint=prior_hint,
                    provider=self.provider,
                )
                chunk_results.append(result)

            run_store.update_step_status(step_id, 'SUCCESS', {
                'chunks_processed': len(chunk_results)
            })

            # 4. 构建 ChapterFact
            step_id = run_store.create_step(run_id, self.STEP_BUILD_FACT, 2, {
                'book_id': book_id, 'chapter_id': chapter_id
            })

            # 从第一个 chunk 的模型输出中提取章节概要
            chapter_summary = ''
            for cr in chunk_results:
                summary = cr.get('chapter_summary', '') or ''
                if summary:
                    chapter_summary = summary
                    break

            # 获取章节原文用于证据校验
            chapter_text = chapter.get('raw_content', '')

            fact = build_chapter_fact(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                chunk_results=chunk_results
            )

            run_store.update_step_status(step_id, 'SUCCESS', {
                'entities': len(fact.get('characters', [])),
                'relations': len(fact.get('relations', [])),
                'events': len(fact.get('events', []))
            })

            # 5. 校验证据
            step_id = run_store.create_step(run_id, self.STEP_VALIDATE, 3, {
                'book_id': book_id, 'chapter_id': chapter_id
            })

            validated_fact = validate_chapter_fact(fact, chapter_text)

            # 确定 evidence_status
            has_unsupported = any(
                f['flag_type'] == 'WEAK_EVIDENCE' for f in validated_fact.get('quality_flags', [])
            )
            evidence_status = 'WEAK' if has_unsupported else 'PASSED'

            run_store.update_step_status(step_id, 'SUCCESS', {
                'evidence_status': evidence_status,
                'quality_flags': len(validated_fact.get('quality_flags', []))
            })

            # 6. 保存 ChapterFact
            fact_id = chapter_fact_store.insert_fact(
                book_id=book_id,
                chapter_id=chapter_id,
                fact_json=validated_fact,
                evidence_json={'evidence_records': validated_fact.get('evidence_records', [])},
                summary=validated_fact.get('chapter_summary', ''),
                parse_status='SUCCESS',
                evidence_status=evidence_status,
                review_status='PENDING'
            )

            return {
                'chapter_id': chapter_id,
                'status': 'success',
                'fact_id': fact_id,
                'entities': len(fact.get('characters', [])),
                'evidence_status': evidence_status
            }

        except Exception as e:
            logger.error(f"Chapter {chapter_id} processing failed: {e}")
            return {'chapter_id': chapter_id, 'status': 'error', 'error': str(e)}
