"""
实体合并规则。
"""
from typing import Optional

MERGE_DEFAULTS = {
    "max_entity_distance": 3,
    "same_initial_threshold": 0.8,
    "fuzzy_match_threshold": 0.85,
    "enable_alias_merge": True,
    "max_aliases_per_entity": 10,
    "merge_by_first_character": True,
    "merge_by_edit_distance": True,
    "edit_distance_ratio": 0.3,
    "respect_coreference": True,
    "cross_chapter_merge": True,
}


def get_merge_config(book_rules: Optional[dict] = None) -> dict:
    config = dict(MERGE_DEFAULTS)
    if book_rules and isinstance(book_rules, dict):
        book_merge = book_rules.get("merge") or book_rules.get("merge_rules") or {}
        if isinstance(book_merge, dict):
            mode = book_merge.pop("__mode__", "merge") if isinstance(book_merge, dict) else "merge"
            if mode == "replace":
                config = book_merge
            else:
                for k, v in book_merge.items():
                    if k.startswith("__"):
                        continue
                    config[k] = v
    return config
