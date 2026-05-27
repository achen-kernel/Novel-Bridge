"""
候选提示生成器。
在模型提取之前，用规则/NLP 生成候选提示。
"""
import re
from collections import Counter
from typing import List, Dict

import jieba

# 中文实体常见后缀
ENTITY_SUFFIXES = [
    '小姐', '先生', '老人', '师父', '师傅', '公子', '姑娘', '夫人', '太太',
    '老爷', '少爷', '娘娘', '皇后', '皇上', '陛下', '大王', '将军', '元帅',
    '大人', '员外', '管家', '丫鬟', '侍女', '书童', '道士', '和尚', '尼姑',
    '妖精', '妖怪', '狐仙', '仙人', '神仙', '魔王', '鬼怪', '老者', '少年',
    '娘子', '郎君', '兄弟', '妹妹', '姐姐', '哥哥', '婆婆', '公公',
]

# 对话归属模式
DIALOGUE_PATTERNS = [
    re.compile(r'([\u4e00-\u9fff]{2,6})[道说曰云]'),
    re.compile(r'([\u4e00-\u9fff]{2,6})[怒笑嘆]道'),
    re.compile(r'([\u4e00-\u9fff]{2,6})大[叫喝喊]'),
]


def generate_candidates(chunk_text: str, chapter_id: int, chunk_id: int) -> dict:
    """为一个 chunk 生成候选提示"""
    # 1. jieba 分词 + 高频词
    words = list(jieba.cut(chunk_text))
    word_freq = Counter(w for w in words if len(w) >= 2)
    high_freq = [w for w, c in word_freq.most_common(20) if c >= 2]

    # 2. 实体后缀匹配
    suffix_matches = []
    for suffix in ENTITY_SUFFIXES:
        pattern = re.compile(rf'([\u4e00-\u9fff]{{1,4}}){re.escape(suffix)}')
        for match in pattern.finditer(chunk_text):
            name = match.group(0)
            if len(name) >= 2:
                suffix_matches.append(name)

    # 3. 对话归属
    dialogue_matches = []
    for pattern in DIALOGUE_PATTERNS:
        for match in pattern.finditer(chunk_text):
            name = match.group(1)
            if len(name) >= 2:
                dialogue_matches.append(name)

    # 4. 去重合并
    unique_candidates = list(set(high_freq + suffix_matches + dialogue_matches))

    return {
        "chapter_id": chapter_id,
        "chunk_id": chunk_id,
        "high_frequency_terms": high_freq[:15],
        "entity_suffix_matches": list(set(suffix_matches))[:15],
        "dialogue_attributions": list(set(dialogue_matches))[:15],
        "all_candidates": unique_candidates[:30],
        "char_count": len(chunk_text)
    }
