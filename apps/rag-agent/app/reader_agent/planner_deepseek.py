"""@NB-ENTRYPOINT P1 model-based planner using DeepSeek.

Provides an alternative to the deterministic planner for complex/ambiguous queries.
Falls back to deterministic planner when DeepSeek is unavailable or returns
invalid output.

Usage:
    plan = await plan_with_deepseek(book_id=6, question="看看宋江这个人")
    deterministic_plan = plan(book_id=6, question="...")  # fallback
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.clients.deepseek_client import deepseek_client
from app.reader_agent.planner import BOOK_CATALOG, plan as deterministic_plan
from app.reader_agent.schemas import PlanResponse, PlanRequestPatch

logger = logging.getLogger(__name__)

_MODE_DESCRIPTIONS = """
- answer: 证据问答。用户问"为什么""是什么""如何"。返回直接回答+引用。
- analyze: 结构化分析。用户说"分析XXX的人物形象/性格/关系"。返回结构化分析。
- trace: 跨章节追踪。用户说"追踪/时间线/线索/变化"。返回 timeline。
- enrich: 知识库反哺候选。用户说"修正/补充知识库/KnowledgePatch"。返回 candidate。
"""


async def plan_with_deepseek(
    book_id: int,
    question: str,
    preferred_mode: str = "auto",
    session_summary: str | None = None,
) -> PlanResponse | None:
    """Call DeepSeek to produce a PlanResponse.

    Returns None if DeepSeek fails or returns invalid JSON,
    so the caller can fall back to deterministic planner.

    The DeepSeek planner is optional — the system works without it.
    """
    book = BOOK_CATALOG.get(book_id, BOOK_CATALOG[6])
    book_title = book["title"]

    mode_instruction = ""
    if preferred_mode and preferred_mode != "auto":
        mode_instruction = f"用户指定了模式：{preferred_mode}，请使用该模式。"

    session_context = ""
    if session_summary:
        session_context = f"会话上下文：{session_summary}\n"

    prompt = f"""你是一个小说阅读分析系统的意图识别器。你的任务是分析用户的问题，确定最佳处理模式。

当前书籍：{book_title}
用户问题：{question}
{session_context}{mode_instruction}

可用模式：
{_MODE_DESCRIPTIONS}

输出 JSON（不要含 markdown 代码块标记，只输出纯 JSON）：
{{
  "mode": "answer|analyze|trace|enrich",
  "optimized_question": "改写后的检索友好问题",
  "target_name": "目标人物/物件/设定名称，多个用逗号分隔",
  "target_type": "character|relation|item|setting",
  "analysis_type": "character|relation 或 null",
  "trace_target_type": "character|item|setting 或 null",
  "confidence": 0.0-1.0,
  "reason": "简短的中文解释为什么选择这个模式"
}}

规则：
- 如果问题模糊、缺少目标，设置 confidence < 0.5 并填上 best guess。
- optimized_question 应该改写为清晰的检索问句。
- 坚决不输出 JSON 之外的文字。
- target_type 是 relation 时，trace_target_type 填 character。
"""
    try:
        text = await deepseek_client.chat(
            messages=[
                {"role": "system", "content": "你是小说分析意图识别器。只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        if not text or not text.strip():
            logger.warning("DeepSeek planner returned empty response")
            return None

        # Clean potential markdown code fences
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)
        if not isinstance(data, dict):
            return None

        mode = data.get("mode", "answer")
        if mode not in ("answer", "analyze", "trace", "enrich"):
            mode = "answer"

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        target_name = str(data.get("target_name", "") or "")
        target_type = str(data.get("target_type", "character") or "character")
        analysis_type = data.get("analysis_type")
        trace_target_type = data.get("trace_target_type")

        # Build patch and tool sequence using deterministic helpers
        patch = PlanRequestPatch(
            mode=mode,
            question=data.get("optimized_question", question),
            target_name=target_name,
            target_type=target_type,
            analysis_type=analysis_type,
            trace_target_type=trace_target_type,
        )

        # Use deterministic planner to fill in tool_sequence
        fallback = deterministic_plan(book_id=book_id, question=question)
        tool_sequence = fallback.tool_sequence
        # Update tool params with model-based values
        for step in tool_sequence:
            if step.tool_name == mode:
                step.params["target_name"] = target_name
                step.params["target_type"] = target_type

        return PlanResponse(
            mode=mode,
            optimized_question=data.get("optimized_question", question),
            target_name=target_name,
            target_type=target_type,
            analysis_type=analysis_type,
            trace_target_type=trace_target_type,
            confidence=confidence,
            reason=data.get("reason", "DeepSeek planner"),
            warnings=[],
            clarification=None,
            request_patch=patch,
            tool_sequence=tool_sequence,
        )

    except json.JSONDecodeError as e:
        logger.warning("DeepSeek planner JSON decode error: %s — raw=%r", e, text[:200] if 'text' in dir() else '')
        return None
    except Exception as e:
        logger.warning("DeepSeek planner failed: %s", e)
        return None
