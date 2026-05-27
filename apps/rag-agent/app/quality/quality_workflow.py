"""
提取质量提升工作流编排器。
按序执行：实体名同步 → 关系去重 → 事件摘要填充（骨架）。
每个 stage 可单独运行，也支持全量串跑。
"""
import logging
from typing import Optional

from app.clients.mysql_client import MysqlClient
from app.quality.stages.entity_name_normalizer import EntityNameNormalizer
from app.quality.stages.relation_deduper import RelationDeduper
from app.quality.stages.event_summarizer import EventSummarizer

logger = logging.getLogger(__name__)


class QualityWorkflow:
    """质量提升工作流编排器"""

    def __init__(self, db: MysqlClient):
        self.db = db

    async def run_all(self, book_id: Optional[int] = None,
                      dry_run: bool = True,
                      use_deepseek: bool = True) -> dict:
        """
        全量串跑所有 stage。

        Args:
            book_id: 指定书号，None=全部
            dry_run: True=只报告不写入
            use_deepseek: 事件摘要用 DeepSeek 还是本地模型

        Returns:
            {status, stages: {stage_name: stage_result, ...}, summary: {...}}
        """
        conn = self.db.connect()
        results = {}

        # Stage 1: 实体名同步
        logger.info("=== Stage 1: Entity Name Normalizer ===")
        normalizer = EntityNameNormalizer(conn)
        r1 = normalizer.run(book_id=book_id, dry_run=dry_run)
        results['entity_name_normalizer'] = r1
        logger.info(f"  Result: {r1['message']}")

        # Stage 2: 关系去重
        logger.info("=== Stage 2: Relation Deduper ===")
        deduper = RelationDeduper(conn)
        r2 = deduper.run(book_id=book_id, dry_run=dry_run)
        results['relation_deduper'] = r2
        logger.info(f"  Result: {r2['message']}")

        # Stage 3: 事件摘要填充（骨架，当前无空 summary）
        logger.info("=== Stage 3: Event Summarizer ===")
        summarizer = EventSummarizer(conn)
        r3 = summarizer.run(book_id=book_id, dry_run=dry_run,
                            use_deepseek=use_deepseek)
        results['event_summarizer'] = r3
        logger.info(f"  Result: {r3['message']}")

        conn.close()

        # 汇总
        summary = {
            'stages_completed': len(results),
            'changes': {
                'entity_name_normalizer': results.get('entity_name_normalizer', {}).get('stats', {}).get('updated', 0),
                'relation_deduper': results.get('relation_deduper', {}).get('stats', {}).get('rows_actually_merged', 0),
                'event_summarizer': results.get('event_summarizer', {}).get('stats', {}).get('filled', 0),
            },
            'dry_run': dry_run,
        }

        return {
            'status': 'ok',
            'stages': results,
            'summary': summary,
        }

    def run_stage(self, stage_name: str, book_id: Optional[int] = None,
                  dry_run: bool = True) -> dict:
        """
        单独运行某个 stage。

        Args:
            stage_name: 'entity_name_normalizer' | 'relation_deduper' | 'event_summarizer'
        """
        conn = self.db.connect()
        try:
            if stage_name == 'entity_name_normalizer':
                runner = EntityNameNormalizer(conn)
                return runner.run(book_id=book_id, dry_run=dry_run)
            elif stage_name == 'relation_deduper':
                runner = RelationDeduper(conn)
                return runner.run(book_id=book_id, dry_run=dry_run)
            elif stage_name == 'event_summarizer':
                runner = EventSummarizer(conn)
                return runner.run(book_id=book_id, dry_run=dry_run)
            else:
                return {'status': 'error', 'message': f'Unknown stage: {stage_name}'}
        finally:
            conn.close()
