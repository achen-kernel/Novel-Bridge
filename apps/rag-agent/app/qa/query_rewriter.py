"""@NB-ENTRYPOINT P1 QueryRewriter — DeepSeek-based query rewrite for retrieval.

Transforms raw user questions into retrieval-friendly queries.
Replaces the old n-gram keyword extraction + scattered abstract rewrite.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.clients.deepseek_client import deepseek_client

logger = logging.getLogger(__name__)

IntentType = Literal["factual", "relation_analysis", "trace_timeline", "abstract_meaning", "enumeration"]
StrategyType = Literal["precise", "broad", "timeline"]


class RewriteRequest(BaseModel):
    question: str
    book_id: int
    book_title: str = ""
    entities: list[str] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)  # recent Q&A
    previous_fail: bool = False  # True = retry with broader query


class RewriteResult(BaseModel):
    rewritten_query: str
    intent: IntentType = "factual"
    explicit_entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    strategy: StrategyType = "precise"


# Book names for context
_BOOK_NAMES = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}


async def rewrite(req: RewriteRequest) -> RewriteResult:
    """Rewrite a user question into a retrieval-friendly query using DeepSeek.

    Falls back to identity (returns original question as-is) when:
    - DeepSeek API is unavailable
    - DeepSeek returns invalid JSON
    - Any exception occurs
    """
    try:
        return await _rewrite_deepseek(req)
    except Exception as e:
        logger.warning("QueryRewriter fallback to identity: %s", e)
        return _fallback(req)


async def _rewrite_deepseek(req: RewriteRequest) -> RewriteResult:
    """Core DeepSeek-based rewrite."""
    book_title = req.book_title or _BOOK_NAMES.get(req.book_id, f"Book {req.book_id}")

    history_text = ""
    if req.history:
        turns = []
        for h in req.history[-2:]:  # last 2 turns
            role = "用户" if h.get("role") == "user" else "助手"
            content = (h.get("content") or "")[:100]
            turns.append(f"{role}: {content}")
        history_text = "\n对话历史：\n" + "\n".join(turns)

    entities_text = f"已知实体：{'、'.join(req.entities)}" if req.entities else "已知实体：无"
    fail_hint = "\n（上次检索未找到足够结果，请用更宽泛的关键词重写）" if req.previous_fail else ""

    prompt = f"""你是小说检索查询改写器。将用户的自然语言问题改写成适合 dense + lexical 混合检索的查询。

书：《{book_title}》
{entities_text}
{history_text}
当前问题：{req.question}{fail_hint}

输出 JSON（纯 JSON，无其他文字）：
{{
  "rewritten_query": "补全实体名、去除废话、明确意图的检索词串，空格分隔",
  "intent": "factual|relation_analysis|trace_timeline|abstract_meaning|enumeration",
  "explicit_entities": ["补全别名后的实体名列表"],
  "keywords": ["其他重要检索词"],
  "strategy": "precise|broad|timeline"
}}

规则：
- 人物简称补全："悟空"→"孙悟空"，"三藏"→"唐僧"
- 抽象词替换为具体事件词："道理"→"教训 事件 结局"，"精神"→"品质 行动"
- 多实体关系问句改写为："{A} {B} 关系 冲突 合作"
- 时间线追踪问句保留关键阶段词
- 统计类问题保留数字要求（"多少""几个"）
- 如果 previous_fail=true，用更宽泛的关键词
"""

    text = await deepseek_client.chat(
        messages=[
            {"role": "system", "content": "你是小说检索查询改写器。只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=600,
    )

    if not text:
        return _fallback(req)

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    data = json.loads(text)
    if not isinstance(data, dict):
        return _fallback(req)

    intent = data.get("intent", "factual")
    if intent not in ("factual", "relation_analysis", "trace_timeline", "abstract_meaning", "enumeration"):
        intent = "factual"

    strategy = data.get("strategy", "precise")
    if strategy not in ("precise", "broad", "timeline"):
        strategy = "precise"

    return RewriteResult(
        rewritten_query=str(data.get("rewritten_query", req.question)),
        intent=intent,
        explicit_entities=[str(e) for e in (data.get("explicit_entities") or [])],
        keywords=[str(k) for k in (data.get("keywords") or [])],
        strategy=strategy,
    )


def _fallback(req: RewriteRequest) -> RewriteResult:
    """Fallback: return original question as-is."""
    return RewriteResult(
        rewritten_query=req.question,
        intent="factual",
        explicit_entities=list(req.entities),
        keywords=[],
        strategy="precise",
    )
