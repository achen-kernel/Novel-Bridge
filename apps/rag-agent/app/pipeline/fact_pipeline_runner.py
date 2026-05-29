"""
ChapterFact 提取管线编排器。

支持 checkpoint 续跑、失败检测、取消信号。
"""
import asyncio
import json
import logging
import time
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.pipeline.chapter_fact_builder import build_chapter_fact
from app.pipeline.extraction_runner import extract_chunk
from app.pipeline.pipeline_state import (
    CheckpointStatus, MAX_CONSECUTIVE_FAILURES, MAX_FAILURE_RATE, MAX_RETRIES,
    P3Checkpoint, PipelineStateStore, get_state_store,
)
from app.stores.chapter_fact_store import ChapterFactStore
from app.stores.chapter_store import ChapterStore
from app.stores.chunk_store import ChunkStore
from app.stores.model_run_store import ModelRunStore
from app.validators.evidence_validator import validate_chapter_fact

logger = logging.getLogger(__name__)


class PipelineAborted(Exception):
    """Raised when Stage 2 should abort due to too many failures."""
    pass


class FactPipelineRunner:
    """ChapterFact 提取管线"""

    STEP_EXTRACT = "EXTRACT_MENTIONS"
    STEP_BUILD_FACT = "BUILD_CHAPTER_FACT"
    STEP_VALIDATE = "VALIDATE_EVIDENCE"

    def __init__(self, db: MysqlClient, use_model: bool = False, provider: str = "local"):
        self.db = db
        self.use_model = use_model
        self.provider = provider

    async def process_book(self, book_id: int, run_id: Optional[int] = None,
                           cancel_event: Optional[asyncio.Event] = None) -> dict:
        """处理一本书的所有章节（全量运行，写 checkpoint）。

        Args:
            book_id: 书 ID
            run_id: 可选的 run_id（不传则自建）
            cancel_event: 取消信号，收到后优雅退出
        """
        return await self._run(book_id, run_id, cancel_event, resume_mode=False)

    async def resume_book(self, book_id: int, run_id: Optional[int] = None,
                          cancel_event: Optional[asyncio.Event] = None,
                          lookback: int = 2) -> dict:
        """续跑：从中断位置倒退 `lookback` 章开始重新抽取。

        倒退是为了确保中断处的最后几章数据完整。
        Stage 1 和 Stage 3 快，不需要 checkpoint。
        """
        return await self._run(book_id, run_id, cancel_event, resume_mode=True, lookback=lookback)

    async def _run(self, book_id: int, run_id: Optional[int], cancel_event: Optional[asyncio.Event],
                   resume_mode: bool, lookback: int = 2) -> dict:
        """内部运行逻辑"""
        conn = self.db.new_connection()
        run_store = ModelRunStore(conn)
        chapter_store = ChapterStore(conn)
        chapter_fact_store = ChapterFactStore(conn)
        state_store = PipelineStateStore(conn)

        # 确保 checkpoint 表存在
        state_store.ensure_tables()

        # 读取 prior_hint
        prior_hint = None
        with conn.cursor() as cursor:
            cursor.execute("SELECT prior_hint_json FROM novel_book WHERE id = %s", (book_id,))
            row = cursor.fetchone()
            if row and row.get('prior_hint_json'):
                try:
                    prior_hint = json.loads(row['prior_hint_json']) if isinstance(row['prior_hint_json'], str) else row['prior_hint_json']
                except json.JSONDecodeError:
                    logger.warning(f"Invalid prior_hint_json for book {book_id}")

        # run_id
        if run_id is None:
            run_id = run_store.create_run(
                'CHAPTER_FACT_BUILD', book_id,
                {'book_id': book_id, 'mode': 'model' if self.use_model else 'rule'}
            )

        try:
            chapters = chapter_store.get_chapters_by_book(book_id)
            logger.info(f"{'Resume' if resume_mode else 'Process'} book {book_id}: {len(chapters)} chapters")

            total = len(chapters)
            if total == 0:
                return {'status': 'success', 'book_id': book_id, 'chapters_processed': 0, 'success_count': 0}

            # 设置 state 为 RUNNING
            state_store.update_stage(book_id, 2, 'RUNNING', {
                'consecutive_failures': 0, 'total_failed': 0,
                'total_chapters': total, 'aborted': False,
            })

            # resume 模式下：倒退 lookback 章，确保中断处数据完整
            if resume_mode:
                resume_nums = state_store.get_resume_chapters(book_id, lookback=lookback)
                if not resume_nums:
                    # 没有 checkpoint 数据，回退到全量运行
                    chapters_to_process = chapters
                    logger.info(f"Resume: no checkpoint data, full run ({total} chapters)")
                else:
                    nums_set = set(resume_nums)
                    chapters_to_process = [ch for ch in chapters if ch.get('chapter_number', ch['id']) in nums_set]
                    logger.info(f"Resume: {len(chapters_to_process)} chapters (lookback={lookback}) out of {total}")
            else:
                chapters_to_process = chapters

            results = []
            consecutive_failures = 0
            total_failed = 0

            for ch in chapters_to_process:
                chapter_number = ch.get('chapter_number', ch['id'])

                # ── 取消检查 ──
                if cancel_event and cancel_event.is_set():
                    logger.info(f"Stage 2 cancelled for book {book_id}, stopping at chapter {chapter_number}")
                    state_store.update_stage(book_id, 2, 'CANCELLED', {
                        'consecutive_failures': consecutive_failures,
                        'total_failed': total_failed, 'total_chapters': total, 'aborted': False,
                    })
                    return {
                        'status': 'cancelled', 'book_id': book_id,
                        'chapters_processed': len(results), 'success_count': sum(1 for r in results if r.get('status') == 'success'),
                        'run_id': run_id,
                    }

                # ── checkpoint 跳过（resume 模式下已经过滤，但全量运行时也检查） ──
                if not resume_mode:
                    existing = state_store.get_checkpoint(book_id, chapter_number)
                    if existing and existing.status == CheckpointStatus.SUCCESS.value:
                        logger.info(f"  Chapter {chapter_number} already SUCCESS, skipping")
                        results.append({'chapter_id': ch['id'], 'status': 'skipped', 'reason': 'already done'})
                        continue

                # ── 重试上限检查 ──
                existing_cp = state_store.get_checkpoint(book_id, chapter_number)
                if existing_cp and existing_cp.status == CheckpointStatus.FAILED.value and existing_cp.retry_count >= MAX_RETRIES:
                    logger.warning(f"  Chapter {chapter_number} permanently failed ({existing_cp.retry_count} retries), skipping")
                    results.append({'chapter_id': ch['id'], 'status': 'skipped', 'reason': f'permanent failure after {MAX_RETRIES} retries'})
                    continue

                # ── 写开始 checkpoint ──
                state_store.upsert_checkpoint(P3Checkpoint(
                    book_id=book_id, chapter_number=chapter_number,
                    status=CheckpointStatus.PENDING.value,
                    started_at=time.time(),
                ))

                # MySQL keepalive
                try:
                    conn.ping(reconnect=True)
                except Exception:
                    logger.warning("MySQL reconnecting...")
                    conn = self.db.new_connection()
                    chapter_fact_store = ChapterFactStore(conn)
                    chapter_store = ChapterStore(conn)
                    run_store = ModelRunStore(conn)
                    state_store = PipelineStateStore(conn)

                # 处理该章
                fact = await self._process_chapter(
                    conn, book_id, ch, run_id, run_store,
                    chapter_store, chapter_fact_store,
                    prior_hint=prior_hint,
                )

                # 写完成 checkpoint
                if fact.get('status') == 'success':
                    consecutive_failures = 0
                    state_store.upsert_checkpoint(P3Checkpoint(
                        book_id=book_id, chapter_number=chapter_number,
                        status=CheckpointStatus.SUCCESS.value,
                        completed_at=time.time(),
                    ))
                else:
                    consecutive_failures += 1
                    total_failed += 1
                    retry_count = (existing_cp.retry_count + 1) if existing_cp else 1
                    state_store.upsert_checkpoint(P3Checkpoint(
                        book_id=book_id, chapter_number=chapter_number,
                        status=CheckpointStatus.FAILED.value,
                        retry_count=retry_count,
                        error=str(fact.get('error', 'unknown'))[:1000],
                        completed_at=time.time(),
                    ))

                results.append(fact)

                # ── 失败阈值检查 ──
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(f"Aborting book {book_id}: {consecutive_failures} consecutive failures")
                    state_store.update_stage2_detail(book_id, {
                        'consecutive_failures': consecutive_failures,
                        'total_failed': total_failed, 'total_chapters': total, 'aborted': True,
                        'reason': f'连续{consecutive_failures}章失败',
                    })
                    raise PipelineAborted(f"连续{consecutive_failures}章失败，已中止")

                failure_rate = total_failed / max(total, 1)
                if failure_rate > MAX_FAILURE_RATE:
                    logger.error(f"Aborting book {book_id}: failure rate {failure_rate:.0%} exceeds {MAX_FAILURE_RATE:.0%}")
                    state_store.update_stage2_detail(book_id, {
                        'consecutive_failures': consecutive_failures,
                        'total_failed': total_failed, 'total_chapters': total, 'aborted': True,
                        'reason': f'失败率{failure_rate:.0%}超过阈值',
                    })
                    raise PipelineAborted(f"失败率{failure_rate:.0%}超过{MAX_FAILURE_RATE:.0%}，已中止")

                # 每 10 章更新一次 state detail
                if len(results) % 10 == 0:
                    state_store.update_stage2_detail(book_id, {
                        'consecutive_failures': consecutive_failures,
                        'total_failed': total_failed, 'total_chapters': total, 'aborted': False,
                    })

            # ── 收尾 ──
            success_count = sum(1 for r in results if r.get('status') == 'success')
            total_success = success_count + sum(
                1 for r in results if r.get('status') == 'skipped'
            )

            run_store.update_run_status(run_id, 'SUCCESS', {
                'book_id': book_id, 'total_chapters': total,
                'success_count': success_count, 'failed_count': total - total_success,
            })

            # 判断 Stage 2 整体状态
            failed_chapters = state_store.get_failed_chapters(book_id)
            if failed_chapters:
                stage2_status = 'COMPLETED_WITH_ERRORS'
                logger.warning(f"Book {book_id} Stage 2 done with {len(failed_chapters)} permanently failed chapters")
            else:
                stage2_status = 'SUCCESS'

            state_store.update_stage(book_id, 2, stage2_status, {
                'consecutive_failures': consecutive_failures,
                'total_failed': total_failed, 'total_chapters': total, 'aborted': False,
            })

            return {
                'status': stage2_status,
                'book_id': book_id,
                'chapters_processed': len(results),
                'success_count': success_count,
                'run_id': run_id,
            }

        except PipelineAborted as pae:
            state_store.update_stage(book_id, 2, 'FAILED')
            run_store.update_run_status(run_id, 'FAILED', error_message=str(pae))
            return {'status': 'aborted', 'book_id': book_id, 'error': str(pae)}

        except Exception as e:
            logger.error(f"Fact pipeline failed for book {book_id}: {e}")
            try:
                run_store.update_run_status(run_id, 'FAILED', error_type=type(e).__name__, error_message=str(e))
            except Exception:
                pass
            state_store.update_stage(book_id, 2, 'FAILED')
            return {'status': 'error', 'book_id': book_id, 'error': str(e)}

        finally:
            try:
                conn.close()
            except Exception:
                pass

    async def _process_chapter(self, conn, book_id: int, chapter: dict,
                                run_id: int, run_store, chapter_store, chapter_fact_store,
                                prior_hint: dict = None) -> dict:
        """处理单个章节"""
        chapter_id = chapter['id']
        chapter_title = chapter.get('title', '')

        try:
            chunk_store = ChunkStore(conn)
            chunks = chunk_store.find_by_chapter(chapter_id)

            if not chunks:
                logger.warning(f"No chunks for chapter {chapter_id}")
                return {'chapter_id': chapter_id, 'status': 'skipped', 'reason': 'no chunks'}

            step_id = run_store.create_step(run_id, self.STEP_EXTRACT, 1, {
                'book_id': book_id, 'chapter_id': chapter_id, 'chunk_count': len(chunks),
            })

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
                'chunks_processed': len(chunk_results),
            })

            step_id = run_store.create_step(run_id, self.STEP_BUILD_FACT, 2, {
                'book_id': book_id, 'chapter_id': chapter_id,
            })

            chapter_summary = ''
            for cr in chunk_results:
                summary = cr.get('chapter_summary', '') or ''
                if summary:
                    chapter_summary = summary
                    break

            chapter_text = chapter.get('raw_content', '')

            fact = build_chapter_fact(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                chunk_results=chunk_results,
            )

            run_store.update_step_status(step_id, 'SUCCESS', {
                'entities': len(fact.get('characters', [])),
                'relations': len(fact.get('relations', [])),
                'events': len(fact.get('events', [])),
            })

            step_id = run_store.create_step(run_id, self.STEP_VALIDATE, 3, {
                'book_id': book_id, 'chapter_id': chapter_id,
            })

            validated_fact = validate_chapter_fact(fact, chapter_text)

            has_unsupported = any(
                f['flag_type'] == 'WEAK_EVIDENCE' for f in validated_fact.get('quality_flags', [])
            )
            evidence_status = 'WEAK' if has_unsupported else 'PASSED'

            run_store.update_step_status(step_id, 'SUCCESS', {
                'evidence_status': evidence_status,
                'quality_flags': len(validated_fact.get('quality_flags', [])),
            })

            fact_id = chapter_fact_store.insert_fact(
                book_id=book_id,
                chapter_id=chapter_id,
                fact_json=validated_fact,
                evidence_json={'evidence_records': validated_fact.get('evidence_records', [])},
                summary=validated_fact.get('chapter_summary', ''),
                parse_status='SUCCESS',
                evidence_status=evidence_status,
                review_status='PENDING',
            )

            return {
                'chapter_id': chapter_id,
                'status': 'success',
                'fact_id': fact_id,
                'entities': len(fact.get('characters', [])),
                'evidence_status': evidence_status,
            }

        except Exception as e:
            logger.error(f"Chapter {chapter_id} processing failed: {e}")
            return {'chapter_id': chapter_id, 'status': 'error', 'error': str(e)}
