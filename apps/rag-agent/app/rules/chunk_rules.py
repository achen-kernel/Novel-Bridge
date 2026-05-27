"""
分块规则。
"""
from typing import Optional

CHUNK_DEFAULTS = {
    "target_chunk_size": 2000,
    "max_chunk_size": 3000,
    "overlap": 200,
    "split_by_paragraph": True,
    "split_by_dialogue": True,
    "min_chunk_size": 500,
    "respect_chapter_boundary": True,
    "paragraph_separator": "\n\n",
    "dialogue_markers": ["「", "『", "“", "『"],
}


def get_chunk_config(book_rules: Optional[dict] = None) -> dict:
    config = dict(CHUNK_DEFAULTS)
    if book_rules and isinstance(book_rules, dict):
        book_chunk = book_rules.get("chunk") or book_rules.get("chunk_rules") or {}
        if isinstance(book_chunk, dict):
            mode = book_chunk.pop("__mode__", "merge") if isinstance(book_chunk, dict) else "merge"
            if mode == "replace":
                config = book_chunk
            else:
                for k, v in book_chunk.items():
                    if k.startswith("__"):
                        continue
                    config[k] = v
    return config
