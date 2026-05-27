"""
实体/关系/事件抽取规则。
"""
from typing import Optional

EXTRACTION_DEFAULTS = {
    "max_entities_per_chunk": 30,
    "max_relations_per_chunk": 40,
    "max_events_per_chunk": 20,
    "max_entity_length": 50,
    "min_entity_length": 1,
    "require_display_name": True,
    "extract_relations": True,
    "extract_events": True,
    "extract_summary": True,
    "confidence_threshold": 0.3,
    "alias_generation": True,
    "max_aliases_per_entity": 5,
    "enable_coreference": True,
    "coreference_window": 3,
}


def get_extraction_config(book_rules: Optional[dict] = None) -> dict:
    """合并书级别覆盖"""
    config = dict(EXTRACTION_DEFAULTS)
    if book_rules and isinstance(book_rules, dict):
        book_extract = book_rules.get("extraction") or book_rules.get("extraction_rules") or {}
        if isinstance(book_extract, dict):
            mode = book_extract.pop("__mode__", "merge") if isinstance(book_extract, dict) else "merge"
            if mode == "replace":
                config = book_extract
            else:
                for k, v in book_extract.items():
                    if k.startswith("__"):
                        continue
                    config[k] = v
    return config
