"""
Stage 1: 实体名同步。
将 relation_fact 中的实体名对齐到 entity_profile.canonical_name。
用 entity_profile 的 aliases_json 构建别名→正名映射，覆盖 relation_fact 中不规范的名称。

可独立运行，支持 dry_run 预览和按 book_id 过滤。
"""
import json
import logging
from typing import List, Dict, Optional

import pymysql

logger = logging.getLogger(__name__)


class EntityNameNormalizer:
    """实体名同步器"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def run(self, book_id: Optional[int] = None, dry_run: bool = True) -> Dict:
        """
        执行实体名同步。

        Args:
            book_id: 指定书号，None=全部
            dry_run: True=只报告不改写

        Returns:
            {'status': 'ok', 'stats': {...}, 'changes': [...]}
        """
        # Step 1: 构建别名→正名映射表
        alias_map = self._build_alias_map(book_id)

        if not alias_map:
            return {
                'status': 'ok',
                'stats': {'alias_map_size': 0, 'scanned': 0, 'updated': 0, 'skipped': 0},
                'changes': [],
                'message': 'No alias map built (no entities found)'
            }

        # Step 2: 扫描 relation_fact 中的不规范实体名
        changes = []
        for field in ['source_entity_name', 'target_entity_name']:
            mismatches = self._find_mismatches(book_id, field, alias_map)
            changes.extend(mismatches)

        stats = {
            'alias_map_size': len(alias_map),
            'scanned': len(changes),
            'updated': len(changes) if not dry_run else 0,
            'skipped': 0,
        }

        if not dry_run and changes:
            updated = self._apply_changes(changes)
            stats['updated'] = updated
            logger.info(f"Entity name normalizer: updated {updated} rows")

        return {
            'status': 'ok',
            'stats': stats,
            'changes': changes if not dry_run else [],
            'change_preview': changes[:20] if dry_run else [],
            'message': f"Found {len(changes)} mismatches" + (" (dry-run)" if dry_run else f" (updated {stats['updated']})"),
        }

    def _build_alias_map(self, book_id: Optional[int] = None) -> Dict[str, str]:
        """
        从 entity_profile.aliases_json 构建 {别名: 正名} 映射。
        每条实体产生 N 对映射：{canonical_name: canonical_name, alias1: canonical_name, ...}
        """
        alias_map = {}
        sql = "SELECT canonical_name, aliases_json FROM novel_entity_profile WHERE status = 'ACTIVE'"
        params = []
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                name = row['canonical_name']
                if not name:
                    continue
                # 正名→自身（即使正名在 relation_fact 中也无需跳过，后续不重复更新）
                alias_map[name] = name
                # 别名→正名
                try:
                    aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
                    if isinstance(aliases, list):
                        for alias in aliases:
                            if isinstance(alias, str) and alias.strip():
                                alias_map[alias.strip()] = name
                except (json.JSONDecodeError, TypeError):
                    pass

        logger.info(f"Built alias map with {len(alias_map)} entries from entity profiles")
        return alias_map

    def _find_mismatches(self, book_id: Optional[int], field: str,
                         alias_map: Dict[str, str]) -> List[Dict]:
        """
        查找 relation_fact 中某字段的不规范实体名。
        返回 [{id, book_id, field, old_value, new_value, ...}]
        """
        changes = []
        sql = f"SELECT id, book_id, {field} as val FROM novel_relation_fact WHERE status = 'ACTIVE'"
        params = []
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)

        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                val = row['val']
                if not val or val == '未知' or val == '无':
                    continue

                # 查找规范名（仅精确匹配，禁止模糊匹配以免误改）
                canonical = alias_map.get(val)
                if canonical is None and len(val) >= 3:
                    # 仅对 >=3 字的尝试：如果 val 是某个实体的别名条目直接匹配
                    # （别名映射来自 aliases_json，已包含 canonical_name 自身）
                    pass

                if canonical and canonical != val:
                    changes.append({
                        'id': row['id'],
                        'book_id': row['book_id'],
                        'field': field,
                        'old_value': val,
                        'new_value': canonical,
                    })

        return changes

    def _apply_changes(self, changes: List[Dict]) -> int:
        """批量改写 relation_fact 中的实体名，捕获唯一键冲突后变更为 MERGED。"""
        count = 0
        merged = 0
        for c in changes:
            field = c['field']
            try:
                with self.conn.cursor() as cursor:
                    sql = f"UPDATE novel_relation_fact SET {field} = %s WHERE id = %s"
                    cursor.execute(sql, (c['new_value'], c['id']))
                count += 1
            except Exception:
                # 唯一键冲突：标记为 MERGED（对应的标准行已存在）
                self.conn.rollback()
                with self.conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE novel_relation_fact SET status = 'MERGED' WHERE id = %s",
                        (c['id'],)
                    )
                merged += 1
        self.conn.commit()
        logger.info(f"Applied: {count} updated, {merged} merged-due-to-conflict")
        return count
