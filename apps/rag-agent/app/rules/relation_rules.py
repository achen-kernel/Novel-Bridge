"""
Controlled vocabulary for entity relation types (Chinese).

Each entry defines:
  - type: canonical type key
  - label: Chinese display label
  - category: broad grouping category
  - bidirectional: whether the relation is symmetric
  - description: explanation
"""

RELATION_TYPE_VOCAB = {
    # ─── Family: Parent-Child ─────────────────────────────────────────────
    "父子": {
        "type": "父子", "label": "父子", "category": "family",
        "bidirectional": False, "description": "Father-son relationship",
    },
    "父女": {
        "type": "父女", "label": "父女", "category": "family",
        "bidirectional": False, "description": "Father-daughter relationship",
    },
    "母子": {
        "type": "母子", "label": "母子", "category": "family",
        "bidirectional": False, "description": "Mother-son relationship",
    },
    "母女": {
        "type": "母女", "label": "母女", "category": "family",
        "bidirectional": False, "description": "Mother-daughter relationship",
    },
    # ─── Family: Sibling ──────────────────────────────────────────────────
    "兄弟": {
        "type": "兄弟", "label": "兄弟", "category": "family",
        "bidirectional": True, "description": "Brothers (including sworn)",
    },
    "姐妹": {
        "type": "姐妹", "label": "姐妹", "category": "family",
        "bidirectional": True, "description": "Sisters (including sworn)",
    },
    "兄妹": {
        "type": "兄妹", "label": "兄妹", "category": "family",
        "bidirectional": False, "description": "Older brother-younger sister",
    },
    "姐弟": {
        "type": "姐弟", "label": "姐弟", "category": "family",
        "bidirectional": False, "description": "Older sister-younger brother",
    },
    # ─── Family: Extended ─────────────────────────────────────────────────
    "祖孙": {
        "type": "祖孙", "label": "祖孙", "category": "family",
        "bidirectional": False, "description": "Grandparent-grandchild",
    },
    "叔侄": {
        "type": "叔侄", "label": "叔侄", "category": "family",
        "bidirectional": False, "description": "Uncle-nephew",
    },
    "舅甥": {
        "type": "舅甥", "label": "舅甥", "category": "family",
        "bidirectional": False, "description": "Maternal uncle-nephew",
    },
    "姑侄": {
        "type": "姑侄", "label": "姑侄", "category": "family",
        "bidirectional": False, "description": "Paternal aunt-niece/nephew",
    },
    "堂兄弟": {
        "type": "堂兄弟", "label": "堂兄弟", "category": "family",
        "bidirectional": True, "description": "Paternal cousins (same surname)",
    },
    "表兄弟": {
        "type": "表兄弟", "label": "表兄弟", "category": "family",
        "bidirectional": True, "description": "Maternal cousins (different surname)",
    },
    "连襟": {
        "type": "连襟", "label": "连襟", "category": "family",
        "bidirectional": True, "description": "Husbands of sisters",
    },
    "妯娌": {
        "type": "妯娌", "label": "妯娌", "category": "family",
        "bidirectional": True, "description": "Wives of brothers",
    },
    "翁婿": {
        "type": "翁婿", "label": "翁婿", "category": "family",
        "bidirectional": False, "description": "Father-in-law and son-in-law",
    },
    "婆媳": {
        "type": "婆媳", "label": "婆媳", "category": "family",
        "bidirectional": False, "description": "Mother-in-law and daughter-in-law",
    },
    "亲属(未指定)": {
        "type": "亲属(未指定)", "label": "亲属(未指定)", "category": "family",
        "bidirectional": True, "description": "Kinship, type unspecified",
    },
    # ─── Romance & Marriage ───────────────────────────────────────────────
    "夫妻": {
        "type": "夫妻", "label": "夫妻", "category": "romance",
        "bidirectional": True, "description": "Husband-wife (married couple)",
    },
    "恋人": {
        "type": "恋人", "label": "恋人", "category": "romance",
        "bidirectional": True, "description": "Lovers / romantic partners",
    },
    "未婚夫妻": {
        "type": "未婚夫妻", "label": "未婚夫妻", "category": "romance",
        "bidirectional": True, "description": "Engaged couple",
    },
    "情敌": {
        "type": "情敌", "label": "情敌", "category": "romance",
        "bidirectional": True, "description": "Romantic rivals",
    },
    # ─── Master-Disciple & Teaching ───────────────────────────────────────
    "师徒": {
        "type": "师徒", "label": "师徒", "category": "master_disciple",
        "bidirectional": False, "description": "Master-disciple (teacher-student)",
    },
    "师生": {
        "type": "师生", "label": "师生", "category": "master_disciple",
        "bidirectional": False, "description": "Teacher-student (formal education)",
    },
    "师叔侄": {
        "type": "师叔侄", "label": "师叔侄", "category": "master_disciple",
        "bidirectional": False, "description": "Martial uncle-nephew (same sect)",
    },
    "同门": {
        "type": "同门", "label": "同门", "category": "master_disciple",
        "bidirectional": True, "description": "Fellow disciples (same master)",
    },
    "传功": {
        "type": "传功", "label": "传功", "category": "master_disciple",
        "bidirectional": False, "description": "Skill/power transmission",
    },
    # ─── Social & Friendship ──────────────────────────────────────────────
    "好友": {
        "type": "好友", "label": "好友", "category": "social",
        "bidirectional": True, "description": "Close friends",
    },
    "知己": {
        "type": "知己", "label": "知己", "category": "social",
        "bidirectional": True, "description": "Soulmate / kindred spirit (platonic)",
    },
    "结义": {
        "type": "结义", "label": "结义", "category": "social",
        "bidirectional": True, "description": "Sworn siblings (blood oath)",
    },
    "邻居": {
        "type": "邻居", "label": "邻居", "category": "social",
        "bidirectional": True, "description": "Neighbors",
    },
    "同乡": {
        "type": "同乡", "label": "同乡", "category": "social",
        "bidirectional": True, "description": "Fellow townsmen / same hometown",
    },
    "同窗": {
        "type": "同窗", "label": "同窗", "category": "social",
        "bidirectional": True, "description": "Classmates / fellow students",
    },
    # ─── Hostile & Conflict ───────────────────────────────────────────────
    "敌对": {
        "type": "敌对", "label": "敌对", "category": "hostile",
        "bidirectional": True, "description": "Hostile / adversarial",
    },
    "仇敌": {
        "type": "仇敌", "label": "仇敌", "category": "hostile",
        "bidirectional": True, "description": "Mortal enemies with blood grudge",
    },
    "情敌": {
        "type": "情敌", "label": "情敌", "category": "hostile",
        "bidirectional": True, "description": "Romantic rivals",
    },
    "竞争对手": {
        "type": "竞争对手", "label": "竞争对手", "category": "hostile",
        "bidirectional": True, "description": "Competitors / rivals (non-hostile)",
    },
    # ─── Political & Hierarchy ────────────────────────────────────────────
    "君臣": {
        "type": "君臣", "label": "君臣", "category": "political",
        "bidirectional": False, "description": "Ruler-subject",
    },
    "上下级": {
        "type": "上下级", "label": "上下级", "category": "political",
        "bidirectional": False, "description": "Superior-subordinate (bureaucratic)",
    },
    "同僚": {
        "type": "同僚", "label": "同僚", "category": "political",
        "bidirectional": True, "description": "Colleagues / fellow officials",
    },
    "盟友": {
        "type": "盟友", "label": "盟友", "category": "political",
        "bidirectional": True, "description": "Allies (political or military)",
    },
    "主仆": {
        "type": "主仆", "label": "主仆", "category": "political",
        "bidirectional": False, "description": "Master-servant",
    },
    "雇佣": {
        "type": "雇佣", "label": "雇佣", "category": "political",
        "bidirectional": False, "description": "Employer-employee (hired)",
    },
    "医患": {
        "type": "医患", "label": "医患", "category": "political",
        "bidirectional": False, "description": "Doctor-patient",
    },
    # ─── Military & Combat ────────────────────────────────────────────────
    "统帅": {
        "type": "统帅", "label": "统帅", "category": "military",
        "bidirectional": False, "description": "Commander-subordinate (military)",
    },
    "战友": {
        "type": "战友", "label": "战友", "category": "military",
        "bidirectional": True, "description": "Comrades-in-arms",
    },
    "降将": {
        "type": "降将", "label": "降将", "category": "military",
        "bidirectional": False, "description": "Surrendered/submitted general",
    },
    "俘虏": {
        "type": "俘虏", "label": "俘虏", "category": "military",
        "bidirectional": False, "description": "Captor-prisoner of war",
    },
    "人质": {
        "type": "人质", "label": "人质", "category": "military",
        "bidirectional": False, "description": "Hostage taker-hostage",
    },
    # ─── Organizational ────────────────────────────────────────────────────
    "同门": {
        "type": "同门", "label": "同门", "category": "organizational",
        "bidirectional": True, "description": "Same sect / organization members",
    },
    "同宗": {
        "type": "同宗", "label": "同宗", "category": "organizational",
        "bidirectional": True, "description": "Same clan members",
    },
    "下属": {
        "type": "下属", "label": "下属", "category": "organizational",
        "bidirectional": False, "description": "Supervisor-subordinate",
    },
    "合伙人": {
        "type": "合伙人", "label": "合伙人", "category": "organizational",
        "bidirectional": True, "description": "Business partners",
    },
    # ─── Economic ─────────────────────────────────────────────────────────
    "债主": {
        "type": "债主", "label": "债主", "category": "economic",
        "bidirectional": False, "description": "Creditor-debtor",
    },
    "恩人": {
        "type": "恩人", "label": "恩人", "category": "economic",
        "bidirectional": False, "description": "Benefactor-beneficiary",
    },
    "施舍": {
        "type": "施舍", "label": "施舍", "category": "economic",
        "bidirectional": False, "description": "Donor-recipient (charity)",
    },
    "买卖": {
        "type": "买卖", "label": "买卖", "category": "economic",
        "bidirectional": False, "description": "Buyer-seller transaction",
    },
    "物主": {
        "type": "物主", "label": "物主", "category": "economic",
        "bidirectional": False, "description": "Owner-possessed item relation",
    },
    # ─── Special / Cultivation ────────────────────────────────────────────
    "夺舍": {
        "type": "夺舍", "label": "夺舍", "category": "special",
        "bidirectional": False, "description": "Body possession / soul snatching",
    },
    "共生": {
        "type": "共生", "label": "共生", "category": "special",
        "bidirectional": True, "description": "Symbiotic relationship",
    },
    "契约": {
        "type": "契约", "label": "契约", "category": "special",
        "bidirectional": True, "description": "Contractual bond (spirit beast pact, etc.)",
    },
    "转世": {
        "type": "转世", "label": "转世", "category": "special",
        "bidirectional": False, "description": "Reincarnation relationship",
    },
    "附身": {
        "type": "附身", "label": "附身", "category": "special",
        "bidirectional": False, "description": "Spirit possession",
    },
    # ─── Generic ──────────────────────────────────────────────────────────
    "认识": {
        "type": "认识", "label": "认识", "category": "social",
        "bidirectional": True, "description": "Acquainted / knows each other",
    },
    "未知": {
        "type": "未知", "label": "未知", "category": "unknown",
        "bidirectional": True, "description": "Unknown or unclassified relation",
    },
}

# ─── Synonym map for normalization ─────────────────────────────────────────
RELATION_SYNONYMS = {
    # Family parent-child
    "父亲": "父子",
    "爸爸": "父子",
    "爹": "父子",
    "儿子": "父子",
    "女儿": "父女",
    "母亲": "母子",
    "妈妈": "母子",
    "娘": "母子",
    "儿子(母)": "母子",
    # Family sibling
    "哥哥": "兄弟",
    "弟弟": "兄弟",
    "姐姐": "姐妹",
    "妹妹": "姐妹",
    "兄长": "兄弟",
    "弟弟(兄)": "兄弟",
    "姐姐(妹)": "姐妹",
    "妹妹(姐)": "姐妹",
    # Family extended
    "爷爷": "祖孙",
    "奶奶": "祖孙",
    "孙子": "祖孙",
    "孙女": "祖孙",
    "外公": "祖孙",
    "外婆": "祖孙",
    "叔叔": "叔侄",
    "伯伯": "叔侄",
    "舅舅": "舅甥",
    "姑姑": "姑侄",
    "堂兄": "堂兄弟",
    "堂弟": "堂兄弟",
    "表兄": "表兄弟",
    "表弟": "表兄弟",
    "岳父": "翁婿",
    "公公": "婆媳",
    # Romance
    "丈夫": "夫妻",
    "妻子": "夫妻",
    "老公": "夫妻",
    "老婆": "夫妻",
    "夫君": "夫妻",
    "娘子": "夫妻",
    "男朋友": "恋人",
    "女朋友": "恋人",
    "情人": "恋人",
    "未婚夫": "未婚夫妻",
    "未婚妻": "未婚夫妻",
    "爱人": "夫妻",
    # Master-disciple
    "老师": "师徒",
    "师父": "师徒",
    "师傅": "师徒",
    "徒弟": "师徒",
    "弟子": "师徒",
    "学生": "师生",
    "徒儿": "师徒",
    "师尊": "师徒",
    # Social
    "朋友": "好友",
    "好朋友": "好友",
    "挚友": "好友",
    "同学": "同窗",
    "同门师兄": "同门",
    "同门师弟": "同门",
    "师兄": "同门",
    "师弟": "同门",
    "师姐": "同门",
    "师妹": "同门",
    "义兄": "结义",
    "义弟": "结义",
    "结拜兄弟": "结义",
    "结拜": "结义",
    # Hostile
    "敌人": "敌对",
    "仇人": "仇敌",
    "死敌": "仇敌",
    "对手": "竞争对手",
    "死对头": "敌对",
    "宿敌": "仇敌",
    # Political
    "皇帝": "君臣",
    "臣子": "君臣",
    "主公": "主仆",
    "主人": "主仆",
    "仆人": "主仆",
    "奴婢": "主仆",
    "侍卫": "主仆",
    "上级": "上下级",
    "下属": "上下级",
    "上司": "上下级",
    "部下": "上下级",
    "同事": "同僚",
    # Military
    "将军": "统帅",
    "士兵": "统帅",
    "主帅": "统帅",
    # Economic
    "恩公": "恩人",
    "救命恩人": "恩人",
    "债主(经济)": "债主",
    "欠债": "债主",
    # Special
    "主宠": "契约",
    "灵兽契约": "契约",
}

# ─── Category groups ──────────────────────────────────────────────────────
CATEGORY_GROUPS = {
    "family": ["父子", "父女", "母子", "母女", "兄弟", "姐妹", "兄妹", "姐弟",
               "祖孙", "叔侄", "舅甥", "姑侄", "堂兄弟", "表兄弟", "连襟",
               "妯娌", "翁婿", "婆媳", "亲属(未指定)"],
    "romance": ["夫妻", "恋人", "未婚夫妻", "情敌"],
    "master_disciple": ["师徒", "师生", "师叔侄", "同门", "传功"],
    "social": ["好友", "知己", "结义", "邻居", "同乡", "同窗", "认识"],
    "hostile": ["敌对", "仇敌", "情敌", "竞争对手"],
    "political": ["君臣", "上下级", "同僚", "盟友", "主仆", "雇佣", "医患"],
    "military": ["统帅", "战友", "降将", "俘虏", "人质"],
    "organizational": ["同门", "同宗", "下属", "合伙人"],
    "economic": ["债主", "恩人", "施舍", "买卖", "物主"],
    "special": ["夺舍", "共生", "契约", "转世", "附身"],
    "unknown": ["未知"],
}


def normalize_relation_type(raw: str) -> str:
    """Normalize a raw relation type string to canonical form.

    Priority:
      1. Direct match in RELATION_TYPE_VOCAB
      2. Synonym map lookup
      3. Substring match against canonical type keys
      4. Heuristic fallback
    """
    cleaned = raw.strip()

    # 1. Direct match
    if cleaned in RELATION_TYPE_VOCAB:
        return cleaned

    # 2. Synonym map
    if cleaned in RELATION_SYNONYMS:
        return RELATION_SYNONYMS[cleaned]

    # 3. Substring match against canonical keys
    for key in RELATION_TYPE_VOCAB:
        if key in cleaned or cleaned in key:
            return key

    # 4. Heuristic fallback
    if "师" in cleaned or "徒" in cleaned or "传" in cleaned:
        return "师徒"
    if "父" in cleaned or "母" in cleaned or "子" in cleaned or "女" in cleaned:
        if "夫" in cleaned or "妻" in cleaned:
            return "夫妻"
        return "亲属(未指定)"
    if "兄" in cleaned or "弟" in cleaned:
        return "兄弟"
    if "姐" in cleaned or "妹" in cleaned:
        return "姐妹"
    if "友" in cleaned or "朋" in cleaned:
        return "好友"
    if "敌" in cleaned or "仇" in cleaned:
        return "仇敌"
    if "君" in cleaned or "臣" in cleaned:
        return "君臣"
    if "主" in cleaned or "仆" in cleaned:
        return "主仆"
    if "夫" in cleaned or "妻" in cleaned or "婚" in cleaned:
        return "夫妻"
    if "恋" in cleaned or "爱" in cleaned:
        return "恋人"
    if "同" in cleaned:
        return "同门"
    if "盟" in cleaned:
        return "盟友"

    return "未知"
