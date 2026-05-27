"""
Stage 2: 关系去重。
处理两类重复：
1. 精准重复：完全相同的 (A, B, type) 多行
2. 双向重复：A→B 和 B→A 同 type（如"唐僧→孙悟空"和"孙悟空→唐僧"均标记为师徒关系）

策略：每组保留 confidence 最高的那行，合并 evidence_ids_json，其余标记为 MERGED。
"""
import json
import logging
from collections import defaultdict
from typing import List, Dict, Optional

import pymysql

logger = logging.getLogger(__name__)


class RelationDeduper:
    """关系去重器"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def run(self, book_id: Optional[int] = None, dry_run: bool = True) -> Dict:
        """
        执行关系去重。

        Args:
            book_id: 指定书号，None=全部
            dry_run: True=只报告不改写

        Returns:
            {'status': 'ok', 'stats': {...}, 'changes': [...]}
        """
        # Step 1: 查找所有重复组
        dup_groups = self._find_duplicates(book_id)

        stats = {
            'total_groups': len(dup_groups),
            'total_affected_rows': sum(len(g) for g in dup_groups),
            'rows_to_keep': len(dup_groups),  # 每组保留1条
            'rows_to_merge': sum(len(g) - 1 for g in dup_groups),
        }

        if not dup_groups:
            return {
                'status': 'ok',
                'stats': stats,
                'changes': [],
                'message': 'No duplicates found',
            }

        # Step 2: 生成变更预览
        changes = []
        for group in dup_groups:
            keep = group[0]
            merges = group[1:]
            for m in merges:
                changes.append({
                    'keep_id': keep['id'],
                    'merge_id': m['id'],
                    'book_id': keep['book_id'],
                    'entity_a': self._normalize_name(keep['source_name']),
                    'entity_b': self._normalize_name(keep['target_name']),
                    'relation_type': keep['relation_type'],
                    'keep_confidence': keep['confidence'],
                    'merge_confidence': m['confidence'],
                    'action': 'merge_into_keep' if not dry_run else 'would_merge',
                })

        if not dry_run:
            merged = self._apply_merges(dup_groups)
            stats['rows_actually_merged'] = merged
            logger.info(f"Relation deduper: merged {merged} duplicate rows into {len(dup_groups)} groups")

        return {
            'status': 'ok',
            'stats': stats,
            'changes': changes if not dry_run else [],
            'change_preview': changes[:20],
            'message': f"Found {stats['total_groups']} duplicate groups ({stats['rows_to_merge']} rows to merge)"
                       + (" (dry-run)" if dry_run else f" (merged {stats.get('rows_actually_merged', 0)})"),
        }

    def _find_duplicates(self, book_id: Optional[int]) -> List[List[Dict]]:
        """
        查找所有重复关系组。
        每组包含 2+ 条记录，按 (归一化后的实体对, relation_type) 分组。
        归一化：对实体名排序，使得 A→B 和 B→A 归入同一组。
        """
        sql = """SELECT id, book_id, source_entity_name, target_entity_name,
                        relation_type, confidence, evidence_ids_json
                 FROM novel_relation_fact
                 WHERE status = 'ACTIVE'"""
        params = []
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)

        # 分组：key = (e1, e2, type)，e1 <= e2 排序后
        groups = defaultdict(list)
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                e1, e2 = sorted([row['source_entity_name'], row['target_entity_name']])
                key = (row['book_id'], e1, e2, row['relation_type'])
                groups[key].append({
                    'id': row['id'],
                    'book_id': row['book_id'],
                    'source_name': row['source_entity_name'],
                    'target_name': row['target_entity_name'],
                    'relation_type': row['relation_type'],
                    'confidence': row['confidence'],
                    'evidence_ids_json': row.get('evidence_ids_json'),
                })

        # 过滤出有重复的组
        dup_groups = [g for g in groups.values() if len(g) > 1]

        # 每组按 confidence 降序排列，第0条作为保留
        for g in dup_groups:
            g.sort(key=lambda x: x['confidence'], reverse=True)

        logger.info(f"Found {len(dup_groups)} duplicate groups from {len(groups)} total groups")
        return dup_groups

    def _apply_merges(self, dup_groups: List[List[Dict]]) -> int:
        """
        执行合并：每组保留第0条（最高 confidence），其余标记 MERGED。
        如有多个 evidence_ids_json，合并到保留行。
        """
        count = 0
        with self.conn.cursor() as cursor:
            for group in dup_groups:
                keep = group[0]
                # 收集所有非空的 evidence_ids_json
                all_evidence = []
                for r in group:
                    if r.get('evidence_ids_json'):
                        try:
                            ev = json.loads(r['evidence_ids_json']) if isinstance(r['evidence_ids_json'], str) else r['evidence_ids_json']
                            if isinstance(ev, list):
                                all_evidence.extend(ev)
                        except (json.JSONDecodeError, TypeError):
                            pass

                # 合并 evidence_ids_json（去重）
                if all_evidence:
                    merged = list(set(all_evidence))
                    cursor.execute(
                        "UPDATE novel_relation_fact SET evidence_ids_json = %s WHERE id = %s",
                        (json.dumps(merged, ensure_ascii=False), keep['id'])
                    )

                # 其余行标记为 MERGED
                for r in group[1:]:
                    cursor.execute(
                        "UPDATE novel_relation_fact SET status = 'MERGED', evidence_ids_json = %s WHERE id = %s",
                        (json.dumps(list(set(all_evidence)), ensure_ascii=False) if all_evidence else None,
                         r['id'])
                    )
                    count += 1

        self.conn.commit()
        return count

    @staticmethod
    def _normalize_name(name: str) -> str:
        return (name or '').strip()
