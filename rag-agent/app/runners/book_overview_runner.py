"""
Book overview runner — asks the model to analyze book structure before splitting.

Sends the first ~8000 chars of the book to the model, gets back:
- structure_type (CHAPTER/HUI/STORY/SECTION/NONE)
- book_summary
- main_sections
- entity hints for later extraction
"""

import json
import os
import logging

from app.clients.llama_cpp_client import LlamaCppClient
from app.clients.mysql_client import MySQLClient

logger = logging.getLogger("rag-agent.overview")
PROMPT_VERSION = "book_overview_v0_1"
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

OVERVIEW_CHARS = 6000  # 填满 8K 上下文：结构检测 + 开篇梗概


def _load_prompt_template() -> str:
    path = os.path.join(PROMPT_DIR, "book_overview_v0_1.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return """分析书籍结构。structure_type: CHAPTER/HUI/STORY/SECTION/NONE"""


def generate_book_overview(book_source: dict, llm: LlamaCppClient, db: MySQLClient) -> dict:
    """
    Call the model to generate a book overview and structure analysis.
    Saves result to novel_book_source.book_overview.
    Returns the parsed overview dict.
    """
    book_source_id = book_source["id"]
    raw_text = book_source.get("raw_text", "")
    title = book_source.get("title", "")
    author = book_source.get("author", "")

    # Take first OVERVIEW_CHARS chars
    text_start = raw_text[:OVERVIEW_CHARS]

    template = _load_prompt_template()
    # 使用 replace 而不是 format，避免 prompt 中的 {} 被误解析
    user_content = template.replace("{book_title}", title or "未知")\
                           .replace("{author}", author or "未知")\
                           .replace("{text_start}", text_start)

    messages = [
        {"role": "system", "content": "你是一个小说结构分析器。分析输入文本的结构类型和内容概览。只输出 JSON，不要多余文字。"},
        {"role": "user", "content": user_content},
    ]

    logger.info(f"[overview #{book_source_id}] Calling LLM for book overview...")
    response = llm.chat_completion(
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
        # 不使用 response_format schema（大 prompt 下返回空），靠 prompt 保证 JSON 输出
    )

    output_text = llm.extract_text(response)
    duration_ms = response.get("_duration_ms", 0)
    logger.info(f"[overview #{book_source_id}] LLM responded in {duration_ms}ms")

    # Parse JSON
    try:
        overview = json.loads(output_text)
    except json.JSONDecodeError as e:
        logger.warning(f"[overview #{book_source_id}] JSON parse failed: {e}")
        overview = {
            "structure_type": "NONE",
            "confidence": 0.0,
            "description": f"LLM output parse failed: {e}",
            "book_summary": "",
            "main_sections": [],
            "notable_entities": [],
            "entity_hints": [],
        }

    # Save to DB
    overview_json = json.dumps(overview, ensure_ascii=False)
    db.update(
        "UPDATE novel_book_source SET book_overview = %s WHERE id = %s",
        (overview_json, book_source_id),
    )

    # Update chapter_split_runner confidence for structure_type
    logger.info(f"[overview #{book_source_id}] Structure: {overview.get('structure_type')} "
                f"(confidence={overview.get('confidence')})")
    logger.info(f"[overview #{book_source_id}] Summary: {overview.get('book_summary', '')[:100]}")

    return overview
