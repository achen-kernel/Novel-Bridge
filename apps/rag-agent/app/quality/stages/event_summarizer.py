"""
Stage 3: 事件摘要填充（骨架）。
为 novel_event_fact 中 summary 为空的记录生成摘要。
使用 LLM（DeepSeek API 或本地 9B），基于 event_type + participants_json 生成。

当前状态：所有事件已有 summary（0 条空），本 stage 暂不执行。
保持骨架供后续扩展。
"""
import json
import logging
from typing import List, Dict, Optional

import pymysql

from app.clients.deepseek_client import deepseek_client
from app.clients.llama_cpp_client import llama_client

logger = logging.getLogger(__name__)


class EventSummarizer:
    """事件摘要填充器"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def run(self, book_id: Optional[int] = None, dry_run: bool = True,
            use_deepseek: bool = True) -> Dict:
        """
        填充空 summary 的事件。

        Args:
            book_id: 指定书号，None=全部
            dry_run: True=只报告不改写
            use_deepseek: True=DeepSeek API, False=本地 9B

        Returns:
            {'status': 'ok', 'stats': {...}, 'changes': [...]}
        """
        # 检查空 summary 数量
        sql = """SELECT id, book_id, event_type, participants_json, location, importance
                 FROM novel_event_fact
                 WHERE (summary IS NULL OR summary = '')"""
        params = []
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)

        empty_events = []
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            empty_events = cursor.fetchall()

        stats = {
            'total_empty': len(empty_events),
        }

        if not empty_events:
            return {
                'status': 'ok',
                'stats': stats,
                'changes': [],
                'message': 'No events with empty summary found',
            }

        logger.info(f"Found {len(empty_events)} events with empty summary")

        if dry_run:
            return {
                'status': 'ok',
                'stats': stats,
                'change_preview': [{'id': e['id'], 'book_id': e['book_id'],
                                    'event_type': e['event_type']} for e in empty_events[:20]],
                'message': f"Found {len(empty_events)} empty summaries (dry-run)",
            }

        # 实际填充（需要 LLM 调用）
        changes = self._fill_summaries(empty_events, use_deepseek)
        stats['filled'] = len(changes)

        return {
            'status': 'ok',
            'stats': stats,
            'changes': changes,
            'message': f"Filled {len(changes)} event summaries",
        }

    async def _fill_summaries(self, events: List[Dict], use_deepseek: bool) -> List[Dict]:
        """
        （骨架）调 LLM 为每条事件生成摘要。
        事件 summary 全部非空，本方法暂无实际调用需求。
        保留骨架供后续复用。
        """
        # 骨架：返回提示信息
        logger.info(f"EventSummarizer._fill_summaries: skeleton called with {len(events)} events, "
                     f"use_deepseek={use_deepseek}. All events already have summaries, no action needed.")
        return []
