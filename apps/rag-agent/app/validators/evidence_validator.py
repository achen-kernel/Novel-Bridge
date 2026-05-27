"""
证据校验器。
验证提取的 evidence_text 是否在原始文本中找到。
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """标准化文本用于比较"""
    text = re.sub(r'\s+', '', text)
    text = text.replace('，', ',').replace('。', '.').replace('！', '!').replace('？', '?')
    text = text.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    # 全角转半角
    result = []
    for c in text:
        code = ord(c)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(c)
    return ''.join(result)


def validate_evidence(evidence_text: str, source_text: str) -> str:
    """验证 evidence_text 在 source_text 中是否存在

    返回 evidence level: EXACT | NORMALIZED | NEAR | UNSUPPORTED
    """
    if not evidence_text or not source_text:
        return "UNSUPPORTED"

    # EXACT: 精确包含
    if evidence_text in source_text:
        return "EXACT"

    # NORMALIZED: 标准化后包含
    norm_evidence = normalize_text(evidence_text)
    norm_source = normalize_text(source_text)
    if norm_evidence in norm_source:
        return "NORMALIZED"

    # NEAR: 在附近位置模糊匹配
    if len(evidence_text) >= 4:
        # 取 evidence 的前4个字符和后4个字符
        prefix = evidence_text[:4]
        suffix = evidence_text[-4:]
        if prefix in source_text or suffix in source_text:
            return "NEAR"

    return "UNSUPPORTED"


def validate_chapter_fact(fact: dict, chapter_text: str) -> dict:
    """校验整个 ChapterFact 的证据

    返回增强后的 fact，包含每个实体的 evidence_status
    """
    updated_fact = dict(fact)
    updated_fact["quality_flags"] = []

    for char in updated_fact.get("characters", []):
        worst_level = "EXACT"
        for ev_id in char.get("evidence_ids", []):
            for rec in updated_fact.get("evidence_records", []):
                if rec["evidence_id"] == ev_id:
                    level = validate_evidence(rec.get("text", ""), chapter_text)
                    if level == "UNSUPPORTED":
                        worst_level = level
                    elif level == "NEAR" and worst_level != "UNSUPPORTED":
                        worst_level = level
                    elif level == "NORMALIZED" and worst_level not in ("UNSUPPORTED", "NEAR"):
                        worst_level = level
        if worst_level == "UNSUPPORTED":
            updated_fact["quality_flags"].append({
                "flag_type": "WEAK_EVIDENCE",
                "message": f"Entity '{char['display_name']}' has no supported evidence",
                "related_items": [char['display_name']]
            })

    return updated_fact
