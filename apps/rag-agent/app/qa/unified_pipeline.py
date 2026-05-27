"""@NB-ENTRYPOINT P3 Unified Pipeline — single entry for all QA flows.

UserQuestion → QueryRewriter → Retriever → QualityGate → PromptSelector → Generator → OutputFormatter

P1 + P3 integration point.
"""

from __future__ import annotations

import logging
from typing import Any

from app.qa.prompt_selector import select_prompt
from app.qa.qa_runner import QaRunner
from app.qa.quality_gate import GateDecision, evaluate as gate_evaluate
from app.qa.query_rewriter import RewriteRequest, rewrite as rewrite_query
from app.qa.retrieval_runner import RetrievalRunner

logger = logging.getLogger(__name__)


from app.reader_agent.memory import MemoryManager
from app.reader_agent.memory.session_memory import SessionTurn


async def run_pipeline(
    question: str,
    book_id: int,
    book_title: str = "",
    session_id: int = 0,
    provider: str = "local",
    entity_name: str | None = None,
    top_k: int = 12,
    conn=None,
    memory_manager: MemoryManager | None = None,
) -> dict:
    """Run the unified QA pipeline with MemoryManager integration.

    Args:
        question: User's natural language question.
        book_id: Book ID.
        book_title: Book title.
        session_id: Session ID for history tracking.
        provider: "local" or "deepseek".
        entity_name: Known entity name (from planner).
        top_k: Top-k retrieval count.
        conn: MySQL connection.
        memory_manager: MemoryManager for L0/L1/L2 memory.

    Returns:
        dict with keys: answer, citations, rewritten_query, intent, retrieval_stats, etc.
    """
    result: dict[str, Any] = {
        "answer": "",
        "citations": [],
        "rewritten_query": question,
        "intent": "factual",
        "retrieval_stats": {},
        "model_calls_note": "",
        "run_id": None,
    }

    # ── MemoryManager wiring: reset L1+L2, record current question in L1 ──
    if memory_manager:
        memory_manager.reset_run()
        memory_manager.l1.set_plan({
            "mode": "answer",
            "question": question,
            "book_id": book_id,
            "entity_name": entity_name,
        })

    if conn is None:
        result["answer"] = "数据库未连接"
        return result

    # ── Build history from MemoryManager for QueryRewriter ───────────────
    history: list[dict] = []
    if memory_manager and memory_manager.l0.turns:
        for t in memory_manager.l0.turns[-3:]:  # last 3 turns
            history.append({"role": "user", "content": t.question})
            if t.answer_preview:
                history.append({"role": "assistant", "content": t.answer_preview[:200]})

    # 1. QueryRewriter — rewrite for retrieval
    rewriter_request = RewriteRequest(
        question=question,
        book_id=book_id,
        book_title=book_title or f"Book {book_id}",
        entities=[entity_name] if entity_name else [],
        history=history,
    )
    rewrite_result = await rewrite_query(rewriter_request)
    result["rewritten_query"] = rewrite_result.rewritten_query
    result["intent"] = rewrite_result.intent

    # 2. Retriever — hybrid search
    runner = RetrievalRunner(conn)
    raw_results = await runner.hybrid_search(
        rewrite_result.rewritten_query,
        book_id,
        top_k=top_k,
        entity_name=rewrite_result.explicit_entities[0] if rewrite_result.explicit_entities else entity_name,
    )

    # 3. Build contexts (same as QaRunner)
    contexts = await _build_contexts(runner, conn, rewrite_result.rewritten_query, book_id, raw_results, top_k)

    # 4. Quality Gate
    gate_result = gate_evaluate(
        contexts=contexts,
        entity_name=rewrite_result.explicit_entities[0] if rewrite_result.explicit_entities else entity_name,
        retry_count=0,
    )

    result["retrieval_stats"] = {
        "raw_results": len(raw_results),
        "contexts_after_dedup": len(contexts),
        "gate_decision": gate_result.decision.value,
        "gate_reason": gate_result.reason,
    }

    if gate_result.decision in (GateDecision.FAIL_INSUFFICIENT,):
        # Fallback: call model directly (retrieval failed, use model knowledge)
        fallback = await _generate_then_retrieve(question, book_title, provider, book_id=book_id, conn=conn)
        result["answer"] = fallback
        return result

    if gate_result.decision == GateDecision.RETRY_BROADER:
        # Broader rewrite + retry
        broader_request = RewriteRequest(
            question=question,
            book_id=book_id,
            book_title=book_title,
            entities=rewrite_result.explicit_entities,
            previous_fail=True,
        )
        broader_result = await rewrite_query(broader_request)
        broader_raw = await runner.hybrid_search(
            broader_result.rewritten_query,
            book_id,
            top_k=top_k * 2,
            entity_name=rewrite_result.explicit_entities[0] if rewrite_result.explicit_entities else entity_name,
        )
        contexts = await _build_contexts(runner, conn, broader_result.rewritten_query, book_id, broader_raw, top_k)
        gate_result = gate_evaluate(contexts=contexts, retry_count=1)

        if gate_result.decision in (GateDecision.FAIL_INSUFFICIENT,):
            fallback = await _generate_then_retrieve(question, book_title, provider, book_id=book_id, conn=conn)
            result["answer"] = fallback
            return result

    if gate_result.decision == GateDecision.RETRY_ENTITY and gate_result.entity_name:
        entity_contexts = await _entity_bruteforce(conn, book_id, gate_result.entity_name)
        if entity_contexts:
            contexts = entity_contexts + contexts

        if not contexts:
            fallback = await _generate_then_retrieve(question, book_title, provider, book_id=book_id, conn=conn)
            result["answer"] = fallback
            return result

    # 5. Prompt Selector + Generator
    prompt_config = select_prompt(
        intent=rewrite_result.intent,
        book_title=book_title,
        target_name=rewrite_result.explicit_entities[0] if rewrite_result.explicit_entities else "",
    )

    # Format contexts into text
    context_text = runner._format_context(contexts) if hasattr(runner, "_format_context") else _simple_format(contexts)

    # Build messages for generator
    messages = [
        {"role": "system", "content": prompt_config.system_prompt},
        {"role": "user", "content": f"## 参考段落\n{context_text}\n\n## 问题\n{question}\n\n## 回答"},
    ]

    # Call LLM
    try:
        if provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            answer = await deepseek_client.chat(messages, temperature=prompt_config.temperature, max_tokens=prompt_config.max_tokens)
        else:
            from app.clients.llama_cpp_client import llama_client
            answer = await llama_client.chat(messages, temperature=prompt_config.temperature, max_tokens=prompt_config.max_tokens)
    except Exception as e:
        logger.exception("Generator failed")
        result["answer"] = f"生成回答时出错: {e}"
        return result

    # Extract citations
    citations = _extract_citations(answer, contexts)

    result["answer"] = answer or ""
    result["citations"] = citations

    # ── Record turn in MemoryManager L0 ────────────────────────────────
    if memory_manager and (answer or result.get("rewritten_query")):
        try:
            memory_manager.l0.record_turn(SessionTurn(
                mode="answer",
                question=question,
                optimized_question=result.get("rewritten_query", question),
                answer_preview=(answer or "")[:200],
                target_name=entity_name or "",
                target_type="",
                book_id=book_id,
                run_id=result.get("run_id", 0),
                evidence_ids=[c.get("source_id", 0) for c in citations[:10]],
                provider=provider,
            ))
            # Conversation window management: if > 10 turns, compact oldest
            if len(memory_manager.l0.turns) > 10:
                _compact_session(memory_manager)
        except Exception as e:
            logger.warning("Failed to record session turn: %s", e)

    return result


# ── DeepSeek 缓存前缀优化: 所有 prompt 共享同一前缀 ────────────
# 固定前缀保证缓存命中率。DeepSeek 按前缀缓存，相同开头只算一次
_DS_CACHE_PREFIX = "你是小说检索分析助手。请严格按指令输出。"


async def _generate_then_retrieve(
    question: str,
    book_title: str,
    provider: str,
    book_id: int | None = None,
    entity_name: str | None = None,
    conn=None,
) -> str:
    """Generate-then-Retrieve pipeline.

    Step 1: Model generates draft answer + search terms (from model knowledge)
    Step 2: Use search terms to retrieve evidence
    Step 3: If evidence found, model verifies/supplements; if not, return draft

    DeepSeek cache prefix optimization: fixed prefix for all calls.
    """
    book_ctx = f"《{book_title}》" if book_title else "相关书籍"

    # ═══ Step 1: Generate draft + search terms ═════════════════
    extract_prompt = (
        f"{_DS_CACHE_PREFIX}\n"
        f"书：{book_ctx}\n"
        f"问题：{question}\n\n"
        "先简洁回答，再给出3-5个检索关键词。\n"
        '输出 JSON：{"draft": "回答", "search_terms": ["关键词1", "关键词2"]}'
    )

    draft = ""
    search_terms: list[str] = []
    try:
        if provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            text = await deepseek_client.chat(
                messages=[{"role": "system", "content": _DS_CACHE_PREFIX}, {"role": "user", "content": extract_prompt}],
                temperature=0.3, max_tokens=1200,
            )
        else:
            from app.clients.llama_cpp_client import llama_client
            text = await llama_client.chat(
                messages=[{"role": "system", "content": _DS_CACHE_PREFIX}, {"role": "user", "content": extract_prompt}],
                temperature=0.3, max_tokens=1200,
            )

        if text:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            import json
            data = json.loads(text.strip())
            if isinstance(data, dict):
                draft = data.get("draft", "")
                search_terms = data.get("search_terms", [])
                if isinstance(search_terms, list):
                    search_terms = [str(t) for t in search_terms if t]
    except Exception as e:
        logger.warning("Generate-then-retrieve step 1 failed: %s", e)

    if not draft:
        draft = "（模型无法生成回答）"

    # ═══ Step 2: Retrieve using generated terms ════════════════
    evidence_text = ""
    if search_terms and conn and book_id:
        try:
            from app.qa.retrieval_runner import RetrievalRunner
            runner = RetrievalRunner(conn)
            # Search with each term, collect unique results
            seen = set()
            contexts = []
            for term in search_terms[:5]:
                results = await runner.hybrid_search(term, book_id, top_k=4, entity_name=entity_name)
                for r in results:
                    rid = r.get("id")
                    if rid and rid not in seen:
                        seen.add(rid)
                        # Fetch full text
                        text_content = None
                        with conn.cursor() as c:
                            c.execute("SELECT content FROM novel_chunk WHERE id = %s", (rid,))
                            row = c.fetchone()
                            if row:
                                text_content = str(row.get("content", ""))[:600]
                        if text_content:
                            contexts.append(f"[{r.get('source','chunk')}] {text_content}")
            if contexts:
                evidence_text = "\n\n".join(contexts[:5])
        except Exception as e:
            logger.warning("Generate-then-retrieve step 2 failed: %s", e)

    # ═══ Step 3: Integrate evidence into final answer ═══════════════
    has_relevant_evidence = bool(evidence_text)
    if evidence_text:
        # Check if evidence directly mentions entities from the question
        import re as _re
        question_entities = _re.findall(r'[\u4e00-\u9fff]{2,4}', question)
        evidence_mentions = sum(1 for e in question_entities if e in evidence_text)
        has_relevant_evidence = evidence_mentions >= 2  # at least 2 entity mentions in evidence

    if not has_relevant_evidence and draft:
        return f"以下回答基于模型知识，未检索到相关原文。\n\n{draft}"

    if has_relevant_evidence:
        integrate_prompt = (
            f"{_DS_CACHE_PREFIX}\n"
            f"书：{book_ctx}\n"
            f"问题：{question}\n\n"
            f"检索到的相关片段：\n{evidence_text}\n\n"
            "回答这个问题。有证据支持的论断用<cite>标注；证据不足的部分加「(基于模型知识)」。\n"
            "只输出回答，不要分析过程。"
        )
        try:
            if provider == "deepseek":
                from app.clients.deepseek_client import deepseek_client
                final = await deepseek_client.chat(
                    messages=[{"role": "system", "content": _DS_CACHE_PREFIX}, {"role": "user", "content": integrate_prompt}],
                    temperature=0.3, max_tokens=1500,
                )
            else:
                from app.clients.llama_cpp_client import llama_client
                final = await llama_client.chat(
                    messages=[{"role": "system", "content": _DS_CACHE_PREFIX}, {"role": "user", "content": integrate_prompt}],
                    temperature=0.3, max_tokens=1500,
                )
            if final and final.strip():
                return final.strip()
        except Exception as e:
            logger.warning("Generate-then-retrieve step 3 failed: %s", e)

    # Fallback: return draft with disclaimer
    return f"以下回答基于模型知识，未检索到相关原文。\n\n{draft}"


def _compact_session(mm: MemoryManager) -> None:
    """Compress oldest turns when session exceeds 10 turns.

    Keeps last 5 turns full, compresses older ones into a summary string.
    """
    turns = mm.l0.turns
    if len(turns) <= 10:
        return
    # Keep last 5, compact the rest
    keep = turns[-5:]
    compacted = turns[:-5]
    summary_parts = []
    for t in compacted:
        summary_parts.append(f"Q:{t.question[:60]} A:{t.answer_preview[:60]}")
    summary = " | ".join(summary_parts)
    # Store compressed summary in preferences (ephemeral)
    mm.l0.preferences.concise = True
    # Clear and re-add
    import copy
    for t in keep:
        t.timestamp = 0  # reset timestamp
    mm.l0.clear()
    for t in keep:
        mm.l0.record_turn(t)
    logger.info("Session compacted: %d turns → 5 + summary (%d chars)", len(compacted) + len(keep), len(summary))


async def _build_contexts(
    runner: RetrievalRunner,
    conn,
    query: str,
    book_id: int,
    search_results: list[dict],
    top_k: int,
) -> list[dict]:
    """Build full contexts from search results (same logic as QaRunner)."""
    contexts = []
    for r in search_results:
        source = r.get("source", "")
        if "chunk" in str(source):
            text = _get_chunk_text(conn, r.get("id"))
            if text:
                contexts.append({
                    "source": "chunk", "id": r["id"],
                    "chapter_id": r.get("metadata", {}).get("chapter_id") if isinstance(r.get("metadata"), dict) else 0,
                    "text": text, "score": r.get("score", 0),
                    "relevance": "high" if r.get("score", 0) > 0.5 else "medium",
                })
        elif "chapter_fact" in str(source):
            text = _get_fact_text(conn, r.get("id"))
            if text:
                contexts.append({
                    "source": "chapter_fact", "id": r["id"],
                    "chapter_id": r.get("metadata", {}).get("chapter_id") if isinstance(r.get("metadata"), dict) else 0,
                    "text": text, "score": r.get("score", 0),
                    "relevance": "medium",
                })

    # Deduplicate and limit
    seen = set()
    deduped = []
    for c in contexts:
        key = (c["source"], c["id"])
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped[:top_k]


async def _entity_bruteforce(conn, book_id: int, entity_name: str) -> list[dict]:
    """Direct SQL LIKE search by entity name (bypasses embedding)."""
    if not entity_name or not conn:
        return []
    results = []
    parts = entity_name.replace(",", " ").split()
    with conn.cursor() as cursor:
        for part in parts[:3]:
            if len(part.strip()) < 2:
                continue
            cursor.execute(
                "SELECT id, chapter_id, content FROM novel_chunk WHERE book_id = %s AND content LIKE %s LIMIT 4",
                (book_id, f"%{part.strip()}%"),
            )
            for row in cursor.fetchall():
                results.append({
                    "source": "chunk", "id": row["id"],
                    "chapter_id": row["chapter_id"],
                    "text": row.get("content", ""),
                    "score": 0.6,
                    "relevance": "high",
                })
    return results


def _get_chunk_text(conn, chunk_id: int | None) -> str | None:
    if not chunk_id or not conn:
        return None
    with conn.cursor() as cursor:
        cursor.execute("SELECT content FROM novel_chunk WHERE id = %s", (chunk_id,))
        row = cursor.fetchone()
        return str(row.get("content", ""))[:1200] if row and row.get("content") else None


def _get_fact_text(conn, fact_id: int | None) -> str | None:
    if not fact_id or not conn:
        return None
    with conn.cursor() as cursor:
        cursor.execute("SELECT summary FROM novel_chapter_fact WHERE id = %s", (fact_id,))
        row = cursor.fetchone()
        return str(row.get("summary", ""))[:600] if row and row.get("summary") else None


def _extract_citations(answer: str, contexts: list[dict]) -> list[dict]:
    """Extract <cite> tags from answer and match to contexts."""
    import re
    citations = []
    pattern = re.compile(r'<cite\s+type="(\w+)"(?:\s+id="(\d+)")?[^>]*>([^<]+)</cite>')
    for m in pattern.finditer(answer):
        source_type = m.group(1)
        source_id = int(m.group(2)) if m.group(2) else 0
        excerpt = m.group(3)
        citations.append({
            "source_type": source_type, "source_id": source_id,
            "excerpt": excerpt, "chapter_id": None,
        })
    return citations


def _simple_format(contexts: list[dict]) -> str:
    parts = []
    for i, ctx in enumerate(contexts[:8], 1):
        src = ctx.get("source", "chunk")
        text = ctx.get("text", "")[:600]
        parts.append(f"[{i}] ({src})\n{text}")
    return "\n\n".join(parts)
