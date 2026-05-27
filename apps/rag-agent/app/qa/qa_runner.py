"""
QA 生成引擎。
接收问题 → 混合检索 → 组装 context → 调 LLM → 解析回答 + 引用 → 存储。

Stage 5A: 接受可选 agent_run_id/agent_step_id/model_call_store/tool_call_store，
将模型调用和工具调用记录到 ReaderAgent run 下。默认 old behavior 不变。
"""
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

import pymysql

from app.clients.deepseek_client import deepseek_client
from app.clients.llama_cpp_client import llama_client
from app.clients.qdrant_client import qdrant_client
from app.qa.retrieval_runner import RetrievalRunner
from app.stores.qa_store import QaStore

logger = logging.getLogger(__name__)


class QaRunner:
    """QA 生成引擎"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
        self.retrieval = RetrievalRunner(conn)
        self.qa_store = QaStore(conn)

    def _ensure_conn(self):
        """LLM 长调用后确保 MySQL 连接未断连，断则 auto-reconnect"""
        try:
            self.conn.ping(reconnect=True)
        except Exception:
            logger.warning("MySQL connection lost, reconnecting...")
            import pymysql
            from app.config import settings
            self.conn = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
            )
            # 重建依赖此连接的子对象
            self.retrieval = RetrievalRunner(self.conn)
            self.qa_store = QaStore(self.conn)

    async def answer(
        self,
        session_id: int,
        book_id: int,
        question: str,
        use_deepseek: bool = False,
        *,
        agent_run_id: int | None = None,
        agent_step_id: int | None = None,
        model_call_store: Any = None,
        tool_call_store: Any = None,
    ) -> dict:
        """回答一个问题

        1. 确保 session 存在（auto-create）
        2. 获取 book 基本信息
        3. 获取最近对话历史
        4. 混合检索相关文本
        5. 组装 prompt
        6. 调 LLM 生成回答
        7. 提取引用
        8. 存储 message + citations
        9. 返回 {answer, citations}
        """
        # 1. 确保 session 存在
        if session_id == 0 or not self.qa_store.get_session(session_id):
            session_id = self.qa_store.create_session(book_id, title=f"Book {book_id} QA")

        # 2. 获取 book 基本信息
        book_title = self._get_book_title(book_id)

        # 3. 获取最近对话历史 (最多5轮)
        history = self.qa_store.get_recent_messages(session_id, limit=10)

        # 3. 构建增强检索查询（结合上一轮用户问题，支持多轮对话）
        search_query = self._build_search_query(question, history)

        # 3b. 抽象查询改写（优化3）：检测"道理""寓意""象征"等抽象词，用 DeepSeek 改写为具体检索词
        search_query = await self.retrieval._rewrite_abstract_query(search_query, book_id)

        # 4. 混合检索（用增强查询，优先搜索 planner 检测到的实体名）
        entity_name = self._extract_target_from_question(question)
        search_results = await self.retrieval.hybrid_search(
            search_query, book_id, top_k=12, entity_name=entity_name,
        )

        # 5. 读取 chunks/facts 完整内容（检索结果只有预览）
        contexts = []
        for r in search_results:
            if r['source'] == 'chunk' or 'chunk' in r.get('source', []):
                chunk_text = self._get_chunk_text(r['id'])
                if chunk_text:
                    contexts.append({
                        "source": "chunk",
                        "id": r['id'],
                        "chapter_id": r.get('metadata', {}).get('chapter_id', 0)
                                   if isinstance(r.get('metadata'), dict) else 0,
                        "text": chunk_text,
                        "score": r['score'],
                        "relevance": "high" if r['score'] > 0.5 else "medium"
                    })
            elif r['source'] == 'chapter_fact':
                fact_text = self._get_fact_text(r['id'])
                if fact_text:
                    contexts.append({
                        "source": "chapter_fact",
                        "id": r['id'],
                        "chapter_id": r.get('metadata', {}).get('chapter_id', 0)
                                   if isinstance(r.get('metadata'), dict) else 0,
                        "text": fact_text,
                        "score": r['score'],
                        "relevance": "high" if r['score'] > 0.5 else "medium"
                    })

        # 4.3 实体名直查：问题中出现的已知实体名，直接检索含该名的 chunks
        entity_chunks = self._entity_chunk_lookup(question, book_id)
        contexts.extend(entity_chunks)

        # 4.4 按章节多样性采样：每章最多 2 个 chunk，凑满 8 条
        contexts = self._diversify_by_chapter(contexts, top_k=8)

        knowledge_results = self.retrieval.knowledge_search(search_query, book_id)
        if knowledge_results:
            logger.info(f"Knowledge search returned {len(knowledge_results)} items: "
                        f"{[k['source'] for k in knowledge_results]}")
            # 追加结构化知识（不超过 4 条，不抢占 chunk 位置）
            for kr in knowledge_results[:4]:
                contexts.append({
                    "source": kr.get("source", "knowledge"),
                    "id": kr.get("id", 0),
                    "chapter_id": 0,
                    "text": kr.get("text", ""),
                    "score": 0.01,  # 低分确保排在 chunks 之后
                    "relevance": "medium",
                })

        # ── Retrieval Quality Gate (P3): 检索为空时走模型知识 ──
        retrieval_empty = not contexts
        model_knowledge_prompt = f"""你是小说《{book_title}》的阅读理解助手。当前检索未找到相关原文段落，请基于你自己的知识来回答。

回答策略：
- 如果你了解该小说和问题中的角色/事件，请直接回答
- 在回答末尾注明："（基于模型知识，未找到原文段落）"
- 如果你不了解，请诚实地回答你不知道

不要编造不存在的内容。"""
        if retrieval_empty:
            logger.warning(f"Retrieval: 0 results for q={question[:80]} from book={book_id}, fallback to model knowledge")
            context_text = ""
        else:
            context_text = self._format_context(contexts)

        # 构建对话历史字符串
        history_text = self._format_history(history)

        # ── 检索为空时用模型知识 fallback prompt ──
        if retrieval_empty:
            system_prompt = model_knowledge_prompt
        elif use_deepseek:
            system_prompt = f"""你是小说《{book_title}》的阅读理解助手。
请基于提供的参考段落来回答问题。

信息来源优先级：
1. 原文段落（chunk）= 最直接证据
2. 角色档案（entity_profile）= 描述角色的标准信息
3. 角色关系（relation）= 关系事实
4. 事件记录（event）= 事件摘要

回答策略：
- 先用角色档案回答角色身份类问题
- 综合多个段落的信息来推断完整答案
- 如果角色档案中有明确的描述，即使原文段落未提及也可以回答

引用要求：
- 每个关键事实必须引用具体来源
- 引用格式：<cite type="source_type" id="编号">原文片段</cite>
- 对于枚举性问题（"多少人""分几部分"），必须逐条引用每个数字/条目

只有在所有来源都完全没有相关信息时，才回答"基于现有信息无法回答"。
不要编造不存在的内容。"""
        else:
            system_prompt = f"""你是小说《{book_title}》的阅读理解助手。
请基于提供的参考段落来回答问题。每个段落前的方括号标记了来源类型。
引用格式：<cite type="chunk" id="123">原文片段</cite>
引用时 type 对应来源类型（chunk=原文段落, relation=角色关系, entity_profile=角色档案, event=事件记录），id 用段落编号。

信息来源优先级：
1. 原文段落（chunk）= 最直接证据
2. 角色档案（entity_profile）= 描述角色的标准信息，可用来回答角色身份/背景
3. 角色关系（relation）= 关系事实
4. 事件记录（event）= 事件摘要

回答策略：
- 先用角色档案回答角色身份类问题（如"沙僧是什么身份"）
- 综合多个段落的信息来推断完整答案
- 如果角色档案中有明确的描述，即使原文段落未提及也可以回答

引用要求：
- 每个论断必须引用检索结果中的具体文本
- 每个关键事实尽量引用具体来源
- 角色档案的信息用 <cite type="entity_profile">角色名</cite>
- 关系的引用用 <cite type="relation">关系描述</cite>
- 原文引用用 <cite type="chunk">原文片段</cite>

只有在所有来源（原文+角色档案+关系+事件）都完全没有相关信息时，才回答"基于现有信息无法回答"。
不要编造不存在的内容。"""

        if use_deepseek:
            answer_style_contract = """
## 回答输出约束
- 先直接回答问题，再补充必要分析。
- 可以自然展开，但要围绕问题，不要罗列资料。
- 枚举性问题必须逐条回答，每条带引用。
- 如果证据不足，明确说"基于现有证据无法确认"，不要编造。
- 答案应该简洁完整，避免过短回答（少于80字时要补充说明）。
"""
        else:
            answer_style_contract = """
## 回答输出约束
- 先直接回答问题，再补充必要分析，不要先复述检索到的原文。
- 可以自然展开，但要围绕问题，不要写成资料罗列。
- 关键事实应有引用；引用只用于支撑结论，不能替代回答本身。
- 每个论断必须有检索文本支撑，无法引用时要说明"证据不足"。
- 不要连续堆砌原文片段，不要把参考段落当作最终答案。
- 如果证据不足，明确说"基于现有证据无法确认"，不要编造。
"""

        context_part = f"""
## 参考段落
{context_text}

## 对话历史
{history_text}

{answer_style_contract}

## 问题
{question}

## 回答（请引用原文）"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_part}
        ]

        # 6. 调 LLM（同时记录 model_call + tool_call 到 ReaderAgent run）
        model_call_id = None
        tool_call_id = None
        llm_start = time.monotonic()
        llm_provider = "deepseek" if use_deepseek else "local"
        llm_model = "DeepSeek API" if use_deepseek else "Qwen3.5-9B-Q8_0"

        # Record model call (PENDING) if store available
        if model_call_store is not None and agent_run_id is not None:
            try:
                model_call_id = model_call_store.create_model_call({
                    "agent_run_id": agent_run_id,
                    "agent_step_id": agent_step_id,
                    "book_id": book_id,
                    "task_type": "qa_answer",
                    "provider": llm_provider,
                    "model_name": llm_model,
                    "prompt_name": "reader_agent_answer_v1",
                    "input_text": system_prompt[:200] + "\n" + context_part[:200],
                    "request_json": {"messages": messages, "temperature": 0.3, "max_tokens": 2048},
                    "status": "PENDING",
                })
            except Exception as e:
                logger.warning("Model call start persistence failed: %s", e)

        # Record tool call for answer generation (PENDING)
        if tool_call_store is not None and agent_run_id is not None:
            try:
                tool_call_id = tool_call_store.create_tool_call(
                    "qa_answer",
                    agent_run_id=agent_run_id,
                    agent_step_id=agent_step_id,
                    input_json={"book_id": book_id, "question": question[:100], "provider": llm_provider},
                    status="RUNNING",
                )
            except Exception as e:
                logger.warning("Tool call start persistence failed: %s", e)

        # Execute LLM call
        try:
            if use_deepseek:
                answer = await deepseek_client.chat(messages, temperature=0.3, max_tokens=2048)
            else:
                answer = await llama_client.chat(messages, temperature=0.3, max_tokens=2048)
            llm_status = "SUCCESS"
        except Exception as e:
            logger.warning(f"LLM call failed, returning mock: {e}")
            answer = self._generate_mock_answer(question, contexts)
            llm_status = "FAILED"

        llm_duration_ms = int((time.monotonic() - llm_start) * 1000)

        # Finish model call
        if model_call_store is not None and model_call_id is not None:
            try:
                model_call_store.finish_model_call(model_call_id, {
                    "status": llm_status,
                    "output_text": answer[:500],
                    "response_json": {"content": answer[:200]},
                    "duration_ms": llm_duration_ms,
                })
            except Exception as e:
                logger.warning("Model call finish persistence failed: %s", e)

        # Finish tool call
        if tool_call_store is not None and tool_call_id is not None:
            try:
                tool_call_store.finish_tool_call(
                    tool_call_id,
                    status=llm_status,
                    output_json={"answer_length": len(answer), "citation_count_estimate": 0},
                    error_message="" if llm_status == "SUCCESS" else "LLM failed, used mock",
                )
            except Exception as e:
                logger.warning("Tool call finish persistence failed: %s", e)

        # 7. 确保 LLM 长调用后 MySQL 连接仍存活
        self._ensure_conn()

        # 8. 提取引用
        citations = self._extract_citations(answer, contexts)

        # 9. 存储到 DB
        msg_count = self.qa_store.get_message_count(session_id)
        msg_index = msg_count + 1

        # 存 user message（Python 侧也存一份作为保障）
        self.qa_store.insert_user_message(session_id, book_id, question, msg_count)

        # 存 assistant message
        msg_id = self.qa_store.insert_assistant_message(session_id, book_id, answer, msg_index)

        # 存 citations
        for cit in citations:
            self.qa_store.insert_citation(
                message_id=msg_id,
                book_id=book_id,
                source_type=cit.get('source_type', 'chunk'),
                source_id=cit.get('source_id', 0),
                chapter_id=cit.get('chapter_id', 0),
                excerpt=cit.get('excerpt', ''),
                evidence_level=cit.get('evidence_level', 'NEAR'),
                relevance_score=cit.get('relevance_score', 0.5)
            )

        return {
            "answer": answer,
            "citations": citations
        }

    def _build_search_query(self, question: str, history: List[Dict]) -> str:
        """
        构建增强检索查询：将上一轮用户问题与当前问题拼接，
        让代词（他、她、它）能检索到上文的实体。
        """
        if not history:
            return question
        # 取最近的用户问题（之前最多1轮）
        last_user_q = ''
        for h in reversed(history):
            if h.get('role') == 'user':
                last_user_q = (h.get('content') or '').strip()
                break
        if not last_user_q or last_user_q == question:
            return question
        # 简短拼接："[历史] 孙悟空是谁？ [当前] 他是怎么拿到金箍棒的？"
        return f"[历史] {last_user_q} [当前] {question}"

    def _entity_chunk_lookup(self, question: str, book_id: int) -> List[Dict]:
        """
        实体名直查：检测问题中的已知实体名（含别名匹配），
        直接去 novel_chunk 做 LIKE 匹配。
        确保含关键实体名的 chunk 不会被埋没。
        """
        import json
        extra = []
        matched_names = set()  # canonical names that matched

        with self.conn.cursor() as c:
            c.execute(
                "SELECT canonical_name, aliases_json FROM novel_entity_profile "
                "WHERE book_id = %s AND status = 'ACTIVE' "
                "AND LENGTH(canonical_name) >= 2",
                (book_id,)
            )
            for row in c.fetchall():
                name = row['canonical_name']
                # 检查 canonical_name 是否在问题中
                if name in question:
                    matched_names.add(name)
                    continue
                # 检查别名是否在问题中
                try:
                    aliases = json.loads(row['aliases_json']) if row.get('aliases_json') else []
                    if isinstance(aliases, list):
                        for alias in aliases:
                            if isinstance(alias, str) and len(alias) >= 2 and alias in question:
                                matched_names.add(name)
                                break
                except (json.JSONDecodeError, TypeError):
                    pass

        # 对每个匹配的 canonical_name 检索 chunks
        seen_ids = set()
        if matched_names:
            with self.conn.cursor() as c:
                for name in matched_names:
                    c.execute(
                        "SELECT id, content, chapter_id FROM novel_chunk "
                        "WHERE book_id = %s AND content LIKE CONCAT('%%', %s, '%%') "
                        "LIMIT 3",
                        (book_id, name)
                    )
                    for r2 in c.fetchall():
                        if r2['id'] not in seen_ids:
                            seen_ids.add(r2['id'])
                            extra.append({
                                "source": "chunk",
                                "id": r2['id'],
                                "chapter_id": r2['chapter_id'],
                                "text": r2['content'],
                                "score": 0.3,
                                "relevance": "high",
                            })

        if extra:
            logger.info(f"Entity chunk lookup matched {list(matched_names)}: "
                        f"found {len(extra)} chunks")
        return extra

    def _diversify_by_chapter(self, contexts: List[Dict], top_k: int = 8) -> List[Dict]:
        """
        按章节多样性采样：每章最多 2 个 chunk，确保覆盖更多章节。
        如果总条数不足 top_k，补回被排除的高分 chunk。
        """
        # 按 score 降序排列
        sorted_ctx = sorted(contexts, key=lambda x: x['score'], reverse=True)

        selected = []
        chapter_counts = {}
        overflow = []

        for ctx in sorted_ctx:
            ch_id = ctx.get('chapter_id', 0)
            count = chapter_counts.get(ch_id, 0)
            if count < 2:
                selected.append(ctx)
                chapter_counts[ch_id] = count + 1
            else:
                overflow.append(ctx)

        # 如果不足 top_k，从 overflow 中补回
        while len(selected) < top_k and overflow:
            selected.append(overflow.pop(0))

        logger.info(f"Diversify: {len(sorted_ctx)} → {len(selected)} contexts, "
                     f"{len(chapter_counts)} chapters")
        return selected[:top_k]

    def _get_book_title(self, book_id: int) -> str:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT title FROM novel_book WHERE id = %s", (book_id,))
            row = cursor.fetchone()
            return row['title'] if row else 'Unknown'

    def _get_chunk_text(self, chunk_id: int) -> Optional[str]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT content, chapter_id FROM novel_chunk WHERE id = %s", (chunk_id,))
            row = cursor.fetchone()
            return row['content'] if row else None

    def _get_fact_text(self, fact_id: int) -> Optional[str]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT summary, fact_json, chapter_id FROM novel_chapter_fact WHERE id = %s", (fact_id,))
            row = cursor.fetchone()
            if row:
                # 优先用 fact_json 中的事件描述（更丰富）
                try:
                    fj = json.loads(row['fact_json']) if row.get('fact_json') else {}
                    events = fj.get('events', [])
                    if events:
                        parts = []
                        for e in events[:5]:
                            desc = e.get('description') or e.get('summary') or ''
                            if desc:
                                parts.append(desc[:200])
                        if parts:
                            return "[事件信息] " + " | ".join(parts)
                except (json.JSONDecodeError, TypeError):
                    pass
                # 回退到 summary
                summary = row.get('summary', '') or ''
                return f"[章摘要] {summary}" if summary else None
            return None

    def _extract_target_from_question(self, question: str) -> str | None:
        """从问题中提取出已知的人物/实体名，用于优先检索。

        简单版：检查 planner 的 BOOK_CATALOG 中的实体名是否出现在问题中。
        如果找到，返回第一个匹配的实体名。
        """
        try:
            from app.reader_agent.planner import BOOK_CATALOG
            for book_id, catalog in BOOK_CATALOG.items():
                all_names = catalog.get("characters", []) + catalog.get("items", []) + catalog.get("settings", [])
                for name in all_names:
                    if name and name in question:
                        return name
        except Exception:
            pass
        return None

    def _format_context(self, contexts: List[Dict]) -> str:
        parts = []
        source_labels = {
            "chunk": "原文段落",
            "chapter_fact": "章摘要/事件",
            "entity_profile": "角色档案",
            "relation": "角色关系",
            "event": "事件记录",
            "relation_fact": "角色关系",
        }
        for i, ctx in enumerate(contexts):
            src_type = source_labels.get(ctx.get('source', ''), ctx.get('source', '信息'))
            # 结构化知识：用描述替代 id=0 的编号
            ctx_id = ctx.get('id', 0)
            src = ctx.get('source', '')
            if src in ('entity_profile', 'relation', 'event', 'relation_fact'):
                # 从文本中提取前20字作为摘要标识
                label = ctx.get('text', '')[:30].replace('\n', ' ')
                id_str = label
            else:
                id_str = f"chunk={ctx_id}" if src == 'chunk' else f"id={ctx_id}"
            parts.append(f"[{i+1}] ({src_type}, {id_str})\n{ctx['text'][:1200]}")
        return "\n\n".join(parts)

    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return "无"
        lines = []
        for h in history[-6:]:  # 最近3轮对话
            role = "用户" if h['role'] == 'user' else "助手"
            content = (h.get('content', '') or '')[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _extract_citations(self, answer: str, contexts: List[Dict]) -> List[Dict]:
        """从回答中提取 <cite> 标记的引用
        支持三种匹配方式：
        1. source_type + id 匹配（标准的 chunk 引用: <cite type="chunk" id="123">）
        2. 用 id 作为段落索引 [N] 回查 contexts
        3. 文本 ID（结构化知识的 description 引用: <cite type="entity_profile">文本片段</cite>）
        """
        citations = []
        pattern = re.compile(r'<cite\s+type="(\w+)"(?:\s+id="(\d+)")?[^>]*>([^<]+)</cite>')

        for match in pattern.finditer(answer):
            source_type_str = match.group(1)
            id_str = match.group(2)
            source_id = int(id_str) if id_str else 0
            excerpt = match.group(3)

            chapter_id = 0
            actual_type = source_type_str
            actual_id = source_id

            # 优先按 source_type + id 查找
            ctx_match = None
            if source_id > 0:
                for ctx in contexts:
                    if ctx.get('source') == source_type_str and ctx.get('id') == source_id:
                        ctx_match = ctx
                        break

            # 如果没找到且 id>0，用 id 作为段落编号回查（[i+1] 格式）
            if not ctx_match and source_id > 0:
                idx = source_id - 1  # 段落编号 [1] 对应 context[0]
                if 0 <= idx < len(contexts):
                    ctx_match = contexts[idx]
                    actual_type = ctx_match.get('source', source_type_str)
                    actual_id = ctx_match.get('id', source_id)

            if ctx_match:
                chapter_id = ctx_match.get('chapter_id', 0) or 0

            citations.append({
                "source_type": actual_type,
                "source_id": actual_id,
                "chapter_id": chapter_id,
                "excerpt": excerpt,
                "evidence_level": "EXACT",
                "relevance_score": 0.8
            })

        return citations

    def _generate_mock_answer(self, question: str, contexts: List[Dict]) -> str:
        """当 LLM 不可用时的 mock 回答"""
        if not contexts:
            return f"抱歉，基于现有信息无法回答「{question}」。未找到相关原文段落。"

        # 用第一个 context 作为引用
        first = contexts[0]
        excerpt = first['text'][:100]

        return f"根据原文记载：{excerpt}\n\n<cite type=\"{first['source']}\" id=\"{first['id']}\">{excerpt[:50]}……</cite>\n\n（注意：当前 LLM 服务不可用，此为基于检索结果的模拟回答。）"
