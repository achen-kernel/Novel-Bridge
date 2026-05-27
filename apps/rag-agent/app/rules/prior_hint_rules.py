"""
Prior Hint 规则。
解析大模型生成的梗概，提取实体线索用于指导抽取。
"""

from typing import Any, Optional

PRIOR_HINT_DEFAULTS = {
    "max_hint_entities": 50,
    "min_entity_confidence": 0.3,
    "enable_alias_expansion": True,
    "alias_expansion_depth": 2,
    "apply_hints_to_all_chunks": True,
    "boost_exact_match": True,
    "boost_weight": 1.5,
    "hint_expiry_chapters": None,
}


def parse_prior_hint(hint_text: str) -> dict:
    """解析 prior_hint 文本为结构化实体列表。

    支持 JSON 格式和简化的文本行格式。
    """
    import json

    # 尝试 JSON 解析
    if hint_text.strip().startswith("{"):
        try:
            data = json.loads(hint_text)
            # 统一顶层结构
            if isinstance(data, dict):
                if "entities" not in data:
                    # 可能是直接是实体列表
                    for key in ("characters", "people", "items"):
                        if key in data:
                            data["entities"] = data[key]
                            break
                for section in ("chapter_patterns", "themes", "key_locations"):
                    if section not in data:
                        data[section] = []
                return data
        except json.JSONDecodeError:
            pass

    # 尝试 JSON 数组格式
    if hint_text.strip().startswith("["):
        try:
            items = json.loads(hint_text)
            if isinstance(items, list):
                return {
                    "entities": items,
                    "chapter_patterns": [],
                    "themes": [],
                    "key_locations": [],
                }
        except json.JSONDecodeError:
            pass

    # 回退：按行解析
    entities = []
    for line in hint_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            entity = {
                "name": parts[0].strip(),
                "type": parts[1].strip(),
            }
            if len(parts) >= 3 and parts[2].strip():
                entity["aliases"] = [a.strip() for a in parts[2].split(",") if a.strip()]
            entities.append(entity)

    return {
        "entities": entities,
        "chapter_patterns": [],
        "themes": [],
        "key_locations": [],
    }


def apply_prior_hint_rules(chunk_text: str, prior_hint: dict) -> list:
    """应用 prior_hint 线索，返回匹配的候选词列表。

    Args:
        chunk_text: 文本分块内容
        prior_hint: 解析后的 prior_hint 字典

    Returns:
        候选词列表，每项包含 text, type, source, confidence
    """
    candidates = []
    if not isinstance(prior_hint, dict):
        return candidates

    entities = prior_hint.get("entities", [])
    if not isinstance(entities, list):
        return candidates

    for ent in entities:
        if not isinstance(ent, dict):
            continue
        name = ent.get("name", "")
        ent_type = ent.get("type", "character")
        aliases = ent.get("aliases", [])

        if not name or len(name) < 2:
            continue

        # 精确匹配实体名
        if name in chunk_text:
            candidates.append({
                "text": name,
                "type": ent_type,
                "source": "prior_hint",
                "confidence": 0.9,
            })

        # 别名扩展匹配
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and len(alias) >= 2 and alias in chunk_text:
                    candidates.append({
                        "text": alias,
                        "type": ent_type,
                        "source": "prior_hint_alias",
                        "confidence": 0.7,
                    })

    return candidates
