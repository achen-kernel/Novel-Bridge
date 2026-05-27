"""@NB-ENTRYPOINT Stage 6F reference resolver for follow-up questions.

Resolves pronoun references ("他", "她", "它", "这关系", "那条线索", etc.)
using the current session context.

Pure function — no model calls, no DB reads.
Uses deterministic rules over session state.
"""

from __future__ import annotations

import re

from app.reader_agent.memory.session_memory import SessionMemory

SessionContext = SessionMemory | None

# Pronouns that might refer to the current target
_TARGET_PRONOUNS = {"他", "她", "它", "他们", "她们", "它们", "这个人", "这个人物", "该角色", "该人物", "这位", "该人"}

# Reference patterns where resolution needs context
_RELATION_REF = {"这关系", "这段关系", "他们的关系", "他们的矛盾", "他们的互动", "其关系", "他俩", "他们俩"}
_TRACE_REF = {"这条线索", "这个线索", "这个变化", "这个发展", "该线索", "该变化", "这条线", "这个走向"}
_ANSWER_REF = {"这个回答", "这个结论", "刚才的说法", "上述分析", "你的回答", "你刚才说的"}
_EVIDENCE_REF = {"这个证据", "这些证据", "那几条证据", "刚才的证据", "你引用的"}
_MODE_REF = {"换成时间线", "改为追踪", "详细分析", "简单回答", "换一种说法", "换个角度", "继续说", "展开说说"}
_PREV_QUESTION_REF = {"我刚问", "我刚刚问", "我问的是什么", "我上一轮", "刚才的问题", "之前的问题", "第一个问题", "最开始的问题"}


def resolve_question(
    question: str,
    session: SessionContext,
) -> tuple[str, str | None]:
    """Resolve a follow-up question using session context.

    Args:
        question: The user's new question.
        session: Current session state, or None.

    Returns:
        (resolved_question, suggested_mode_override):
        - resolved_question: question with references replaced.
        - suggested_mode_override: "answer"/"analyze"/"trace"/"enrich" or None.
    """
    if not session or not session.turns:
        return question, None

    last = session.last_turn
    if not last:
        return question, None

    resolved = question
    mode_override: str | None = None

    # 1. Mode change requests
    if any(kw in question for kw in _MODE_REF):
        if any(kw in question for kw in ("时间线", "追踪", "线索", "发展")):
            mode_override = "trace"
        elif any(kw in question for kw in ("分析", "形象", "性格")):
            mode_override = "analyze"
        elif any(kw in question for kw in ("证据", "citation", "补丁", "补充")):
            mode_override = "enrich"
        # "详细回答" or "简单回答" → keep current mode

    # 2. Pronoun → current target
    if _has_pronouns(question, _TARGET_PRONOUNS) and session.current_target_name:
        resolved = _replace_pronouns(resolved, _TARGET_PRONOUNS, session.current_target_name)

    # 3. Relation reference → current target (likely two entities)
    if any(ref in question for ref in _RELATION_REF) and session.current_target_name:
        resolved = resolved.replace("这关系", f"{session.current_target_name}的关系")
        resolved = resolved.replace("这段关系", f"{session.current_target_name}的关系")
        resolved = resolved.replace("他们的关系", f"{session.current_target_name}的关系")
        if "关系" in question and mode_override is None:
            mode_override = "analyze"

    # 4. Trace/evidence reference → carry over to current question
    if any(ref in question for ref in _TRACE_REF) and session.current_target_name:
        resolved = resolved.replace("这条线索", f"{session.current_target_name}的线索")

    # 5. Book reference — no book keyword → carry last book
    # (handled by planner falling back to session's book_id)

    # 6. "我刚问的是什么" / "最开始的问题" → reference previous question
    if any(kw in question for kw in _PREV_QUESTION_REF):
        # Find first question in session
        first_q = session.turns[0].question if session.turns else ""
        if "最开始" in question and first_q:
            resolved = f"请基于上下文复述第一个问题「{first_q}」的相关信息"
        else:
            resolved = f"请基于上下文复述上一轮的问题「{last.question}」以及相关信息"
        if mode_override is None:
            mode_override = "answer"

    # 7. Empty/very short follow-up → use last context
    if len(resolved.strip()) < 4 and session.current_target_name:
        resolved = f"关于{session.current_target_name}：{resolved}"

    return resolved, mode_override


def _has_pronouns(text: str, pronouns: set[str]) -> bool:
    for p in pronouns:
        if p in text:
            return True
    return False


def _replace_pronouns(text: str, pronouns: set[str], replacement: str) -> str:
    """Replace standalone pronouns with the replacement text."""
    for p in pronouns:
        text = text.replace(p, replacement)
    return text
