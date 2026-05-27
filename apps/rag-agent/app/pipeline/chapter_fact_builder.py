"""
ChapterFact 构建器。
将一章内所有 chunk 的提取结果合并为一个 ChapterFact。
"""
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def build_chapter_fact(
    chapter_id: int,
    chapter_title: str,
    chapter_summary: str,
    chunk_results: List[dict]
) -> dict:
    """合并 chunk 级提取结果，构建 ChapterFact

    Args:
        chunk_results: extract_chunk 的结果列表
    """
    all_entities = []
    all_relations = []
    all_events = []
    evidence_records = []
    seen_entities = set()

    for chunk_res in chunk_results:
        # 合并实体
        for ent in chunk_res.get("entity_mentions", []):
            name = ent.get("normalized_name", ent.get("surface_text", ""))
            if name and name not in seen_entities:
                seen_entities.add(name)
                evidence_id = f"ev_{chunk_res.get('chunk_id', 0)}_{len(evidence_records)}"
                evidence_records.append({
                    "evidence_id": evidence_id,
                    "chunk_id": chunk_res.get("chunk_id", 0),
                    "text": ent.get("evidence_text", ""),
                    "supports": [name]
                })
                all_entities.append({
                    "display_name": name,
                    "surface_texts": [ent.get("surface_text", name)],
                    "local_aliases": [],
                    "description": ent.get("description", ""),
                    "evidence_ids": [evidence_id],
                    "confidence": ent.get("confidence", 0.3),
                    "alias_risk": ent.get("mention_role") == "GENERIC_MENTION"
                })
            elif name:
                # 已有实体，更新 surface_texts
                for e in all_entities:
                    if e["display_name"] == name:
                        st = ent.get("surface_text", name)
                        if st not in e["surface_texts"]:
                            e["surface_texts"].append(st)
                        break

        # 合并关系
        for rel in chunk_res.get("relation_mentions", []):
            all_relations.append(rel)

        # 合并事件
        for evt in chunk_res.get("event_mentions", []):
            all_events.append(evt)

    return {
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "chapter_summary": chapter_summary,
        "characters": all_entities,
        "locations": [],
        "items": [],
        "organizations": [],
        "relations": all_relations,
        "events": all_events,
        "evidence_records": evidence_records,
        "quality_flags": []
    }
