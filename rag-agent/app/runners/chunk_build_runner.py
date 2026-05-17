"""
Chunk generation from chapter text.

Strategy:
- Target 800-1500 Chinese characters per chunk
- 150-300 character overlap
- Prefer paragraph boundaries
- Do NOT cross chapter boundaries
"""

import hashlib
from typing import List, Tuple

# Chunking parameters
TARGET_CHARS = 1200
MIN_CHARS = 800
MAX_CHARS = 1500
OVERLAP_CHARS = 200
CHUNK_VERSION = "chunk_v0.1"


class ChunkResult:
    """A single chunk generated from chapter text."""
    def __init__(self, text: str, start_offset: int, end_offset: int,
                 char_count: int, chunk_index: int):
        self.text = text
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.char_count = char_count
        self.chunk_index = chunk_index
        self.content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_chinese_char(c: str) -> bool:
    """Check if character is CJK Unified Ideograph."""
    return '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf'


def _count_chinese(text: str) -> int:
    """Count Chinese characters in text."""
    return sum(1 for c in text if _is_chinese_char(c))


def _find_paragraph_boundary(text: str, start: int, direction: str = "forward") -> int:
    """
    Find the nearest paragraph boundary (double newline or single newline).
    direction: 'forward' to search forward from start, 'backward' to search backward.
    """
    if direction == "forward":
        # Find next \n\n or \n
        idx = text.find("\n\n", start)
        if idx == -1 or idx > start + 200:
            idx = text.find("\n", start)
        return idx if idx != -1 else len(text)
    else:
        # Find previous \n\n or \n
        idx = text.rfind("\n\n", 0, start)
        if idx == -1 or start - idx > 200:
            idx = text.rfind("\n", 0, start)
        return idx if idx != -1 else 0


def build_chunks(chapter_text: str, chapter_start_offset: int = 0) -> List[ChunkResult]:
    """
    Split chapter_text into chunks using sliding window with overlap.

    Args:
        chapter_text: Full text of the chapter.
        chapter_start_offset: Global offset of this chapter in the whole book.

    Returns:
        List of ChunkResult sorted by chunk_index.
    """
    if not chapter_text or not chapter_text.strip():
        return []

    chunks = []
    text_len = len(chapter_text)
    pos = 0
    chunk_index = 0

    while pos < text_len:
        # Determine end for this chunk
        end = min(pos + TARGET_CHARS, text_len)

        # Try to find a clean paragraph boundary near the target
        if end < text_len:
            boundary = _find_paragraph_boundary(chapter_text, end, "forward")
            # Only use boundary if it's within MAX_CHARS from start
            if boundary <= pos + MAX_CHARS:
                end = boundary
            elif boundary > pos + MAX_CHARS:
                # Hard cut at MAX_CHARS
                end = pos + MAX_CHARS

        chunk_text = chapter_text[pos:end].strip()
        if not chunk_text:
            pos = end
            continue

        chunks.append(ChunkResult(
            text=chunk_text,
            start_offset=chapter_start_offset + pos,
            end_offset=chapter_start_offset + end,
            char_count=_count_chinese(chunk_text),
            chunk_index=chunk_index,
        ))

        chunk_index += 1

        # Next position: apply overlap
        next_pos = end - OVERLAP_CHARS
        if next_pos <= pos:
            next_pos = end
        pos = next_pos

        # Safety: if we're stuck near the end, just finish
        if text_len - pos < MIN_CHARS and pos < text_len:
            final_text = chapter_text[pos:].strip()
            if final_text:
                chunks.append(ChunkResult(
                    text=final_text,
                    start_offset=chapter_start_offset + pos,
                    end_offset=chapter_start_offset + text_len,
                    char_count=_count_chinese(final_text),
                    chunk_index=chunk_index,
                ))
            break

    return chunks
