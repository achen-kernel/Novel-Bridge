"""@NB-ENTRYPOINT Intent detector — uses LLM to classify user input.

Instead of hardcoded patterns, calls a lightweight model prompt to decide:
- book_qa → full retrieval pipeline
- greeting / chat → direct model response
- gibberish → polite redirect

The model is better at this than regex because it understands semantics.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

logger = logging.getLogger(__name__)

IntentCategory = Literal["book_qa", "greeting", "chat", "gibberish"]

_CLASSIFY_PROMPT = """判断用户输入属于哪一类，只输出 JSON：

{"intent": "book_qa|greeting|chat|gibberish", "reason": "简短原因"}

分类规则：
- book_qa: 关于古典小说（西游记/水浒传/山海经/聊斋/搜神记）的具体问题、人物分析、情节追踪、主题探讨
- greeting: 问候、打招呼、告别、感谢
- chat: 闲聊、非小说类的一般对话、日常话题
- gibberish: 无意义输入、乱码、纯符号

输入：{query}
"""


async def detect(
    query: str,
    book_id: int | None = None,
    provider: str = "local",
    session_context: str | None = None,
) -> tuple[IntentCategory, str | None]:
    """Detect intent using LLM.

    Args:
        query: User input.
        book_id: Current book ID (optional, for context).
        provider: "local" or "deepseek".
        session_context: Recent conversation turns (for context-aware chat responses).

    Returns:
        (category, response_override):
        - category: detected intent
        - response_override: if chat/greeting, a model-generated response.
          None for book_qa (caller should run QA pipeline).
    """
    if not query or not query.strip():
        return ("gibberish", "请输入内容。")

    # Try DeepSeek first, fallback to local
    try:
        result = await _classify_with_model(query, provider="deepseek")
        if result:
            intent = result.get("intent", "book_qa")
            if intent == "book_qa":
                return ("book_qa", None)
            response = await _generate_response(query, intent, provider="deepseek", session_context=session_context)
            return (intent, response)
    except Exception as e:
        logger.warning("DeepSeek intent detection failed, trying local: %s", e)

    try:
        result = await _classify_with_model(query, provider="local")
        if result:
            intent = result.get("intent", "book_qa")
            if intent == "book_qa":
                return ("book_qa", None)
            response = await _generate_response(query, intent, provider="local", session_context=session_context)
            return (intent, response)
    except Exception as e:
        logger.warning("Local intent detection failed: %s", e)

    # Ultimate fallback: treat as book_qa
    return ("book_qa", None)


async def _classify_with_model(query: str, provider: str) -> dict | None:
    """Call model to classify intent. Returns parsed JSON or None."""
    prompt = _CLASSIFY_PROMPT.format(query=query[:200])

    try:
        if provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            text = await deepseek_client.chat(
                messages=[
                    {"role": "system", "content": "你是分类器。只输出 JSON，不要其他文字。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.05,
                max_tokens=200,
            )
        else:
            from app.clients.llama_cpp_client import llama_client
            text = await llama_client.chat(
                messages=[
                    {"role": "system", "content": "你是分类器。只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.05,
                max_tokens=200,
            )

        if not text:
            return None

        text = text.strip()
        # Clean potential markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        data = json.loads(text)
        if isinstance(data, dict) and data.get("intent") in ("book_qa", "greeting", "chat", "gibberish"):
            return data
        return None
    except Exception as e:
        logger.debug("Model classification failed: %s", str(e)[:80])
        return None


async def _generate_response(query: str, intent: str, provider: str, session_context: str | None = None) -> str:
    """Generate a natural response for non-book-qa inputs.

    Includes session context when available so the model can reference
    previous conversation turns (e.g., "我之前都问了什么").
    """
    ctx_hint = ""
    if session_context:
        ctx_hint = f"\n\n对话历史（最近几轮）：\n{session_context[:500]}"

    system_prompts = {
        "greeting": "你是 NovelBridge 阅读智能体。用户向你打招呼，请友好回应并引导ta问小说问题。简短自然，30字以内。" + ctx_hint,
        "chat": "你是 NovelBridge 阅读智能体。用户在闲聊，请简短友好回应，可以引用对话历史。引导ta问古典小说问题。" + ctx_hint,
        "gibberish": "你是 NovelBridge 阅读智能体。用户输入无意义内容，请礼貌提示ta输入小说相关问题。简洁。" + ctx_hint,
    }
    system_prompt = system_prompts.get(intent, "简短友好回应。")

    try:
        if provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            text = await deepseek_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.6,
                max_tokens=200,
            )
        else:
            from app.clients.llama_cpp_client import llama_client
            text = await llama_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.6,
                max_tokens=200,
            )
        return text.strip() if text else "你好！我是 NovelBridge 阅读智能体。"
    except Exception:
        return "你好！我是 NovelBridge 阅读智能体，可以问我关于古典小说的问题。"
