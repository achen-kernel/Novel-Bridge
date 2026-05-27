"""
规则系统包。
包含全局规则模块和 RuleRegistry，支持书级别规则覆盖。
"""

from .entity_rules import KNOWN_ENTITY_TYPES, KNOWN_ENTITY_KEYS
from .relation_rules import RELATION_TYPE_VOCAB, RELATION_SYNONYMS, CATEGORY_GROUPS, normalize_relation_type
from .event_rules import EVENT_TYPE_VOCAB, normalize_event_type
from .extraction_rules import EXTRACTION_DEFAULTS, get_extraction_config
from .chunk_rules import CHUNK_DEFAULTS, get_chunk_config
from .merge_rules import MERGE_DEFAULTS, get_merge_config
from .prior_hint_rules import PRIOR_HINT_DEFAULTS, parse_prior_hint, apply_prior_hint_rules
from .registry import RuleRegistry, get_or_create_registry

__all__ = [
    "KNOWN_ENTITY_TYPES", "KNOWN_ENTITY_KEYS",
    "RELATION_TYPE_VOCAB", "RELATION_SYNONYMS", "CATEGORY_GROUPS", "normalize_relation_type",
    "EVENT_TYPE_VOCAB", "normalize_event_type",
    "EXTRACTION_DEFAULTS", "get_extraction_config",
    "CHUNK_DEFAULTS", "get_chunk_config",
    "MERGE_DEFAULTS", "get_merge_config",
    "PRIOR_HINT_DEFAULTS", "parse_prior_hint", "apply_prior_hint_rules",
    "RuleRegistry",
    "get_or_create_registry",
]
