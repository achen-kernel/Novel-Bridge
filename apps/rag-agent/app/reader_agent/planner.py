"""@NB-ENTRYPOINT Stage 6E ReaderAgent deterministic planner.

Turns a user's natural-language request into an executable plan:
  question + book_id → mode, optimized_question, targets, confidence, warnings

The planner is deterministic (no model calls). It exists to:
1. Remove mode-selection burden from the user.
2. Rewrite vague questions into retrieval-friendly prompts.
3. Provide a `request_patch` the frontend merges into `/api/reader-agent/run`.

"auto" exists only in the planner — it is never a persisted ReaderMode.

Usage:
    from app.reader_agent.planner import ReaderAgentPlanner
    plan = ReaderAgentPlanner().plan(book_id=6, question="追踪孙悟空和唐僧关系变化")
"""

from __future__ import annotations

from typing import Any

from app.agent_runtime.schemas import ToolCallStep
from app.reader_agent.memory.session_memory import SessionMemory
from app.reader_agent.reference_resolver import resolve_question
from app.reader_agent.schemas import PlanResponse, PlanRequestPatch

SessionContext = SessionMemory | None


# ── book catalog: title + known entities ──────────────────────────────
BOOK_CATALOG: dict[int, dict[str, Any]] = {
    6: {
        "title": "西游记",
        "characters": [
            "孙悟空", "唐僧", "猪八戒", "沙僧", "白骨精", "铁扇公主",
            "牛魔王", "红孩儿", "如来", "观音", "玉皇大帝", "太白金星",
            "二郎神", "哪吒", "菩提祖师", "镇元大仙", "黄袍怪",
        ],
        "items": ["芭蕉扇", "金箍棒", "紧箍咒", "炼丹炉", "九齿钉耙", "月牙铲"],
        "settings": ["火焰山", "花果山", "五行山", "昆仑", "天宫", "龙宫", "西天"],
    },
    7: {
        "title": "聊斋志异",
        "characters": [
            "聂小倩", "宁采臣", "婴宁", "王子服", "狐女", "书生",
            "娇娜", "黄英", "席方平", "画皮",
        ],
        "items": [],
        "settings": ["鬼狐", "异类", "人鬼关系", "神异", "狐媚", "幽冥"],
    },
    8: {
        "title": "搜神记",
        "characters": ["干宝", "董永", "韩凭", "紫玉", "左慈", "于吉", "费长房"],
        "items": [],
        "settings": ["神异", "异界", "伦理", "报应", "孝义", "巫术", "仙道"],
    },
    9: {
        "title": "山海经",
        "characters": ["西王母", "夸父", "精卫", "刑天", "黄帝", "蚩尤", "大禹", "伏羲", "女娲"],
        "items": [],
        "settings": [
            "昆仑", "异兽", "山川", "海内", "海外", "神人", "大荒",
            "南山经", "西山经", "北山经", "东山经", "中山经", "海内经",
        ],
    },
    10: {
        "title": "水浒传",
        "characters": [
            "宋江", "林冲", "鲁智深", "武松", "晁盖", "李逵", "吴用",
            "卢俊义", "杨志", "燕青", "柴进", "花荣", "戴宗", "石秀",
            "潘金莲", "西门庆", "高俅", "蒋门神",
        ],
        "items": [],
        "settings": ["梁山", "招安", "生辰纲", "江湖", "义气", "聚义厅", "东京", "沧州"],
    },
}


# ── helper: find known targets in question ────────────────────────────
def _find_targets(book_id: int, question: str) -> list[dict[str, str]]:
    """Return known entity targets found in the question text."""
    catalog = BOOK_CATALOG.get(book_id, BOOK_CATALOG[6])
    results: list[dict[str, str]] = []
    seen = set()
    for kind, names in [
        ("character", catalog["characters"]),
        ("item", catalog["items"]),
        ("setting", catalog["settings"]),
    ]:
        for name in names:
            if name in question and name not in seen:
                seen.add(name)
                results.append({"name": name, "type": kind})
    return results


def _extract_fallback_target(question: str, book_id: int) -> str:
    """Extract a plausible target name when no known entity matches."""
    catalog = BOOK_CATALOG.get(book_id, BOOK_CATALOG[6])
    cleaned = question
    for prefix in ["请", "帮我", "分析", "追踪", "梳理", "说明", "解释", "看看", "讲讲", "基于证据"]:
        cleaned = cleaned.replace(prefix, "")
    for punct in "？?。！!，,、；;：:""''（）()":
        cleaned = cleaned.replace(punct, " ")
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    if tokens:
        candidate = tokens[0][:24]
        if len(candidate) >= 2:
            return candidate
    return catalog["title"]


def _has_multiple_targets(targets: list[dict[str, str]]) -> bool:
    return len(targets) >= 2


def _count_entity_mentions(question: str) -> int:
    """Count how many distinct known entities appear across all books."""
    seen = set()
    for catalog in BOOK_CATALOG.values():
        for kind in ("characters", "items", "settings"):
            for name in catalog[kind]:
                if name in question:
                    seen.add(name)
    return len(seen)


# ── mode inference ────────────────────────────────────────────────────
_TRACE_PATTERNS = [
    "追踪", "时间线", "线索", "变化", "演变", "过程", "阶段",
    "出场", "如何成为", "关键节点", "发展", "历程", "轨迹",
    "出现", "沿革", "变迁",
]
_ANALYZE_PATTERNS = [
    "分析", "人物形象", "性格", "关系", "特点", "转变",
    "评价", "形象", "矛盾", "互动", "羁绊", "解析",
]
_ENRICH_PATTERNS = [
    "反哺", "修正", "补充知识库", "KnowledgePatch",
    "citation_fix", "证据修正", "patch",
]
# Relation patterns shared by both analyze and trace
_RELATION_PATTERNS = ["关系", "矛盾", "冲突", "合作", "师徒", "互动", "羁绊"]


def _infer_mode(question: str) -> str:
    """Return one of answer/analyze/trace/enrich based on question text."""
    q = question.strip()
    if not q:
        return "answer"

    # enrich first (highest specificity)
    if any(kw in q for kw in _ENRICH_PATTERNS):
        return "enrich"

    # trace
    if any(kw in q for kw in _TRACE_PATTERNS):
        return "trace"

    # analyze
    if any(kw in q for kw in _ANALYZE_PATTERNS):
        return "analyze"

    return "answer"


def _calculate_confidence(question: str, mode: str, targets: list[dict[str, str]]) -> float:
    """Calculate confidence score 0-1 based on signal strength."""
    score = 0.7  # base confidence

    # Target match boosts
    if targets:
        score += 0.15
        if _has_multiple_targets(targets):
            score += 0.05

    # Keyword match density
    keywords = {"trace": _TRACE_PATTERNS, "analyze": _ANALYZE_PATTERNS, "enrich": _ENRICH_PATTERNS}
    pattern_list = keywords.get(mode, [])
    matches = sum(1 for kw in pattern_list if kw in question)
    if matches >= 2:
        score += 0.05
    if matches >= 3:
        score += 0.03

    # Question length — very short questions are ambiguous
    if len(question) < 8:
        score -= 0.15
    elif len(question) < 15:
        score -= 0.05

    # Question ending with question mark is natural for answer mode
    if mode == "answer" and any(question.endswith(p) for p in ["？", "?", "。", "."]):
        score += 0.05

    return round(min(score, 0.99), 2)


def _generate_warnings(
    question: str, mode: str, targets: list[dict[str, str]], confidence: float
) -> list[str]:
    """Generate user-facing warnings about the plan."""
    warnings: list[str] = []
    if not targets:
        warnings.append("问题中未识别到已知人物/物件/设定，使用问题文字截取作为目标。")
    if confidence < 0.6:
        warnings.append(f"意图判断置信度较低（{confidence:.0%}），建议在运行前确认模式是否正确。")
    if len(question) < 10:
        warnings.append("问题较短，可能需要补充更多上下文。")
    if mode == "answer" and _count_entity_mentions(question) >= 2:
        warnings.append("问题包含多个人物/设定，可能更适合 analyze 或 trace 模式。")
    return warnings


# ── question optimization ─────────────────────────────────────────────
def _optimize_question(
    question: str, mode: str, book_title: str,
    targets: list[dict[str, str]],
) -> str:
    """Rewrite the user's question into a retrieval-friendly prompt."""
    target_text = ", ".join(t["name"] for t in targets) if targets else ""
    if not target_text:
        target_text = _extract_fallback_target(question, 0)

    # Note: we use _find_targets but discard book_id for fallback — OK because
    # fallback target only needs to know which book catalog's title to use.
    # If no targets matched, pull from the generic logic.
    relation_like = any(rp in question for rp in _RELATION_PATTERNS)
    multi_target = _has_multiple_targets(targets)

    if mode == "trace":
        if relation_like and (multi_target or any("关系" in question for _ in [1])):
            return (
                f"请按章节时间线追踪{target_text}的关系变化，"
                "概括关键阶段、变化原因和证据局限。"
            )
        return (
            f"请按章节时间线追踪{target_text}在《{book_title}》中的出现、"
            "作用变化和证据局限。"
        )

    if mode == "analyze":
        if relation_like or (_has_multiple_targets(targets) and len(targets) <= 2):
            return (
                f"请基于证据分析{target_text}的关系："
                "先给综合判断，再说明关系性质、关键冲突或合作、证据局限。"
            )
        return (
            f"请基于证据分析{target_text}的人物形象："
            "先给综合判断，再列出3-5条关键结论和证据局限。"
        )

    if mode == "enrich":
        if target_text:
            return (
                f"请基于已有证据为{target_text}生成一个低风险 KnowledgePatch 候选，"
                "不自动合并。"
            )
        return (
            "请基于已有证据生成一个低风险 KnowledgePatch 候选，不自动合并。"
        )

    # answer mode
    return f"请基于《{book_title}》的已检索证据，直接、简洁地回答：{question}"


# ── target type inference ─────────────────────────────────────────────
def _infer_target_type(
    targets: list[dict[str, str]], mode: str, question: str,
) -> tuple[str, str | None]:
    """Return (target_type, trace_target_type_or_analysis_type).

    target_type: character / relation / item / setting
    second: trace_target_type (character/item/setting) or analysis_type (character/relation)
    """
    if not targets:
        return ("character", "character")

    types_present = {t["type"] for t in targets}
    relation_like = any(rp in question for rp in _RELATION_PATTERNS)

    # Multiple targets + relation keywords → relation
    if _has_multiple_targets(targets) and relation_like:
        return ("relation", "character")

    # Single target — use its type
    single_type = targets[0]["type"]

    if mode == "analyze":
        if relation_like:
            return ("relation", "relation")
        return (single_type, "character")

    if mode == "trace":
        if relation_like and _has_multiple_targets(targets):
            return ("relation", "character")
        # If item/setting, use as-is
        trace_type = single_type if single_type in ("item", "setting") else "character"
        return (single_type, trace_type)

    return (single_type, None)


def _build_target_name(targets: list[dict[str, str]], question: str) -> str:
    if targets:
        return ", ".join(t["name"] for t in targets)
    return _extract_fallback_target(question, 0)


# ── public planner ────────────────────────────────────────────────────
def plan(
    book_id: int,
    question: str,
    preferred_mode: str = "auto",
    session: SessionContext = None,
) -> PlanResponse:
    """Deterministic planner: infer mode, targets, rewrite question.

    Args:
        book_id: Book ID (6-10 currently supported).
        question: User's natural-language question.
        preferred_mode: "auto" or an explicit mode.
        session: Optional session context (SessionMemory or old SessionState)
                for follow-up reference resolution and book context carryover.

    Returns:
        PlanResponse with mode, optimized_question, targets, confidence, etc.
    """
    # Resolve session-based references for follow-up questions
    resolved_question, mode_override = resolve_question(question, session)
    question = resolved_question
    if mode_override and preferred_mode == "auto":
        preferred_mode = mode_override

    # If session has a current book_id and no explicit book match,
    # prefer session book context
    resolved_book_id = book_id
    if session and session.book_id:
        resolved_book_id = session.book_id

    book = BOOK_CATALOG.get(resolved_book_id, BOOK_CATALOG[6])
    book_title = book["title"]

    # 1. Find known targets
    targets = _find_targets(resolved_book_id, question)

    # 2. Infer mode
    if preferred_mode and preferred_mode != "auto":
        mode = preferred_mode
    else:
        mode = _infer_mode(question)

    # 3. Calculate confidence
    confidence = _calculate_confidence(question, mode, targets)

    # 4. Generate warnings
    warnings = _generate_warnings(question, mode, targets, confidence)

    # 5. Infer target types
    target_type, secondary_type = _infer_target_type(targets, mode, question)

    # 6. Build target name
    target_name = _build_target_name(targets, question)

    # 7. Optimize question
    optimized_question = _optimize_question(question, mode, book_title, targets)

    # 7b. Prepend session context if available — uses MemoryManager L0
    #     (e.g., "我刚问的是什么" → model sees last question + answer)
    if session and session.turns and session.last_turn:
        last = session.last_turn
        if last.question and last.question != question:
            ctx = f"上一轮问题：{last.question}"
            if last.answer_preview:
                ctx += f" | 上一轮回答：{last.answer_preview[:200]}"
            optimized_question = f"[上下文] {ctx} | 当前问题：{question}"

    # 8. Build request patch for frontend merge
    analysis_type: str | None = None
    trace_target_type: str | None = None
    if mode == "analyze":
        analysis_type = secondary_type or "character"
    elif mode == "trace":
        trace_target_type = secondary_type or "character"

    patch = PlanRequestPatch(
        mode=mode,
        question=optimized_question,
        target_name=target_name,
        target_type=target_type,
        analysis_type=analysis_type,
        trace_target_type=trace_target_type,
    )

    # 9. Clarification
    clarification: str | None = None
    clarification_options: list[str] | None = None
    if confidence < 0.5:
        clarification = f"未确定你的意图（置信度 {confidence:.0%}），暂时按「{mode}」模式处理。如结果不理想，请补充更多上下文。"
    elif confidence < 0.6 and not targets:
        clarification = "问题中未识别到已知目标，已选择最匹配的模式。需要我尝试其他模式吗？"
        clarification_options = ["继续", "换成追踪", "换成分析"]

    # 10. Build tool execution sequence
    tool_sequence = _build_tool_sequence(
        mode=mode,
        question=optimized_question,
        book_id=resolved_book_id,
        target_name=target_name,
        target_type=target_type,
        analysis_type=analysis_type,
        trace_target_type=trace_target_type,
    )

    # 11. Build response
    return PlanResponse(
        mode=mode,
        optimized_question=optimized_question,
        target_name=target_name,
        target_type=target_type,
        analysis_type=analysis_type,
        trace_target_type=trace_target_type,
        confidence=confidence,
        reason=_build_reason(mode, targets, question),
        warnings=warnings,
        clarification=clarification,
        clarification_options=clarification_options,
        request_patch=patch,
        tool_sequence=tool_sequence,
    )


def _build_tool_sequence(
    mode: str,
    question: str,
    book_id: int,
    target_name: str,
    target_type: str,
    analysis_type: str | None,
    trace_target_type: str | None,
) -> list[ToolCallStep]:
    """Build a tool execution sequence from the plan.

    Every mode becomes a tool call, with preceding retrieval if needed.
    """
    steps: list[ToolCallStep] = []

    # All tasks start with hybrid_search to gather evidence
    steps.append(ToolCallStep(
        tool_name="hybrid_search",
        params={
            "query": question,
            "book_id": book_id,
            "top_k": 12,
        },
        description="检索相关章节和事实证据",
        fallback_tool=None,
    ))

    # Main execution tool
    tool_params: dict[str, str | int | None] = {
        "question": question,
        "book_id": book_id,
        "target_name": target_name,
        "target_type": target_type,
    }
    if analysis_type:
        tool_params["analysis_type"] = analysis_type
    if trace_target_type:
        tool_params["trace_target_type"] = trace_target_type

    steps.append(ToolCallStep(
        tool_name=mode,
        params=tool_params,
        description={"answer": "基于证据回答问题",
                     "analyze": "结构化分析人物/关系",
                     "trace": "按章节时间线追踪",
                     "enrich": "生成 KnowledgePatch 候选"}.get(mode, f"执行 {mode}"),
        fallback_tool=None,
    ))

    # Audit step - always run after answer
    steps.append(ToolCallStep(
        tool_name="audit",
        params={"provider": "local"},
        description="检查输出格式和潜在问题",
        fallback_tool=None,
    ))

    return steps


def _build_reason(mode: str, targets: list[dict[str, str]], question: str) -> str:
    """Generate a human-readable reason for the mode choice."""
    reasons = {
        "answer": "问题更像普通解释或结论问答，适合证据问答。",
        "analyze": "问题包含分析、形象、关系或特点意图，适合结构化分析。",
        "trace": "问题包含追踪、变化、线索或阶段意图，适合 timeline 输出。",
        "enrich": "问题指向知识库修正或反哺，适合生成候选补丁。",
    }
    reason = reasons.get(mode, reasons["answer"])

    if targets:
        names = "、".join(t["name"] for t in targets)
        reason += f" 目标：{names}。"

    return reason
