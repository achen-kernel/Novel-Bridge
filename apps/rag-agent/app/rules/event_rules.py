"""
事件类型词表（中文可控词表）。
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# ============================================================
# 全局事件类型词表
# ============================================================

EVENT_TYPE_VOCAB = {
    # ---- 政治/权力 ----
    "登基": {"type": "登基", "label": "登基", "category": "政治/权力",
             "description": "皇帝或君主正式即位"},
    "即位": {"type": "即位", "label": "即位", "category": "政治/权力",
             "description": "继承王位或皇位"},
    "禅让": {"type": "禅让", "label": "禅让", "category": "政治/权力",
             "description": "君主将皇位禅让给他人"},
    "废立": {"type": "废立", "label": "废立", "category": "政治/权力",
             "description": "废除或另立君主"},
    "篡位": {"type": "篡位", "label": "篡位", "category": "政治/权力",
             "description": "通过非法手段夺取王位"},
    "立储": {"type": "立储", "label": "立储", "category": "政治/权力",
             "description": "确立皇位继承人"},
    "封王": {"type": "封王", "label": "封王", "category": "政治/权力",
             "description": "册封为王爵"},
    "封后": {"type": "封后", "label": "封后", "category": "政治/权力",
             "description": "册封皇后"},

    # ---- 军事/战争 ----
    "出征": {"type": "出征", "label": "出征", "category": "军事/战争",
             "description": "出兵征讨"},
    "凯旋": {"type": "凯旋", "label": "凯旋", "category": "军事/战争",
             "description": "军队获胜归来"},
    "战败": {"type": "战败", "label": "战败", "category": "军事/战争",
             "description": "军事行动失败"},
    "投降": {"type": "投降", "label": "投降", "category": "军事/战争",
             "description": "向敌方投降"},
    "结盟": {"type": "结盟", "label": "结盟", "category": "军事/战争",
             "description": "缔结军事或政治同盟"},
    "背叛": {"type": "背叛", "label": "背叛", "category": "军事/战争",
             "description": "背叛盟约或君主"},
    "议和": {"type": "议和", "label": "议和", "category": "军事/战争",
             "description": "商议和平停战"},

    # ---- 婚姻/家庭 ----
    "缔结婚约": {"type": "缔结婚约", "label": "缔结婚约", "category": "婚姻/家庭",
                 "description": "订立婚约"},
    "大婚": {"type": "大婚", "label": "大婚", "category": "婚姻/家庭",
             "description": "正式举行婚礼"},
    "纳妾": {"type": "纳妾", "label": "纳妾", "category": "婚姻/家庭",
             "description": "娶侧室"},
    "和亲": {"type": "和亲", "label": "和亲", "category": "婚姻/家庭",
             "description": "通过联姻达成政治目的"},

    # ---- 社会/个人 ----
    "比武": {"type": "比武", "label": "比武", "category": "社会/个人",
             "description": "武艺比试"},
    "科举": {"type": "科举", "label": "科举", "category": "社会/个人",
             "description": "参加科举考试"},
    "上任": {"type": "上任", "label": "上任", "category": "社会/个人",
             "description": "赴任官职"},
    "罢官": {"type": "罢官", "label": "罢官", "category": "社会/个人",
             "description": "被免去官职"},
    "升迁": {"type": "升迁", "label": "升迁", "category": "社会/个人",
             "description": "官职晋升"},
    "流放": {"type": "流放", "label": "流放", "category": "社会/个人",
             "description": "被流放到边远地区"},
    "谋反": {"type": "谋反", "label": "谋反", "category": "社会/个人",
             "description": "谋划造反"},
    "刺杀": {"type": "刺杀", "label": "刺杀", "category": "社会/个人",
             "description": "暗杀重要人物"},
    "政变": {"type": "政变", "label": "政变", "category": "社会/个人",
             "description": "发动政变"},
    "出逃": {"type": "出逃", "label": "出逃", "category": "社会/个人",
             "description": "逃离某地"},
    "隐居": {"type": "隐居", "label": "隐居", "category": "社会/个人",
             "description": "退隐山林"},
    "寻访": {"type": "寻访", "label": "寻访", "category": "社会/个人",
             "description": "寻访人物或地点"},

    # ---- 师徒/传承 ----
    "拜师": {"type": "拜师", "label": "拜师", "category": "师徒/传承",
             "description": "拜某人为师"},
    "收徒": {"type": "收徒", "label": "收徒", "category": "师徒/传承",
             "description": "收某人为弟子"},
    "传功": {"type": "传功", "label": "传功", "category": "师徒/传承",
             "description": "传授功法或技艺"},
    "修炼": {"type": "修炼", "label": "修炼", "category": "师徒/传承",
             "description": "修炼功法"},
    "渡劫": {"type": "渡劫", "label": "渡劫", "category": "师徒/传承",
             "description": "渡过天劫"},
    "突破": {"type": "突破", "label": "突破", "category": "师徒/传承",
             "description": "修为突破境界"},
    "炼器": {"type": "炼器", "label": "炼器", "category": "师徒/传承",
             "description": "炼制法器"},
    "炼丹": {"type": "炼丹", "label": "炼丹", "category": "师徒/传承",
             "description": "炼制丹药"},

    # ---- 寻宝/夺宝 ----
    "寻宝": {"type": "寻宝", "label": "寻宝", "category": "寻宝/夺宝",
             "description": "寻找宝物"},
    "夺宝": {"type": "夺宝", "label": "夺宝", "category": "寻宝/夺宝",
             "description": "争夺宝物"},
    "献宝": {"type": "献宝", "label": "献宝", "category": "寻宝/夺宝",
             "description": "献上宝物"},
    "铸剑": {"type": "铸剑", "label": "铸剑", "category": "寻宝/夺宝",
             "description": "铸造宝剑或神器"},

    # ---- 人际关系 ----
    "结义": {"type": "结义", "label": "结义", "category": "人际关系",
             "description": "结拜为兄弟/姐妹"},
    "复仇": {"type": "复仇", "label": "复仇", "category": "人际关系",
             "description": "为仇恨报复"},
    "报恩": {"type": "报恩", "label": "报恩", "category": "人际关系",
             "description": "报答恩情"},
    "誓言": {"type": "誓言", "label": "誓言", "category": "人际关系",
             "description": "立下誓言"},

    # ---- 仪式/天象 ----
    "祭祀": {"type": "祭祀", "label": "祭祀", "category": "仪式/天象",
             "description": "举行祭祀仪式"},
    "占卜": {"type": "占卜", "label": "占卜", "category": "仪式/天象",
             "description": "占卜吉凶"},
    "预言": {"type": "预言", "label": "预言", "category": "仪式/天象",
             "description": "做出预言"},
    "天象": {"type": "天象", "label": "天象异变", "category": "仪式/天象",
             "description": "天象异变"},

    # ---- 灾难 ----
    "灾难": {"type": "灾难", "label": "灾难", "category": "灾难",
             "description": "发生灾难"},
    "瘟疫": {"type": "瘟疫", "label": "瘟疫", "category": "灾难",
             "description": "发生瘟疫"},
    "旱灾": {"type": "旱灾", "label": "旱灾", "category": "灾难",
             "description": "发生旱灾"},
    "水灾": {"type": "水灾", "label": "水灾", "category": "灾难",
             "description": "发生水灾"},
    "地震": {"type": "地震", "label": "地震", "category": "灾难",
             "description": "发生地震"},

    # ---- 行政 ----
    "招安": {"type": "招安", "label": "招安", "category": "行政",
             "description": "朝廷招安"},
    "剿匪": {"type": "剿匪", "label": "剿匪", "category": "行政",
             "description": "剿灭匪患"},
    "巡游": {"type": "巡游", "label": "巡游", "category": "行政",
             "description": "巡视游历"},
    "赐婚": {"type": "赐婚", "label": "赐婚", "category": "行政",
             "description": "皇帝赐婚"},
    "使节": {"type": "使节", "label": "出使", "category": "行政",
             "description": "奉命出使"},
    "朝贡": {"type": "朝贡", "label": "朝贡", "category": "行政",
             "description": "向朝廷进贡"},
    "会盟": {"type": "会盟", "label": "会盟", "category": "行政",
             "description": "诸侯或各方会盟"},
    "借兵": {"type": "借兵", "label": "借兵", "category": "行政",
             "description": "向他人借兵"},
    "劝降": {"type": "劝降", "label": "劝降", "category": "行政",
             "description": "劝说投降"},

    # ---- 司法/刑罚 ----
    "审问": {"type": "审问", "label": "审问", "category": "司法/刑罚",
             "description": "审讯问话"},
    "刑讯": {"type": "刑讯", "label": "刑讯", "category": "司法/刑罚",
             "description": "用刑逼供"},
    "越狱": {"type": "越狱", "label": "越狱", "category": "司法/刑罚",
             "description": "从监狱逃跑"},
    "劫法场": {"type": "劫法场", "label": "劫法场", "category": "司法/刑罚",
                "description": "在刑场劫人"},
    "探监": {"type": "探监", "label": "探监", "category": "司法/刑罚",
             "description": "探望狱中之人"},
    "行刺": {"type": "行刺", "label": "行刺", "category": "司法/刑罚",
             "description": "行刺暗杀"},
    "暗杀": {"type": "暗杀", "label": "暗杀", "category": "司法/刑罚",
             "description": "暗中杀害"},
    "毒杀": {"type": "毒杀", "label": "毒杀", "category": "司法/刑罚",
             "description": "用毒药杀害"},

    # ---- 死亡 ----
    "自尽": {"type": "自尽", "label": "自尽", "category": "死亡",
             "description": "自杀"},
    "殉情": {"type": "殉情", "label": "殉情", "category": "死亡",
             "description": "为爱情而死"},
    "殉国": {"type": "殉国", "label": "殉国", "category": "死亡",
             "description": "为国家而死"},
    "战死": {"type": "战死", "label": "战死", "category": "死亡",
             "description": "在战斗中死亡"},
    "病逝": {"type": "病逝", "label": "病逝", "category": "死亡",
             "description": "因病去世"},
    "寿终正寝": {"type": "寿终正寝", "label": "寿终正寝", "category": "死亡",
                  "description": "自然老死"},
    "谋杀": {"type": "谋杀", "label": "谋杀", "category": "死亡",
             "description": "被谋杀"},

    # ---- 刑罚(重) ----
    "诛九族": {"type": "诛九族", "label": "诛九族", "category": "刑罚(重)",
               "description": "诛灭九族"},
    "满门抄斩": {"type": "满门抄斩", "label": "满门抄斩", "category": "刑罚(重)",
                 "description": "全家处斩"},
    "抄家": {"type": "抄家", "label": "抄家", "category": "刑罚(重)",
             "description": "查抄家产"},
    "贬为庶人": {"type": "贬为庶人", "label": "贬为庶人", "category": "刑罚(重)",
                 "description": "贬为平民"},
    "入狱": {"type": "入狱", "label": "入狱", "category": "刑罚(重)",
             "description": "被关入监狱"},
    "赦免": {"type": "赦免", "label": "赦免", "category": "刑罚(重)",
             "description": "被赦免释放"},

    # ---- 军事行动 ----
    "起义": {"type": "起义", "label": "起义", "category": "军事行动",
             "description": "发动起义"},
    "起兵": {"type": "起兵", "label": "起兵", "category": "军事行动",
             "description": "起兵反抗"},
    "平叛": {"type": "平叛", "label": "平叛", "category": "军事行动",
             "description": "平定叛乱"},
    "招兵": {"type": "招兵", "label": "招兵", "category": "军事行动",
             "description": "招募士兵"},
    "练兵": {"type": "练兵", "label": "练兵", "category": "军事行动",
             "description": "训练军队"},
    "阅兵": {"type": "阅兵", "label": "阅兵", "category": "军事行动",
             "description": "检阅军队"},
}

EVENT_SYNONYMS = {
    "登基": ["即位", "登基大典", "登极", "践祚", "御极"],
    "驾崩": ["病逝", "驾崩", "龙驭上宾"],
    "禅让": ["让位", "逊位", "退位"],
    "篡位": ["篡权", "夺位", "篡夺"],
    "大婚": ["成亲", "结婚", "完婚", "婚娶"],
    "缔结婚约": ["定亲", "订婚", "下聘", "纳采"],
    "战死": ["阵亡", "殉职", "捐躯"],
    "自尽": ["自杀", "自刎", "上吊", "投井", "服毒"],
    "出征": ["出师", "征讨", "伐"],
    "复仇": ["报仇", "雪恨", "报"],
    "修炼": ["修行", "修练", "练功", "打坐"],
    "拜师": ["拜", "投师", "师从"],
    "结义": ["结拜", "义结金兰", "八拜之交"],
    "科举": ["应试", "赶考", "赴考", "入试"],
    "流放": ["发配", "充军", "贬谪"],
    "刺杀": ["行刺", "暗刺"],
    "谋反": ["造反", "反叛", "叛乱"],
    "收徒": ["纳徒", "收弟子"],
    "突破": ["晋级", "进阶", "破境"],
}


def normalize_event_type(raw: str, vocabulary: Optional[List[str]] = None) -> str:
    """
    将模型输出的原始事件类型归一化为词表中的标准类型。
    规则：精确匹配 > 后缀匹配 > 同义词查找 > 部分匹配 > 原样返回
    """
    if not raw or not isinstance(raw, str):
        return raw

    raw_stripped = raw.strip()
    if not raw_stripped:
        return raw

    vocab_list = vocabulary or list(EVENT_TYPE_VOCAB.keys())

    # 1. 精确匹配
    if raw_stripped in vocab_list:
        return raw_stripped

    # 2. 建立词汇表中英文对照索引
    label_map = {}
    for key, info in EVENT_TYPE_VOCAB.items():
        label = info.get("label", key)
        if label and label != key:
            label_map[label] = key

    if raw_stripped in label_map:
        return label_map[raw_stripped]

    # 3. 同义词映射
    for canonical, synonyms in EVENT_SYNONYMS.items():
        if raw_stripped in synonyms:
            return canonical

    # 4. 包含关系——输入包含标准类型，或标准类型包含输入
    for vt in sorted(vocab_list, key=len, reverse=True):
        if vt in raw_stripped or raw_stripped in vt:
            return vt

    # 5. 部分匹配——标准类型名包含输入的前缀/后缀
    for vt in vocab_list:
        if raw_stripped.endswith(vt) or vt.endswith(raw_stripped):
            return vt

    # 6. 启发式——去掉"了/过/着"等助词再试
    cleaned = re.sub(r"[了过着]$", "", raw_stripped)
    if cleaned != raw_stripped:
        if cleaned in vocab_list:
            return cleaned
        for vt in vocab_list:
            if cleaned.endswith(vt) or vt.endswith(cleaned):
                return vt

    logger.debug(f"Event type not normalized: '{raw}' → keeping as-is")
    return raw_stripped


def get_category_for_event(event_type: str) -> str:
    """获取事件类型所属分类"""
    info = EVENT_TYPE_VOCAB.get(event_type)
    if info:
        return info.get("category", "未分类")
    for canonical, synonyms in EVENT_SYNONYMS.items():
        if event_type in synonyms:
            info = EVENT_TYPE_VOCAB.get(canonical)
            return info.get("category", "未分类") if info else "未分类"
    return "未分类"
