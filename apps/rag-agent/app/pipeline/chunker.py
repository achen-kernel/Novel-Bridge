"""
Chunking module: split chapters into chunks for embedding & retrieval.

History:
- 2026-05-20: Fixed CRLF normalization (\r\n → \n) — critical bug: DB stores \r\n but
  paragraphs were split on \n\n, causing every chapter to appear as a single giant paragraph,
  forcing midpoint hard-split instead of natural paragraph boundaries.
- 2026-05-20: Added classical Chinese (文言文) detection with adaptive chunk sizing.
  文言文 is ~3-5x denser in information per character, so chunk targets are halved.
  Also added 文言文-specific sentence boundaries (也。矣。焉。哉。).
"""

import re
from typing import List

from app.utils.text_splitter import smart_split_text

# ── Modern vernacular targets ──
TARGET_MIN_CHARS = 800
TARGET_MAX_CHARS = 1500
TARGET_IDEAL_CHARS = 1200

# ── Classical Chinese targets (information density ~3-5x higher) ──
CLASSICAL_MIN_CHARS = 300
CLASSICAL_MAX_CHARS = 700
CLASSICAL_IDEAL_CHARS = 500

# ── 文言文 detection thresholds ──
_CLASSICAL_PARTICLES = {'之', '乎', '者', '也', '矣', '焉', '哉', '兮', '耶', '尔', '耳', '欤', '乃', '其', '所', '于', '以'}
_MODERN_PARTICLES = {'的', '了', '着', '过', '把', '被', '这', '那', '吧', '吗', '呢', '啊', '啦', '嘛'}

# 文言文 sentence-ending markers (in priority order for split search)
_CLASSICAL_EOS = ['也。', '矣。', '焉。', '哉。', '乎。', '耶。', '耳。', '欤。', '兮。', '也！', '乎！', '哉！']


def is_classical_chinese(text: str) -> bool:
    """Detect whether *text* is classical Chinese (文言文) vs modern vernacular (白话文).

    Uses two heuristics:
    1. Ratio of classical particles (之乎者也矣焉哉兮) to modern particles (的了着过把被)
    2. Density of 者…也 pattern (strong 文言 marker)

    Returns True if text is very likely classical Chinese.
    """
    if not text or len(text) < 50:
        return False

    classical_count = sum(text.count(p) for p in _CLASSICAL_PARTICLES)
    modern_count = sum(text.count(p) for p in _MODERN_PARTICLES)

    total = len(text)
    classical_permille = classical_count * 1000 / total
    modern_permille = modern_count * 1000 / total

    # 者…也 pattern density
    zhe_ye = len(re.findall(r'者[^。]*也', text)) * 1000 / total

    # Heuristic decision
    if classical_permille > 50 and modern_permille < 10:
        return True
    if classical_permille > 30 and zhe_ye > 2:
        return True
    if classical_permille / max(modern_permille, 1) > 5:
        return True

    return False


def _smart_split_classical(text: str, max_chars: int, book_id: int, chapter_id: int,
                           chunk_index: int, char_offset: int,
                           chapter_start_offset: int) -> List[dict]:
    """Split classical Chinese text at sentence boundaries (也。矣。焉。哉。) or at midpoint.

    For 文言文, sentences end differently than modern Chinese:
    - 也。/矣。/焉。/哉。 are strong sentence boundaries
    - 。！？ are also used but less reliably in 古文
    """
    if len(text) <= max_chars:
        return [{
            "book_id": book_id,
            "chapter_id": chapter_id,
            "chunk_index": chunk_index,
            "content": text,
            "start_offset": chapter_start_offset + char_offset,
            "end_offset": chapter_start_offset + char_offset + len(text),
        }]

    # Find the best split point near midpoint
    mid = len(text) // 2

    # Priority 1: 文言文 sentence boundaries near midpoint
    split_pos = None
    for eos in _CLASSICAL_EOS:
        # Search forward from mid
        fwd = text.find(eos, mid - max_chars // 4, mid + max_chars // 4)
        if fwd != -1:
            split_pos = fwd + len(eos)
            break
        # Search backward from mid
        bwd = text.rfind(eos, mid - max_chars // 4, mid + max_chars // 4)
        if bwd != -1:
            split_pos = bwd + len(eos)
            break

    # Priority 2: standard sentence boundaries
    if split_pos is None:
        for delim in ('。', '！', '？', '\n'):
            fwd = text.find(delim, mid - max_chars // 4, mid + max_chars // 4)
            if fwd != -1:
                split_pos = fwd + len(delim)
                break
            bwd = text.rfind(delim, mid - max_chars // 4, mid + max_chars // 4)
            if bwd != -1:
                split_pos = bwd + len(delim)
                break

    # Fallback: exact half
    if split_pos is None or split_pos <= 0 or split_pos >= len(text):
        split_pos = mid

    left = text[:split_pos]
    right = text[split_pos:]

    left_chunks = _smart_split_classical(left, max_chars, book_id, chapter_id,
                                         chunk_index, char_offset, chapter_start_offset)
    new_offset = char_offset + len(left)
    right_chunks = _smart_split_classical(right, max_chars, book_id, chapter_id,
                                          chunk_index + len(left_chunks),
                                          new_offset, chapter_start_offset)
    return left_chunks + right_chunks


def _chunk_text(text: str, book_id: int, chapter_id: int,
                chunk_index: int, char_offset: int,
                chapter_start_offset: int,
                is_classical: bool = False) -> List[dict]:
    """Split text that exceeds TARGET_MAX_CHARS.

    For classical Chinese, uses 文言文-aware split boundaries.
    For modern Chinese, uses smart_split_text (paragraph → sentence → line → word).
    """
    max_chars = CLASSICAL_MAX_CHARS if is_classical else TARGET_MAX_CHARS
    if len(text) <= max_chars:
        return [{
            "book_id": book_id,
            "chapter_id": chapter_id,
            "chunk_index": chunk_index,
            "content": text,
            "start_offset": chapter_start_offset + char_offset,
            "end_offset": chapter_start_offset + char_offset + len(text),
        }]

    if is_classical:
        return _smart_split_classical(text, CLASSICAL_IDEAL_CHARS, book_id, chapter_id,
                                      chunk_index, char_offset, chapter_start_offset)
    else:
        segments = smart_split_text(text, max_chars=TARGET_MAX_CHARS)
        result = []
        offset = char_offset
        for seg in segments:
            result.append({
                "book_id": book_id,
                "chapter_id": chapter_id,
                "chunk_index": chunk_index,
                "content": seg.text,
                "start_offset": chapter_start_offset + offset,
                "end_offset": chapter_start_offset + offset + len(seg.text),
            })
            chunk_index += 1
            offset += len(seg.text)
        return result


def chunk_chapter(
    chapter_id: int,
    book_id: int,
    chapter_text: str,
    chapter_start_offset: int,
) -> List[dict]:
    """将一章拆分为 chunks

    == CRITICAL BUG FIX (2026-05-20) ==
    MySQL stores text with \r\n line endings (Windows CRLF), but the chunker
    split on \n\n (LF-only). This caused every chapter to appear as a single
    giant paragraph, bypassing the paragraph-assembly logic and falling through
    to midpoint-based smart_split_text — which cuts at ~50% regardless of
    paragraph boundaries.

    Fix: normalize \r\n → \n at entry.

    == Classical Chinese support (2026-05-20) ==
    文言文 has ~3-5x higher information density per character and uses
    different sentence-ending markers (也。矣。焉。哉。). When detected,
    chunk size targets are halved (300-700 chars vs 800-1500) and
    split boundaries prefer 文言文 sentence markers.

    Returns: [{
        'book_id': int,
        'chapter_id': int,
        'chunk_index': int,
        'content': str,
        'start_offset': int,
        'end_offset': int
    }]
    """
    # ── Fix #1: Normalize CRLF → LF ──
    # Windows \r\n\r\n doesn't match \n\n. This was the primary cause of
    # under-chunking for all books, but especially 搜神记 (85 chunks → expected ~400)
    # and 山海经 (144 chunks → expected ~400).
    chapter_text = chapter_text.replace('\r\n', '\n').replace('\r', '\n')

    # ── Fix #2: Detect classical Chinese ──
    is_classical = is_classical_chinese(chapter_text)

    min_chars = CLASSICAL_MIN_CHARS if is_classical else TARGET_MIN_CHARS
    max_chars = CLASSICAL_MAX_CHARS if is_classical else TARGET_MAX_CHARS
    ideal_chars = CLASSICAL_IDEAL_CHARS if is_classical else TARGET_IDEAL_CHARS

    paragraphs = chapter_text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    chunk_index = 0
    char_offset = 0  # relative to chapter start

    for para in paragraphs:
        para = para.strip()
        if not para:
            char_offset += 2  # \n\n
            continue

        para_len = len(para)

        # 超长段落 -> _chunk_text split
        if para_len > max_chars:
            if current_chunk:
                # flush current chunk first
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "book_id": book_id,
                    "chapter_id": chapter_id,
                    "chunk_index": chunk_index,
                    "content": chunk_text,
                    "start_offset": chapter_start_offset
                    + (char_offset - current_length - 2 * max(0, len(current_chunk) - 1)),
                    "end_offset": chapter_start_offset + char_offset,
                })
                chunk_index += 1
                current_chunk = []
                current_length = 0
            # split the oversized paragraph
            sub_chunks = _chunk_text(
                para, book_id, chapter_id, chunk_index,
                char_offset, chapter_start_offset,
                is_classical=is_classical,
            )
            chunks.extend(sub_chunks)
            chunk_index += len(sub_chunks)
            char_offset += para_len + 2
            continue

        # 加上本段会超过上限，且当前已有足够内容
        if current_length + para_len > max_chars and current_length >= min_chars:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "book_id": book_id,
                "chapter_id": chapter_id,
                "chunk_index": chunk_index,
                "content": chunk_text,
                "start_offset": chapter_start_offset
                + (char_offset - current_length - 2 * max(0, len(current_chunk) - 1)),
                "end_offset": chapter_start_offset + char_offset,
            })
            chunk_index += 1
            current_chunk = [para]
            current_length = para_len
        else:
            current_chunk.append(para)
            current_length += para_len

        char_offset += para_len + 2  # +2 for \n\n

    # 最后一个 chunk
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        chunks.append({
            "book_id": book_id,
            "chapter_id": chapter_id,
            "chunk_index": chunk_index,
            "content": chunk_text,
            "start_offset": chapter_start_offset
            + (char_offset - current_length - 2 * max(0, len(current_chunk) - 1)),
            "end_offset": chapter_start_offset + char_offset,
        })

    return chunks
