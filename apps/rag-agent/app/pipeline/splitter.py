import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# 中文章节模式
CHAPTER_PATTERNS = [
    # 第X章/回/节/卷/篇 (阿拉伯数字)
    re.compile(r"第[0-9零○Ｏ一二三四五六七八九十百千万亿]+[章回节卷篇集部]"),
    # 第X章/回/节/卷/篇 (中文数字)
    re.compile(r"第[零○Ｏ一二三四五六七八九十百千万亿]+[章回节卷篇集部]"),
    # 卷X / Chapter X (英文)
    re.compile(r"(?:卷|Chapter|CHAPTER|Section|SECTION)\s*[0-9零○Ｏ一二三四五六七八九十百千万亿]+"),
    # 纯数字章节 (如 001 作为章节标记)
    re.compile(r"^[0-9]{3,}\s*$", re.MULTILINE),
    # 卷上/中/下
    re.compile(r"卷[上中下]"),
    # 回目 (如 第一回, 第二回)
    re.compile(r"第[零○Ｏ一二三四五六七八九十百千万亿]+[回章节]"),
]

# 非故事集段落检测——如果遇到"目 录"，"CONTENTS"等，是目录页
CATALOG_PATTERNS = [
    re.compile(r"^目[录錄 ]", re.MULTILINE),
    re.compile(r"^CONTENTS", re.IGNORECASE),
]


def detect_structure(text: str) -> dict:
    """检测文本结构，返回章节模式和置信度"""
    matches = []
    for i, pattern in enumerate(CHAPTER_PATTERNS):
        found = pattern.findall(text)
        if found:
            matches.append(
                {
                    "pattern_index": i,
                    "pattern": pattern.pattern,
                    "count": len(found),
                    "samples": found[:5],
                }
            )

    has_catalog = any(p.search(text) for p in CATALOG_PATTERNS)

    # 根据匹配数量推断
    if matches:
        best = max(matches, key=lambda m: m["count"])
        return {
            "patterns": matches,
            "has_catalog": has_catalog,
            "best_pattern": best["pattern"],
            "chapter_count": best["count"],
            "confidence": min(1.0, best["count"] / 50),  # 50章以上满置信
        }
    return {
        "patterns": [],
        "has_catalog": has_catalog,
        "chapter_count": 0,
        "confidence": 0.0,
    }


def split_chapters(text: str, prior_hint: dict = None) -> List[dict]:
    """将全文拆分为章节列表

    可传入 prior_hint（DeepSeek 生成的梗概），其中的 chapter_patterns
    会作为附加章节模式参与分割。

    返回: [{
        'chapter_number': int,
        'title': str,
        'content': str,
        'start_offset': int,
        'end_offset': int,
        'split_strategy': str,
        'split_confidence': float
    }]
    """
    # 0. 如果有 prior_hint，将 DeepSeek 提供的章节模式加入列表
    if prior_hint and isinstance(prior_hint, dict):
        extra_patterns = prior_hint.get('chapter_patterns', [])
        for pat in extra_patterns:
            if pat and isinstance(pat, str):
                try:
                    compiled = re.compile(pat)
                    # 避免重复添加完全相同的模式
                    if not any(p.pattern == compiled.pattern for p in CHAPTER_PATTERNS):
                        CHAPTER_PATTERNS.append(compiled)
                        logger.info(f"Added prior-hint pattern: {pat}")
                except re.error:
                    logger.warning(f"Invalid regex from prior_hint: {pat}")

    # 1. 检测结构
    structure = detect_structure(text)

    # 2. 如果没有章节模式，按固定长度分割
    if not structure["patterns"]:
        return _split_by_fixed_length(text)

    # 3. 收集所有章节边界的偏移量
    boundaries = _find_chapter_boundaries(text)

    if len(boundaries) <= 1:
        return _split_by_fixed_length(text)

    # 4. 构建章节
    chapters = []
    for i in range(len(boundaries)):
        start = boundaries[i]["offset"]
        end = boundaries[i + 1]["offset"] if i + 1 < len(boundaries) else len(text)
        chapter_title = boundaries[i]["title"]
        chapter_text = text[start:end].strip()

        if not chapter_text:
            continue

        chapters.append(
            {
                "chapter_number": i + 1,
                "title": chapter_title,
                "content": chapter_text,
                "start_offset": start,
                "end_offset": end,
                "split_strategy": "regex_chapter",
                "split_confidence": structure["confidence"],
            }
        )

    return chapters


def _find_chapter_boundaries(text: str) -> List[Dict]:
    """找到所有章节边界"""
    all_matches = []

    # 合并所有模式的匹配
    for pattern in CHAPTER_PATTERNS:
        for match in pattern.finditer(text):
            all_matches.append(
                {"offset": match.start(), "title": match.group().strip()}
            )

    # 去重 + 按 offset 排序
    seen_offsets = set()
    unique = []
    for m in sorted(all_matches, key=lambda x: x["offset"]):
        if m["offset"] not in seen_offsets:
            seen_offsets.add(m["offset"])
            unique.append(m)

    # 如果没有前标题文本，作为起始边界
    # 某些文本在第一个章节标题前可能有封面语、简介等
    # 保留这些作为"前言/序"
    boundaries = []
    if unique:
        if unique[0]["offset"] > 0:
            boundaries.append({"offset": 0, "title": "前言"})
    else:
        boundaries.append({"offset": 0, "title": ""})

    boundaries.extend(unique)
    return boundaries


def _split_by_fixed_length(text: str, target_chars: int = 5000) -> List[dict]:
    """当无法检测到章节时，按固定长度伪章节分割"""
    chapters = []
    pos = 0
    chapter_num = 0

    while pos < len(text):
        chapter_num += 1
        end = min(pos + target_chars, len(text))
        # 尽量在段落边界切割
        if end < len(text):
            # 向前找最近的段落边界 (\n\n)
            paragraph_end = text.rfind("\n\n", pos, end)
            if paragraph_end > pos + target_chars // 2:
                end = paragraph_end
            else:
                # 向后找下一个段落边界
                next_para = text.find("\n\n", end)
                if next_para != -1 and next_para - end < target_chars // 2:
                    end = next_para

        content = text[pos:end].strip()
        if content:
            chapters.append(
                {
                    "chapter_number": chapter_num,
                    "title": f"第{chapter_num}章",
                    "content": content,
                    "start_offset": pos,
                    "end_offset": end,
                    "split_strategy": "fixed_length",
                    "split_confidence": 0.3,
                }
            )
        pos = end

    return chapters
