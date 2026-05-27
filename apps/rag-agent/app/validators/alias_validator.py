"""
别名校验器。
包含: Generic Mention Blocklist, Do-Not-Merge Rules, 泛称检测。
"""
from typing import List, Tuple, Optional

# 泛称 Blocklist — 这些词不应全局合并为特定人物
GENERIC_BLOCKLIST = [
    '师父', '师傅', '老师', '先生',
    '小姐', '姑娘', '夫人', '太太', '妾身',
    '老人', '老者', '老翁', '老汉', '老妇',
    '少年', '童子', '小孩', '孩子', '小厮',
    '丫鬟', '侍女', '仆人', '管家', '婢女',
    '道士', '和尚', '尼姑', '妖精', '狐仙',
    '皇上', '陛下', '大王', '将军', '元帅',
    '某人', '某生', '书生', '公子', '娘子',
]

# 可分离的称呼前缀
TITLE_PREFIXES = ['老', '小', '大', '二', '三', '四', '五', '阿']

# 常见姓氏（百家姓前30）
SURNAMES = {'赵', '钱', '孙', '李', '周', '吴', '郑', '王', '冯', '陈',
            '褚', '卫', '蒋', '沈', '韩', '杨', '朱', '秦', '尤', '许',
            '何', '吕', '施', '张', '孔', '曹', '严', '华', '金', '魏'}


def is_generic_mention(name: str) -> bool:
    """判断是否为泛称提及"""
    if not name:
        return True

    # 直接在 blocklist 中
    if name in GENERIC_BLOCKLIST:
        return True

    # 匹配 "X师父", "X小姐" 等模式
    for generic in GENERIC_BLOCKLIST:
        if name.endswith(generic) and len(name) > len(generic):
            # 前面的部分应该是姓氏或称呼前缀
            prefix = name[:-len(generic)]
            if is_title_or_surname(prefix):
                return False  # 有姓氏则不是泛称
            return True  # 无姓氏则是临时泛称

    return False


def is_title_or_surname(text: str) -> bool:
    """判断是否为姓氏或常用称呼"""
    if len(text) == 1 and text in SURNAMES:
        return True
    if text in TITLE_PREFIXES:
        return True
    return False


def should_block_merge(name_a: str, name_b: str) -> Tuple[str, str, float]:
    """判断两个名字是否应该禁止合并

    Returns: (decision, reason, confidence)
    decision: "BLOCK" | "MERGE" | "UNCERTAIN"
    """
    # Rule 1: 都是泛称 → 不能合并
    if is_generic_mention(name_a) and is_generic_mention(name_b):
        return ("BLOCK", "Both are generic mentions, cannot merge globally", 0.9)

    # Rule 2: 姓氏不同 → 不能合并
    surname_a = _extract_surname(name_a)
    surname_b = _extract_surname(name_b)
    if surname_a and surname_b and surname_a != surname_b:
        return ("BLOCK", f"Different surnames: {surname_a} vs {surname_b}", 0.95)

    # Rule 3: 同前缀不同后缀 → 不能合并
    if _same_prefix_different_suffix(name_a, name_b):
        return ("BLOCK", "Same prefix with different suffix, likely different entities", 0.85)

    # Rule 4: 完全一致 → 可合并
    if name_a == name_b:
        return ("MERGE", "Identical names", 0.99)

    # Rule 5: 近似匹配（编辑距离 ≤ 1）
    if _levenshtein(name_a, name_b) <= 1:
        return ("MERGE", "Very similar names (edit distance <= 1)", 0.7)

    # Rule 6: 一个是另一个的子串
    if name_a in name_b or name_b in name_a:
        shorter = name_a if len(name_a) < len(name_b) else name_b
        longer = name_b if len(name_a) < len(name_b) else name_a
        # 检查较长的是否只是加了称呼
        suffix = longer[len(shorter):]
        if suffix in TITLE_PREFIXES or suffix in ['先生', '小姐', '公子']:
            return ("MERGE", f"Name with title suffix: {shorter} -> {longer}", 0.6)
        return ("UNCERTAIN", f"One name is substring of another: {shorter} vs {longer}", 0.4)

    return ("UNCERTAIN", f"Names differ significantly: {name_a} vs {name_b}", 0.2)


def _extract_surname(name: str) -> Optional[str]:
    """提取姓氏"""
    if len(name) >= 2 and name[0] in SURNAMES:
        return name[0]
    return None


def _same_prefix_different_suffix(name_a: str, name_b: str) -> bool:
    """判断是否为同前缀不同后缀"""
    # 至少需要 2 字相同前缀
    min_prefix = 2
    prefix_len = 0
    for i in range(min(len(name_a), len(name_b))):
        if name_a[i] == name_b[i]:
            prefix_len += 1
        else:
            break

    if prefix_len >= min_prefix and abs(len(name_a) - len(name_b)) <= 2:
        # 不同后缀
        suffix_a = name_a[prefix_len:]
        suffix_b = name_b[prefix_len:]
        if suffix_a and suffix_b and suffix_a != suffix_b:
            return True
    return False


def _levenshtein(a: str, b: str) -> int:
    """编辑距离"""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                curr[j] + 1,
                prev[j + 1] + 1,
                prev[j] + (ca != cb)
            ))
        prev = curr
    return prev[-1]


def get_chapter_entity_view(mentions: List[dict]) -> List[dict]:
    """构建章节实体视图（只保留本 chapter 的实体，去重）"""
    seen = {}
    for m in mentions:
        name = m.get('normalized_name') or m.get('surface_text', '')
        if not name:
            continue
        if name not in seen:
            seen[name] = {
                'display_name': name,
                'surface_texts': [m.get('surface_text', '')],
                'entity_type': m.get('entity_type', 'CHARACTER'),
                'is_generic': bool(m.get('is_generic', False)),
                'do_not_merge_globally': bool(m.get('do_not_merge_globally', False)),
                'mention_count': 1,
                'first_appearance': str(m.get('created_at', '')),
            }
        else:
            st = m.get('surface_text', '')
            if st and st not in seen[name]['surface_texts']:
                seen[name]['surface_texts'].append(st)
            seen[name]['mention_count'] += 1

    return list(seen.values())
