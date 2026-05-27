"""
提取编排器。
为每个 chunk 做实体/关系/事件提取。
支持两种模式: model (llama-server) 和 rule (规则 fallback)。
"""
import json
import logging
from typing import Optional

from app.clients.model_client import ModelClient
from app.pipeline.candidate_generator import generate_candidates

logger = logging.getLogger(__name__)


async def extract_chunk(
    chunk_text: str,
    chapter_title: str,
    book_title: str,
    chapter_id: int,
    chunk_id: int,
    use_model: bool = False,
    prior_hint: dict = None,
    provider: str = "local"
) -> dict:
    """为一个 chunk 执行提取

    Args:
        use_model: True 则调模型, False 则用规则
        prior_hint: DeepSeek 生成的梗概
        provider: "local" (llama-server 9B) 或 "deepseek" (DeepSeek API)
    """
    # 先生成候选提示（规则部分总是运行）
    candidates = generate_candidates(chunk_text, chapter_id, chunk_id)

    # 如果有 prior_hint，将角色名、别名、地点加入候选
    if prior_hint and isinstance(prior_hint, dict):
        for ch in prior_hint.get('main_characters', []):
            name = ch.get('name', '')
            if name and name not in candidates['all_candidates']:
                candidates['all_candidates'].insert(0, name)
            for alias in ch.get('aliases', []):
                if alias and alias not in candidates['all_candidates']:
                    candidates['all_candidates'].append(alias)
        for loc in prior_hint.get('key_locations', []):
            if loc and loc not in candidates['all_candidates']:
                candidates['all_candidates'].append(loc)

    if use_model:
        return await _model_extract(chunk_text, chapter_title, book_title,
                                    chapter_id, chunk_id, candidates, prior_hint,
                                    provider=provider)
    else:
        return _rule_extract(chunk_text, chapter_id, chunk_id, candidates, prior_hint)


async def _model_extract(
    chunk_text: str, chapter_title: str, book_title: str,
    chapter_id: int, chunk_id: int, candidates: dict,
    prior_hint: dict = None, provider: str = "local"
) -> dict:
    """使用 LLM 做模型提取 — 支持 local (llama-server 9B) 和 deepseek (API)"""
    # 构建角色 + 提取策略提示
    # 构建角色 + 提取策略提示
    extra_hints = ""
    if prior_hint and isinstance(prior_hint, dict):
        # 角色名+别名
        characters = prior_hint.get('main_characters', [])
        if characters:
            names = []
            for ch in characters:
                name = ch.get('name', '')
                aliases = ch.get('aliases', [])
                if aliases:
                    names.append(f"{name}（别名: {'、'.join(aliases)}）")
                else:
                    names.append(name)
            extra_hints += f"\n【已知角色】{', '.join(names)}\n"

        # 提取策略：entity_focus + relation_focus
        strategy = prior_hint.get('extraction_strategy', {})
        if strategy:
            entity_focus = strategy.get('entity_focus', [])
            if entity_focus:
                extra_hints += f"\n【提取重点·实体类别】{', '.join(entity_focus)}\n"
            relation_focus = strategy.get('relation_focus', [])
            if relation_focus:
                extra_hints += f"\n【提取重点·关系类别】{', '.join(relation_focus)}\n"

    prompt = f"""从以下文本中提取实体、关系和事件。

书名: {book_title}
章节: {chapter_title}
{extra_hints}
文本:
{chunk_text}

候选提示 (规则检测到的高频词): {json.dumps(candidates['all_candidates'], ensure_ascii=False)}

请输出严格 JSON 格式，使用以下结构（只提取文本中明确提到的内容）：

{{
  "chapter_summary": "本段内容的一句话概要",
  "entity_mentions": [
    {{"surface_text": "角色名", "normalized_name": "标准名", "entity_type": "CHARACTER|LOCATION|ITEM|ORGANIZATION", "mention_role": "CANONICAL|GENERIC_MENTION|UNCERTAIN", "evidence_text": "原文证据", "confidence": 0.0-1.0, "description": "简要描述"}}
  ],
  "relation_mentions": [
    {{"source": "实体名", "target": "实体名", "relation_type": "关系类型", "evidence_text": "原文证据", "confidence": 0.0-1.0}}
  ],
  "event_mentions": [
    {{"event_type": "事件类型", "description": "事件描述", "participants": ["实体名"], "location": "地点", "evidence_text": "原文证据", "confidence": 0.0-1.0}}
  ]
}}
"""
    try:
        client = ModelClient(provider=provider)
        result = await client.chat_json([
            {"role": "system", "content": "你是精确的小说实体提取助手。只基于提供的文本提取，不添加外部知识。"},
            {"role": "user", "content": prompt}
        ])
        if isinstance(result, dict) and "error" in result:
            logger.warning(f"{provider} extraction failed, falling back to rules: {result['error']}")
            return _rule_extract(chunk_text, chapter_id, chunk_id, candidates, prior_hint)
        return result if isinstance(result, dict) else {"entity_mentions": [], "relation_mentions": [], "event_mentions": []}
    except Exception as e:
        logger.warning(f"Model extraction exception ({provider}), falling back to rules: {e}")
        return _rule_extract(chunk_text, chapter_id, chunk_id, candidates, prior_hint)


def _rule_extract(chunk_text: str, chapter_id: int, chunk_id: int, candidates: dict, prior_hint: dict = None) -> dict:
    """使用规则做提取——利用 prior_hint 的 entity_focus 给实体分类"""
    # 从 prior_hint 提取 entity_focus 和 key_locations
    entity_focus_tags = []
    key_locations = set()
    main_char_names = set()
    main_char_aliases = {}

    if prior_hint and isinstance(prior_hint, dict):
        strategy = prior_hint.get('extraction_strategy', {})
        entity_focus_tags = strategy.get('entity_focus', [])

        for loc in prior_hint.get('key_locations', []):
            if loc:
                key_locations.add(loc)

        for ch in prior_hint.get('main_characters', []):
            name = ch.get('name', '')
            if name:
                main_char_names.add(name)
            for alias in ch.get('aliases', []):
                if alias:
                    main_char_names.add(alias)
                if name:
                    if alias not in main_char_aliases:
                        main_char_aliases[alias] = name
                    if name not in main_char_aliases:
                        main_char_aliases[name] = name

    # 从候选名字中构建 entity_mentions，利用 entity_focus 提示辅助分类
    entity_mentions = []
    for name in candidates['all_candidates'][:20]:
        if name not in chunk_text:
            continue

        # 判断实体类型
        entity_type = "CHARACTER"
        mention_role = "UNCERTAIN"
        confidence = 0.3

        # 如果是关键地点 → LOCATION
        if name in key_locations:
            entity_type = "LOCATION"
            mention_role = "CANONICAL"
            confidence = 0.6
        # 如果出现在 entity_focus 中的"地点"类别 → LOCATION
        elif any("地点" in tag or "位置" in tag or "场景" in tag for tag in entity_focus_tags):
            # 可能含"山""河""洞""国""寺"等字 → 地点
            if any(suffix in name for suffix in ["山", "河", "洞", "国", "寺", "谷", "岭", "海", "湖", "岛", "州", "城"]):
                entity_type = "LOCATION"
                mention_role = "CANONICAL"
                confidence = 0.5
        # 如果出现在 entity_focus 中的"法器"类别 → ITEM
        elif any("法器" in tag or "法宝" in tag or "物品" in tag or "武器" in tag for tag in entity_focus_tags):
            if any(suffix in name for suffix in ["棒", "杖", "刀", "剑", "枪", "鞭", "环", "索", "扇", "旗", "幡", "珠", "瓶", "塔"]):
                entity_type = "ITEM"
                mention_role = "CANONICAL"
                confidence = 0.5

        # 如果 name 是某角色的别名，normalized_name 用主名
        normalized = main_char_aliases.get(name, name)

        entity_mentions.append({
            "surface_text": name,
            "normalized_name": normalized,
            "entity_type": entity_type,
            "mention_role": mention_role,
            "evidence_text": name,
            "confidence": confidence
        })

    # 简单的关系提取——同段中出现且逐对出现的候选实体可能有关联
    # 用启发式：同一 chunk 中同时出现的不同实体，且中间有常见关系动词
    relation_mentions = []
    event_mentions = []
    entity_names_in_text = [e['normalized_name'] for e in entity_mentions if e['normalized_name'] in chunk_text]
    seen_pairs = set()
    # 关系动词模式
    rel_verbs = ['是', '有', '叫', '称', '为', '拜', '封', '任', '娶', '嫁', '生', '养',
                 '收', '传', '授', '赐', '封', '派', '令', '命', '率', '领', '随', '从',
                 '属', '管', '治', '统', '辖', '居', '住', '在', '往', '来', '入', '出']
    for i, src in enumerate(entity_names_in_text[:10]):
        for tgt in entity_names_in_text[i+1:]:
            if src == tgt:
                continue
            pair_key = tuple(sorted([src, tgt]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            # 查找源和目标之间是否有关系动词
            src_pos = chunk_text.find(src)
            tgt_pos = chunk_text.find(tgt)
            if src_pos == -1 or tgt_pos == -1:
                continue
            between = chunk_text[min(src_pos, tgt_pos):max(src_pos, tgt_pos)]
            found_verb = None
            for v in rel_verbs:
                if v in between:
                    found_verb = v
                    break
            confidence = 0.4 if found_verb else 0.2
            rel_type = "RELATED_TO"
            if found_verb in ('是', '为', '称', '叫'):
                rel_type = "IDENTITY_AS"
            elif found_verb in ('拜', '传', '授', '收'):
                rel_type = "MENTOR_OF"
            elif found_verb in ('娶', '嫁', '生'):
                rel_type = "FAMILY_OF"
            elif found_verb in ('率', '领', '随', '从'):
                rel_type = "FOLLOWS"
            elif found_verb in ('居', '住', '在'):
                rel_type = "LOCATED_AT"
            relation_mentions.append({
                "source": src,
                "target": tgt,
                "relation_type": rel_type,
                "evidence_text": between[:80] if len(between) > 80 else between,
                "confidence": round(confidence, 2),
            })

    # 简单的事件提取——有明确动作和实体的段落
    event_keywords = ['打', '战', '斗', '攻', '杀', '救', '助', '逃', '追', '访',
                      '寻', '遇', '见', '会', '聚', '宴', '祭', '求', '请', '献']
    for name in entity_names_in_text[:8]:
        pos = chunk_text.find(name)
        if pos == -1:
            continue
        # 取实体前后 60 字作为事件上下文
        start = max(0, pos - 60)
        end = min(len(chunk_text), pos + len(name) + 60)
        context = chunk_text[start:end]
        found_action = None
        for kw in event_keywords:
            if kw in context:
                found_action = kw
                break
        if found_action:
            # 找该段中的其他参与者
            participants = [name]
            for other in entity_names_in_text:
                if other != name and other in context and other not in participants:
                    participants.append(other)
            event_mentions.append({
                "event_type": "ACTION",
                "description": context[:100] + ('…' if len(context) > 100 else ''),
                "participants": participants[:5],
                "location": "",
                "evidence_text": context[:120],
                "confidence": 0.35,
            })

    # truncate 到合理数量
    if len(relation_mentions) > 20:
        relation_mentions = sorted(relation_mentions, key=lambda r: r['confidence'], reverse=True)[:20]
    if len(event_mentions) > 10:
        event_mentions = sorted(event_mentions, key=lambda e: e['confidence'], reverse=True)[:10]

    return {
        "chapter_id": chapter_id,
        "chunk_id": chunk_id,
        "chapter_summary": chunk_text[:100] if len(chunk_text) > 100 else chunk_text,
        "entity_mentions": entity_mentions,
        "relation_mentions": relation_mentions,
        "event_mentions": event_mentions,
        "uncertain_items": [e for e in entity_mentions if e['confidence'] < 0.5][:5]
    }
