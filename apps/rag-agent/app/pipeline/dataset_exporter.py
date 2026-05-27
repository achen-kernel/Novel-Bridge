"""
训练数据集导出器。
从已审核的 ChapterFacts 导出训练数据到 training/data/。
"""
import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from app.clients.mysql_client import MysqlClient
from app.config import settings

logger = logging.getLogger(__name__)

TRAINING_DATA_DIR = os.environ.get(
    'TRAINING_DATA_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'training', 'data')
)


class DatasetExporter:
    def __init__(self, db: MysqlClient):
        self.db = db

    def export_chapter_facts(self, book_id: int = None,
                              min_review_status: str = 'ACCEPTED',
                              output_dir: str = None) -> dict:
        """导出 ChapterFacts 为微调训练数据

        格式: JSONL, 每条 {instruction, input, output}
        """
        conn = self.db.connect()
        output_dir = output_dir or TRAINING_DATA_DIR
        os.makedirs(output_dir, exist_ok=True)

        with conn.cursor() as cursor:
            sql = """SELECT cf.id, cf.book_id, cf.chapter_id, cf.fact_json,
                            cf.evidence_json, cf.review_status, cf.summary,
                            b.title as book_title
                     FROM novel_chapter_fact cf
                     JOIN novel_book b ON b.id = cf.book_id
                     WHERE cf.review_status = %s"""
            params = [min_review_status]
            if book_id:
                sql += " AND cf.book_id = %s"
                params.append(book_id)
            sql += " ORDER BY cf.book_id, cf.chapter_id"
            cursor.execute(sql, params)
            facts = cursor.fetchall()

        if not facts:
            return {'status': 'error', 'message': f'No facts with review_status={min_review_status}'}

        # 生成训练样本
        samples = []
        for f in facts:
            fact_json = f.get('fact_json', {})
            if isinstance(fact_json, str):
                try:
                    fact_json = json.loads(fact_json)
                except:
                    fact_json = {}

            # instruction + input + output 格式
            sample = {
                'instruction': f"分析小说《{f['book_title']}》第{f['chapter_id']}章的内容，提取结构化事实。",
                'input': f"章节摘要: {f.get('summary', '')}",
                'output': json.dumps(fact_json, ensure_ascii=False, indent=2),
                'metadata': {
                    'book_id': f['book_id'],
                    'chapter_id': f['chapter_id'],
                    'fact_id': f['id'],
                    'review_status': f['review_status'],
                    'source': 'novel_chapter_fact',
                }
            }
            samples.append(sample)

        # 写入 JSONL（使用 book_id 避免多本书导出时覆盖）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        book_ids = sorted(set(f['book_id'] for f in facts))
        book_tag = f"_b{'_'.join(str(b) for b in book_ids)}"
        filename = f'chapter_facts_{min_review_status.lower()}{book_tag}_{timestamp}.jsonl'
        filepath = os.path.join(output_dir, filename)

        valid_count = 0
        with open(filepath, 'w', encoding='utf-8') as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
                valid_count += 1

        # 生成 dataset_info.json
        info_path = os.path.join(output_dir, 'dataset_info.json')
        info = {}
        if os.path.exists(info_path):
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)

        info[filename.replace('.jsonl', '')] = {
            'file_name': filename,
            'formatting': 'alpaca',
            'columns': {'instruction': 'instruction', 'input': 'input', 'output': 'output'},
        }

        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {valid_count} samples to {filepath}")

        return {
            'status': 'success',
            'samples': valid_count,
            'file': filepath,
            'book_count': len(set(f['book_id'] for f in facts)),
        }

    def export_qa_pairs(self, book_id: int = None,
                        output_dir: str = None) -> dict:
        """导出 QA 对话对为训练数据"""
        conn = self.db.connect()
        output_dir = output_dir or TRAINING_DATA_DIR
        os.makedirs(output_dir, exist_ok=True)

        with conn.cursor() as cursor:
            sql = """SELECT cm.id, cm.session_id, cm.role, cm.content,
                            cs.book_id, cb.title as book_title,
                            GROUP_CONCAT(cit.excerpt SEPARATOR ' ||| ') as citations
                     FROM novel_chat_message cm
                     JOIN novel_chat_session cs ON cs.id = cm.session_id
                     JOIN novel_book cb ON cb.id = cs.book_id
                     LEFT JOIN novel_citation cit ON cit.message_id = cm.id
                     WHERE cm.role = 'assistant' AND cm.content != ''"""
            params = []
            if book_id:
                sql += " AND cs.book_id = %s"
                params.append(book_id)
            sql += " GROUP BY cm.id ORDER BY cm.session_id, cm.message_index"

            cursor.execute(sql, params)
            messages = cursor.fetchall()

        if not messages:
            return {'status': 'error', 'message': 'No QA messages found'}

        samples = []
        for m in messages:
            citations = m.get('citations', '')
            context = f"\n引用原文:\n{citations}" if citations else ""

            sample = {
                'instruction': f"关于小说《{m['book_title']}》的问答。",
                'input': f"问题/回答内容: {m['content'][:200]}",
                'output': m['content'],
                'metadata': {
                    'book_id': m['book_id'],
                    'session_id': m['session_id'],
                    'message_id': m['id'],
                    'source': 'qa_chat',
                }
            }
            samples.append(sample)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'qa_pairs_{timestamp}.jsonl'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')

        logger.info(f"Exported {len(samples)} QA pairs to {filepath}")

        return {
            'status': 'success',
            'samples': len(samples),
            'file': filepath,
        }
