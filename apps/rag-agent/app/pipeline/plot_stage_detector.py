"""
情节阶段检测器。
基于 EntityProfile 的出现章节范围和 ChapterFact 聚类检测故事阶段。
"""
import json
import logging
from typing import List, Dict, Optional

import pymysql

from app.clients.mysql_client import MysqlClient
from app.stores.model_run_store import ModelRunStore
from app.stores.plot_stage_store import PlotStageStore

logger = logging.getLogger(__name__)


class PlotStageDetector:
    """检测故事的情节阶段"""

    def __init__(self, db: MysqlClient):
        self.db = db

    def detect(self, book_id: int, run_id: Optional[int] = None) -> dict:
        """检测一本书的情节阶段"""
        conn = self.db.connect()
        run_store = ModelRunStore(conn)
        stage_store = PlotStageStore(conn)

        if run_id is None:
            run_id = run_store.create_run('PLOT_STAGE_DETECT', book_id, {'book_id': book_id})

        try:
            step_id = run_store.create_step(run_id, 'DETECT_STAGES', 1, {'book_id': book_id})

            # 1. 获取章节数
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM novel_chapter WHERE book_id = %s", (book_id,))
                row = cursor.fetchone()
                total_chapters = row['cnt'] if row else 0

            # 2. 获取所有 entity profiles，统计每个章节出现的实体数
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT first_chapter_id, last_chapter_id, canonical_name, mention_count
                       FROM novel_entity_profile
                       WHERE book_id = %s AND status = 'ACTIVE'
                       ORDER BY mention_count DESC LIMIT 50""",
                    (book_id,))
                profiles = cursor.fetchall()

            # 3. 优先使用 prior_hint 中的 story_stages（DeepSeek 分析）
            #    否则 fallback 到简单的三等分
            prior_stages = None
            with conn.cursor() as cursor:
                cursor.execute("SELECT prior_hint_json FROM novel_book WHERE id = %s", (book_id,))
                row = cursor.fetchone()
                if row and row.get('prior_hint_json'):
                    try:
                        ph = json.loads(row['prior_hint_json']) if isinstance(row['prior_hint_json'], str) else row['prior_hint_json']
                        prior_stages = ph.get('story_stages', None)
                    except Exception:
                        pass

            stages = []
            if prior_stages and isinstance(prior_stages, list) and len(prior_stages) > 0:
                # 使用 prior_hint 的阶段定义
                for i, ps in enumerate(prior_stages):
                    stages.append({
                        'stage_index': i + 1,
                        'stage_name': ps.get('stage', f'阶段{i+1}'),
                        'summary': ps.get('summary', ''),
                        'start_chapter': 1,      # 保留章节范围由实体 profile 实际计算
                        'end_chapter': total_chapters,
                    })
                logger.info(f"Using {len(stages)} story stages from prior_hint")
            elif total_chapters <= 3:
                stages.append({
                    'stage_index': 1,
                    'stage_name': '全文',
                    'summary': '全文统一阶段',
                    'start_chapter': 1,
                    'end_chapter': total_chapters,
                })
            else:
                # 按章节数大致三等分
                third = max(1, total_chapters // 3)
                stages = [
                    {
                        'stage_index': 1,
                        'stage_name': '开端',
                        'summary': '故事开场，引入主要人物与背景',
                        'start_chapter': 1,
                        'end_chapter': third,
                    },
                    {
                        'stage_index': 2,
                        'stage_name': '发展',
                        'summary': '情节推进，冲突升级',
                        'start_chapter': third + 1,
                        'end_chapter': third * 2,
                    },
                    {
                        'stage_index': 3,
                        'stage_name': '结局',
                        'summary': '高潮与收束',
                        'start_chapter': third * 2 + 1,
                        'end_chapter': total_chapters,
                    },
                ]

            # 4. 为每个阶段标注关键实体
            for stage in stages:
                key_entities = []
                for prof in profiles:
                    fc = prof.get('first_chapter_id') or 1
                    lc = prof.get('last_chapter_id') or total_chapters
                    # 如果实体出现在该阶段范围内
                    if fc <= stage['end_chapter'] and lc >= stage['start_chapter']:
                        key_entities.append(prof['canonical_name'])
                    if len(key_entities) >= 10:
                        break

                stage_store.insert(
                    book_id=book_id,
                    stage_index=stage['stage_index'],
                    stage_name=stage['stage_name'],
                    summary=stage['summary'],
                    start_chapter_id=stage['start_chapter'],
                    end_chapter_id=stage['end_chapter'],
                    key_entities=key_entities[:10],
                )

            run_store.update_step_status(step_id, 'SUCCESS', {'stages': len(stages)})
            run_store.update_run_status(run_id, 'SUCCESS', {
                'book_id': book_id,
                'stages': len(stages),
                'total_chapters': total_chapters,
            })

            return {
                'status': 'success', 'book_id': book_id,
                'stages': len(stages),
                'total_chapters': total_chapters,
                'run_id': run_id,
            }

        except Exception as e:
            logger.error(f"Plot stage detection failed: {e}")
            run_store.update_run_status(run_id, 'FAILED', error_type=type(e).__name__, error_message=str(e))
            return {'status': 'error', 'book_id': book_id, 'error': str(e)}
