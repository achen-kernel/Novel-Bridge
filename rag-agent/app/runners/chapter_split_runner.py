"""
Book structure analysis and chapter splitting.

Strategy:
1. Try rule-based regex patterns for common Chinese chapter formats.
2. If rules find chapters, use them.
3. If rules are uncertain, use LLM-assisted classification.
4. Fall back to treating the whole text as one chapter (structure_type='NONE').
"""

import re
import os
from typing import List, Optional

# Supported structure types
STRUCTURE_TYPES = {
    "CHAPTER": "第X章",
    "HUI": "第X回",
    "STORY": "故事集（如聊斋志异）",
    "SECTION": "篇/卷/经（如山海经）",
    "NONE": "无明显章节结构",
}

# Regex patterns for Chinese chapter/section detection
CHAPTER_PATTERNS = [
    (r"^[ 　\t]*第[一二三四五六七八九十百千万０１２３４５６７８９0-9]+[章回节部集][ 　\t]*\n?", "CHAPTER_OR_HUI"),
    (r"^[ 　\t]*第[一二三四五六七八九十百千万０１２３４５６７８９0-9]+[章回][ 　\t]+[^\n]{1,50}\n?", "CHAPTER_OR_HUI"),
    (r"^[ 　\t]*[卷篇部集][ 　\t]*[一二三四五六七八九十百千万０１２３４５６７８９0-9]+[ 　\t]*\n?", "SECTION"),
    (r"^[ 　\t]*(?:前言|序言|序|引言|引子|楔子|尾声|后记|附录|注释)[ 　\t]*\n?", "SPECIAL"),
]

# Story collection detection (e.g., 聊斋志异: each story has its own title)
STORY_COLLECTION_PATTERN = r"^[ 　\t]*[^\n]{2,30}$"

SPLITTER_VERSION = "chapter_split_v0.1"


class ChapterSplitResult:
    """Result of structure analysis for a single chapter/section."""
    def __init__(self, chapter_number: int, title: str, structure_type: str,
                 start_offset: int, end_offset: int, raw_content: str):
        self.chapter_number = chapter_number
        self.title = title
        self.structure_type = structure_type
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.raw_content = raw_content


def detect_structure_type(raw_text: str, sample_lines: int = 200) -> str:
    """
    Detect overall book structure type from the first sample_lines of text.
    Returns one of: CHAPTER, HUI, STORY, SECTION, NONE.
    """
    lines = raw_text.split("\n")
    head = "\n".join(lines[:min(sample_lines, len(lines))])

    # Count pattern matches
    chapter_count = 0
    hui_count = 0
    section_count = 0

    for line in head.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^第[0-9一二三四五六七八九十百千万]+章", stripped):
            chapter_count += 1
        elif re.match(r"^第[0-9一二三四五六七八九十百千万]+回", stripped):
            hui_count += 1
        elif re.match(r"^[卷篇部集][ 　\t]*[一二三四五六七八九十0-9]+", stripped):
            section_count += 1

    # Story collection: many short lines that look like titles
    short_title_lines = 0
    for line in head.split("\n"):
        stripped = line.strip()
        if 1 < len(stripped) <= 30 and not stripped.startswith("第"):
            short_title_lines += 1

    # Decision
    if hui_count >= 3:
        return "HUI"
    if chapter_count >= 3:
        return "CHAPTER"
    if section_count >= 3:
        return "SECTION"
    # If >10% lines look like short titles, it might be a story collection
    if short_title_lines >= 20 and len(head) > 0:
        return "STORY"
    # If only a few matches but some patterns exist
    if chapter_count + hui_count + section_count >= 2:
        return "CHAPTER"
    return "NONE"


def split_chapters(raw_text: str, book_source_id: int = 0,
                   book_id: int = 0,
                   structure_type: str = None) -> List[ChapterSplitResult]:
    """
    Split raw_text into chapters using rules + optional type hint.

    Returns list of ChapterSplitResult sorted by start_offset.
    """
    if structure_type is None:
        structure_type = detect_structure_type(raw_text)

    chapters = []

    if structure_type == "NONE":
        # No chapters found — treat whole text as one chapter
        chapters.append(ChapterSplitResult(
            chapter_number=1,
            title="全文",
            structure_type="NONE",
            start_offset=0,
            end_offset=len(raw_text),
            raw_content=raw_text,
        ))
        return chapters

    if structure_type in ("HUI", "CHAPTER"):
        return _split_numeric_chapters(raw_text, structure_type)

    if structure_type == "SECTION":
        return _split_section_chapters(raw_text)

    if structure_type == "STORY":
        return _split_story_collection(raw_text)

    # Fallback
    chapters.append(ChapterSplitResult(
        chapter_number=1,
        title="全文",
        structure_type="NONE",
        start_offset=0,
        end_offset=len(raw_text),
        raw_content=raw_text,
    ))
    return chapters


def _split_numeric_chapters(raw_text: str, structure_type: str) -> List[ChapterSplitResult]:
    """Split by 第X章 or 第X回 patterns."""
    chapters = []
    chapter_markers = []

    lines = raw_text.split("\n")
    current_offset = 0

    for line in lines:
        stripped = line.strip()
        if re.match(r"^第[0-9一二三四五六七八九十百千万]+" +
                    ("回" if structure_type == "HUI" else "章"), stripped):
            chapter_markers.append((current_offset, stripped))
        current_offset += len(line) + 1  # +1 for newline

    if not chapter_markers:
        # Fallback to whole text
        return [ChapterSplitResult(
            chapter_number=1, title="全文",
            structure_type="NONE",
            start_offset=0, end_offset=len(raw_text),
            raw_content=raw_text,
        )]

    for i, (offset, title) in enumerate(chapter_markers):
        end_offset = chapter_markers[i + 1][0] if i + 1 < len(chapter_markers) else len(raw_text)
        chapters.append(ChapterSplitResult(
            chapter_number=i + 1,
            title=title[:100],
            structure_type=structure_type,
            start_offset=offset,
            end_offset=end_offset,
            raw_content=raw_text[offset:end_offset].strip(),
        ))

    return chapters


def _split_section_chapters(raw_text: str) -> List[ChapterSplitResult]:
    """Split by 卷/篇/部 patterns (e.g., 山海经: 南山经, 西山经)."""
    chapters = []
    pattern = re.compile(r"^[ 　\t]*[卷篇部][ 　\t]*[一二三四五六七八九十百千万0-9]+[ 　\t]*\n?", re.MULTILINE)

    matches = [(m.start(), m.group().strip()) for m in pattern.finditer(raw_text)]

    if not matches:
        return [ChapterSplitResult(
            chapter_number=1, title="全文",
            structure_type="NONE",
            start_offset=0, end_offset=len(raw_text),
            raw_content=raw_text,
        )]

    for i, (start, title) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(raw_text)
        chapters.append(ChapterSplitResult(
            chapter_number=i + 1,
            title=title,
            structure_type="SECTION",
            start_offset=start,
            end_offset=end,
            raw_content=raw_text[start:end].strip(),
        ))

    return chapters


def _split_story_collection(raw_text: str) -> List[ChapterSplitResult]:
    """Split story collections where each story starts with a title line."""
    chapters = []
    lines = raw_text.split("\n")

    # Find potential story title lines (short lines, not continuation of paragraph)
    story_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # A story title: 2-30 chars, standalone (previous line is blank or file start)
        if 1 < len(stripped) <= 30 and not stripped.startswith(("「", "『", "（", "［", "{")):
            if i == 0 or not lines[i - 1].strip() or len(lines[i - 1].strip()) > 30:
                story_starts.append(i)

    # Need at least 3 story candidates to treat as story collection
    if len(story_starts) < 3:
        return [ChapterSplitResult(
            chapter_number=1, title="全文",
            structure_type="NONE",
            start_offset=0, end_offset=len(raw_text),
            raw_content=raw_text,
        )]

    for i, line_idx in enumerate(story_starts):
        current_offset = sum(len(l) + 1 for l in lines[:line_idx])
        next_offset = sum(len(l) + 1 for l in lines[:story_starts[i + 1]]) \
            if i + 1 < len(story_starts) else len(raw_text)
        chapters.append(ChapterSplitResult(
            chapter_number=i + 1,
            title=lines[line_idx].strip()[:100],
            structure_type="STORY",
            start_offset=current_offset,
            end_offset=next_offset,
            raw_content=raw_text[current_offset:next_offset].strip(),
        ))

    return chapters
