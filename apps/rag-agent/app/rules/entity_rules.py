"""
Controlled vocabulary for entity types.

Each entry defines:
  - display_name: human-readable label
  - description: what this entity type represents
  - max_alias_count: max alias entries before merge dedup
  - fuzzy_match: whether fuzzy matching is allowed
  - can_merge: whether distinct mentions can be merged
  - requires_evidence: evidence citation required for acceptance
  - priority: merge priority (higher wins tie)
  - alias_generations: how many alias passes are allowed
"""

KNOWN_ENTITY_TYPES = {
    # ─── Characters & People ──────────────────────────────────────────────
    "character": {
        "display_name": "人物",
        "description": "Individual person (protagonist, supporting, minor)",
        "max_alias_count": 20,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 100,
        "alias_generations": 3,
    },
    "group": {
        "display_name": "群体/组织",
        "description": "Unstructured group of people (crowd, army, mob)",
        "max_alias_count": 10,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 70,
        "alias_generations": 2,
    },
    "title": {
        "display_name": "称号/头衔",
        "description": "Epithet, title, or honorific (not a formal rank)",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": False,
        "priority": 40,
        "alias_generations": 0,
    },
    "rank": {
        "display_name": "官职/爵位",
        "description": "Official position or noble rank",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": False,
        "priority": 40,
        "alias_generations": 0,
    },
    "dynasty": {
        "display_name": "朝代",
        "description": "Dynasty or imperial reign name",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": True,
        "priority": 50,
        "alias_generations": 0,
    },
    # ─── Locations ────────────────────────────────────────────────────────
    "location": {
        "display_name": "地点",
        "description": "Geographic location (city, region, landmark, country)",
        "max_alias_count": 10,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 80,
        "alias_generations": 2,
    },
    # ─── Organizations & Schools ──────────────────────────────────────────
    "organization": {
        "display_name": "组织/门派",
        "description": "Structured organization (sect, clan, guild, faction)",
        "max_alias_count": 10,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 80,
        "alias_generations": 2,
    },
    "school": {
        "display_name": "学派/宗门",
        "description": "Martial arts school, philosophical school, or sect",
        "max_alias_count": 8,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 75,
        "alias_generations": 2,
    },
    # ─── Items & Artifacts ────────────────────────────────────────────────
    "item": {
        "display_name": "物品",
        "description": "Ordinary physical object",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 50,
        "alias_generations": 1,
    },
    "artifact": {
        "display_name": "法宝/神器",
        "description": "Magical item, artifact, or divine weapon",
        "max_alias_count": 8,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 70,
        "alias_generations": 2,
    },
    # ─── Concepts & Events ────────────────────────────────────────────────
    "concept": {
        "display_name": "概念",
        "description": "Abstract concept, principle, or philosophy",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": False,
        "priority": 30,
        "alias_generations": 0,
    },
    "event_name": {
        "display_name": "事件名称",
        "description": "Named event (war, ceremony, disaster with proper name)",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 60,
        "alias_generations": 1,
    },
    "era": {
        "display_name": "纪元/时代",
        "description": "Historical era, age, or period name",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": True,
        "priority": 50,
        "alias_generations": 0,
    },
    # ─── Skills & Abilities ───────────────────────────────────────────────
    "skill": {
        "display_name": "技能/功法",
        "description": "Learned ability, martial technique, or cultivation method",
        "max_alias_count": 8,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 60,
        "alias_generations": 2,
    },
    "realm": {
        "display_name": "境界",
        "description": "Cultivation realm or stage",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": False,
        "priority": 40,
        "alias_generations": 0,
    },
    # ─── Nature & Beasts ──────────────────────────────────────────────────
    "beast": {
        "display_name": "灵兽/妖兽",
        "description": "Mythical beast, spirit animal, or demon",
        "max_alias_count": 8,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 60,
        "alias_generations": 2,
    },
    "plant": {
        "display_name": "灵药/植物",
        "description": "Magical herb, spirit plant, or unique flora",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 50,
        "alias_generations": 1,
    },
    # ─── Law & Documents ──────────────────────────────────────────────────
    "law": {
        "display_name": "律法/规则",
        "description": "Law, decree, rule, or regulation",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": False,
        "requires_evidence": False,
        "priority": 30,
        "alias_generations": 0,
    },
    "document": {
        "display_name": "典籍/书信",
        "description": "Book, scroll, letter, or written record",
        "max_alias_count": 5,
        "fuzzy_match": False,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 50,
        "alias_generations": 1,
    },
    # ─── Deities & Spirits ────────────────────────────────────────────────
    "deity": {
        "display_name": "神/仙/魔",
        "description": "Deity, immortal, demon lord, or divine being",
        "max_alias_count": 10,
        "fuzzy_match": True,
        "can_merge": True,
        "requires_evidence": True,
        "priority": 80,
        "alias_generations": 2,
    },
}

KNOWN_ENTITY_KEYS = list(KNOWN_ENTITY_TYPES.keys())
