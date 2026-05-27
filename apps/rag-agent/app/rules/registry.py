"""
规则注册表。
管理全局规则 + 书级别规则（rules_json）的合并与查询。
"""

import logging
from typing import Any, Optional

from app.rules.entity_rules import KNOWN_ENTITY_TYPES, KNOWN_ENTITY_KEYS
from app.rules.extraction_rules import EXTRACTION_DEFAULTS, get_extraction_config
from app.rules.chunk_rules import CHUNK_DEFAULTS, get_chunk_config
from app.rules.merge_rules import MERGE_DEFAULTS, get_merge_config
from app.rules.prior_hint_rules import PRIOR_HINT_DEFAULTS
from app.rules.relation_rules import (
    RELATION_TYPE_VOCAB,
    RELATION_SYNONYMS,
    CATEGORY_GROUPS,
    normalize_relation_type,
)
from app.rules.event_rules import EVENT_TYPE_VOCAB, normalize_event_type

logger = logging.getLogger(__name__)


class RuleRegistry:
    """规则注册表 — 全局默认 + 书级别覆盖。"""

    def __init__(self, book_id: Optional[int] = None, book_rules: Optional[dict] = None):
        self.book_id = book_id
        self.book_rules = book_rules or {}
        self._merged: Optional[dict] = None

    def _merge(self) -> dict:
        """合并全局 + 书规则。"""
        if self._merged is not None:
            return self._merged

        merged: dict[str, Any] = {
            "entity_types": dict(KNOWN_ENTITY_TYPES),
            "relation_vocab": dict(RELATION_TYPE_VOCAB),
            "event_vocab": dict(EVENT_TYPE_VOCAB),
            "extraction": dict(EXTRACTION_DEFAULTS),
            "chunk": dict(CHUNK_DEFAULTS),
            "merge": dict(MERGE_DEFAULTS),
            "prior_hint": dict(PRIOR_HINT_DEFAULTS),
        }

        if self.book_rules:
            for section in ("extraction", "chunk", "merge", "prior_hint", "entity_types"):
                book_section = self.book_rules.get(section)
                if not book_section or not isinstance(book_section, dict):
                    continue
                if section not in merged:
                    merged[section] = {}
                mode = book_section.get("__mode__", "merge")
                if isinstance(mode, str) and mode == "replace":
                    merged[section] = dict(book_section)
                else:
                    section_target = merged[section]
                    if isinstance(section_target, dict):
                        for k, v in book_section.items():
                            if k.startswith("__"):
                                continue
                            section_target[k] = v

        self._merged = merged
        return merged

    def get_entity_types(self) -> dict:
        return self._merge().get("entity_types", KNOWN_ENTITY_TYPES)

    def get_relation_types(self) -> dict:
        return self._merge().get("relation_vocab", RELATION_TYPE_VOCAB)

    def get_event_types(self) -> dict:
        return self._merge().get("event_vocab", EVENT_TYPE_VOCAB)

    def normalize_entity_type(self, type_key: str) -> Optional[str]:
        """归一化实体类型，返回规范类型键或 None。"""
        known = self.get_entity_types()
        if type_key in known:
            return type_key
        for key in known:
            display = known[key].get("display_name", "")
            if type_key == display:
                return key
        return None

    def normalize_relation_type(self, raw: str) -> str:
        return normalize_relation_type(raw)

    def normalize_event_type(self, raw: str) -> str:
        return normalize_event_type(raw)

    def get_chunk_config(self) -> dict:
        return self._merge().get("chunk", CHUNK_DEFAULTS)

    def get_extract_config(self) -> dict:
        return self._merge().get("extraction", EXTRACTION_DEFAULTS)

    def get_merge_config(self) -> dict:
        return self._merge().get("merge", MERGE_DEFAULTS)

    def get_prior_hint_config(self) -> dict:
        return self._merge().get("prior_hint", PRIOR_HINT_DEFAULTS)

    def invalidate(self) -> None:
        """清除合并缓存，强制下次重新合并。"""
        self._merged = None


# 模块级缓存
_registry_cache: dict[Optional[int], "RuleRegistry"] = {}


def get_or_create_registry(
    book_id: Optional[int] = None,
    book_rules: Optional[dict] = None,
) -> RuleRegistry:
    """工厂函数：获取或创建书级别 RuleRegistry 实例。

    使用模块级缓存复用实例。
    """
    global _registry_cache
    if book_id is not None and book_id in _registry_cache:
        existing = _registry_cache[book_id]
        if existing.book_rules == (book_rules or {}):
            return existing
        # 规则变更，刷新
        existing.book_rules = book_rules or {}
        existing.invalidate()
        return existing

    registry = RuleRegistry(book_id, book_rules)
    if book_id is not None:
        _registry_cache[book_id] = registry
    return registry
