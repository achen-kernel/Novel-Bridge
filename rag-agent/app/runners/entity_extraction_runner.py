"""
Entity extraction runner.

Processes a single chunk through llama.cpp:
1. Load prompt template
2. Construct full prompt with chunk context
3. Call llama-server
4. Parse and validate output
5. Save model_run trace
6. Generate entity candidates
7. Evidence-check each candidate
"""

import os
import json
import time
import traceback
from typing import Optional

from app.clients.llama_cpp_client import LlamaCppClient
from app.stores.model_run_store import ModelRunStore
from app.stores.candidate_store import CandidateStore
from app.validators.extraction_validator import parse_and_validate
from app.validators.evidence_validator import validate_evidence_list

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
PROMPT_VERSION = "entity_extract_v0_1"
MODEL_NAME = os.getenv("NB_MODEL_NAME", "Qwen3.6-35B-A3B")

# Maximum retries for failed extractions
MAX_RETRIES = 2


def _load_prompt_template() -> str:
    """Load the entity extraction prompt template."""
    path = os.path.join(PROMPT_DIR, "entity_extract_v0_1.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback minimal prompt
    return """任务：从小说片段中抽取实体候选。

规则：
1. 只抽取当前片段中明确出现的实体。
2. evidence_text 必须是原文中的短句。
3. confidence 范围为 0 到 1。
4. 不确定时 uncertain=true。

输入：
{chunk_text}
"""


def _build_prompt(chunk_text: str, chunk_id: int, chapter_id: int = 0,
                  chapter_title: str = "", book_title: str = "") -> list:
    """Build the OpenAI-style messages list for entity extraction."""
    template = _load_prompt_template()
    user_content = template.format(
        book_title=book_title or "未知书籍",
        chapter_id=chapter_id or 0,
        chapter_title=chapter_title or "",
        chunk_id=chunk_id or 0,
        chunk_text=chunk_text,
    )
    return [
        {"role": "system", "content": "你是一个小说知识抽取器。你只能基于给定片段抽取实体。"},
        {"role": "user", "content": user_content},
    ]


def _build_json_schema() -> dict:
    """Build response_format json_schema for entity extraction."""
    return {
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "chapter_id": {"type": "integer"},
                "chunk_id": {"type": "integer"},
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["CHARACTER", "LOCATION", "ITEM", "ORG", "TITLE", "UNKNOWN"]
                            },
                            "aliases": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "description": {"type": "string"},
                            "evidence_text": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "uncertain": {"type": "boolean"}
                        },
                        "required": ["name", "type", "evidence_text", "confidence"]
                    }
                },
                "uncertain_items": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["chapter_id", "chunk_id", "entities"]
        }
    }


def extract_entities_from_chunk(
    chunk: dict,
    book_source: dict,
    llm: LlamaCppClient,
    model_run_store: ModelRunStore,
    candidate_store: CandidateStore,
) -> dict:
    """
    Run entity extraction on a single chunk.

    Args:
        chunk: novel_chunk record dict.
        book_source: novel_book_source record dict (for book title).
        llm: LlamaCppClient instance.
        model_run_store: ModelRunStore instance.
        candidate_store: CandidateStore instance.

    Returns:
        dict with keys: status, model_run_id, candidate_count, errors
    """
    result = {
        "status": "FAILED",
        "model_run_id": None,
        "candidate_count": 0,
        "errors": [],
    }

    chunk_text = chunk.get("content", "")
    chunk_id = chunk["id"]
    chapter_id = chunk.get("chapter_id", 0)
    book_source_id = chunk.get("book_source_id", 0)
    book_id = chunk.get("book_id", 0)
    book_title = book_source.get("title", "") if book_source else ""

    if not chunk_text.strip():
        result["errors"].append("Empty chunk text")
        return result

    # Build prompt
    messages = _build_prompt(
        chunk_text=chunk_text,
        chunk_id=chunk_id,
        chapter_id=chapter_id,
        book_title=book_title,
    )
    schema = _build_json_schema()
    prompt_text = json.dumps(messages, ensure_ascii=False)

    # Insert initial model_run record
    model_run_id = model_run_store.insert(
        task_type="ENTITY_EXTRACT",
        model_name=MODEL_NAME,
        model_endpoint=f"{llm.base_url}/v1/chat/completions",
        book_source_id=book_source_id,
        book_id=book_id,
        chapter_id=chapter_id,
        chunk_id=chunk_id,
        prompt_version=PROMPT_VERSION,
        schema_version="entity_json_schema_v0.1",
        grammar_version="",
        input_text=prompt_text,
        status="RUNNING",
    )
    result["model_run_id"] = model_run_id

    # Extraction loop with retry
    duration_ms = 0
    final_output = ""
    parse_ok = False
    parse_error = ""
    validated_entities = []
    evidence_missing = []

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = llm.chat_completion(
                messages=messages,
                temperature=0.1 if attempt > 0 else 0.3,
                max_tokens=2048,
                response_format=schema,
            )
            duration_ms = response.get("_duration_ms", 0)
            final_output = llm.extract_text(response)

            if response.get("_status_code") != 200:
                parse_error = f"API error (status {response.get('_status_code')}): {final_output[:200]}"
                if attempt < MAX_RETRIES:
                    continue
                break

            # Parse and validate
            validation = parse_and_validate(final_output)
            if not validation.ok:
                parse_error = "; ".join(validation.errors[:5])
                parse_ok = False
                if attempt < MAX_RETRIES:
                    continue
                break

            # Evidence check
            evidence_missing = validate_evidence_list(validation.entities, chunk_text)
            for ent in validation.entities:
                if ent.get("evidence_text", "") not in evidence_missing:
                    validated_entities.append(ent)

            if evidence_missing:
                parse_error = f"Evidence not found for: {evidence_missing}"
                # Still accept entities that have valid evidence
                if not validated_entities and attempt < MAX_RETRIES:
                    continue

            parse_ok = True
            break

        except Exception as e:
            parse_error = f"Exception: {traceback.format_exc()[:300]}"
            if attempt < MAX_RETRIES:
                continue
            break

    # Update model_run record
    final_status = "SUCCESS" if parse_ok else "FAILED"
    model_run_store.update_status(
        model_run_id,
        status=final_status,
        parse_status="OK" if parse_ok else "FAILED",
        error_type="PARSE_ERROR" if not parse_ok else "",
        error_message=parse_error if not parse_ok else "",
    )
    # Update output text
    from app.clients.mysql_client import MySQLClient
    db = MySQLClient()
    db.update(
        "UPDATE novel_model_run SET output_text = %s, duration_ms = %s WHERE id = %s",
        (final_output, duration_ms, model_run_id),
    )

    if not parse_ok:
        result["errors"].append(parse_error)
        return result

    # Save candidates
    candidate_count = 0
    for ent in validated_entities:
        try:
            cand_id = candidate_store.insert(
                book_source_id=book_source_id,
                book_id=book_id,
                chapter_id=chapter_id,
                chunk_id=chunk_id,
                model_run_id=model_run_id,
                name=ent["name"],
                entity_type=ent.get("type", "UNKNOWN"),
                evidence_text=ent.get("evidence_text", ""),
                confidence=ent.get("confidence", 0.0),
                uncertain=ent.get("uncertain", False),
                aliases=ent.get("aliases", []),
                description=ent.get("description", ""),
            )
            candidate_count += 1
        except Exception as e:
            result["errors"].append(f"Failed to save candidate '{ent.get('name', '')}': {e}")

    result["status"] = "SUCCESS"
    result["candidate_count"] = candidate_count
    return result
