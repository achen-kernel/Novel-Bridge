"""ReaderAgent analyze mode, minimal deterministic implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agent_runtime.citation_verifier import CitationVerifier
from app.agent_runtime.run_store import MysqlAgentRunStore
from app.agent_runtime.schemas import EvidenceItem, EvidenceLevel
from app.agent_runtime.tool_call_store import MysqlToolCallStore
from app.agent_runtime.trace_store import MysqlRetrievalTraceStore
from app.clients.deepseek_client import deepseek_client
from app.clients.llama_cpp_client import llama_client
from app.qa.retrieval_runner import RetrievalRunner
from app.reader_agent.schemas import ReaderRequest, ReaderResponse
from app.reader_agent.states import ReaderState
from app.stores.relation_fact_store import RelationFactStore

logger = logging.getLogger(__name__)


def _clean_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


class AnalyzeMode:
    """Minimal analyze mode for character and relation.

    The mode is deterministic and evidence-first: it reads existing structured
    stores plus best-effort RetrievalRunner results, then returns
    INSUFFICIENT_EVIDENCE when no L2 evidence can support the requested target.
    """

    def __init__(self, conn=None) -> None:
        self.conn = conn

    async def run(self, request: ReaderRequest) -> ReaderResponse:
        if self.conn is None:
            return ReaderResponse(
                mode="analyze",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent analyze mode requires a MySQL connection."],
            )

        analysis_type = request.analysis_type or self._infer_analysis_type(request)
        if analysis_type not in {"character", "relation"}:
            return ReaderResponse(
                mode="analyze",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent analyze mode only supports character and relation."],
            )

        run_store = MysqlAgentRunStore(self.conn)
        trace_store = MysqlRetrievalTraceStore(self.conn)
        tool_store = MysqlToolCallStore(self.conn)

        run_id = run_store.create_run(
            agent_name="ReaderAgent",
            mode="analyze",
            payload={
                "book_id": request.book_id,
                "question": request.question,
                "analysis_type": analysis_type,
                "target_name": request.target_name,
                "target_type": request.target_type,
                "options": request.options.model_dump(),
            },
        )
        step1_id = run_store.create_step(
            run_id,
            "EVIDENCE_SEARCH",
            payload={
                "book_id": request.book_id,
                "analysis_type": analysis_type,
                "target_name": request.target_name,
                "top_k": request.options.top_k,
            },
            step_order=0,
        )
        trace_id = trace_store.create_trace(
            run_id,
            query=request.question,
            payload={"book_id": request.book_id, "mode": "analyze"},
        )

        try:
            if analysis_type == "character":
                result = await self._analyze_character(request, trace_id, tool_store, run_id, step1_id)
            else:
                result = await self._analyze_relation(request, trace_id, tool_store, run_id, step1_id)
        except Exception as exc:
            logger.exception("ReaderAgent analyze failed")
            run_store.finish_step(
                step1_id,
                "FAILED",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            run_store.finish_run(
                run_id,
                "FAILED",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return ReaderResponse(
                run_id=run_id,
                mode="analyze",
                status=ReaderState.FAILED,
                trace_id=trace_id,
                errors=[f"ReaderAgent analyze failed: {exc}"],
            )

        evidence = result["evidence"]
        verification = CitationVerifier().verify(evidence)
        status = ReaderState.RESPONDED
        errors: list[str] = []
        if request.options.require_citations and (not evidence or not verification.ok):
            status = ReaderState.INSUFFICIENT_EVIDENCE
            errors.extend(verification.errors or ["No evidence found for analyze mode"])

        step2_id = run_store.create_step(
            run_id,
            "DRAFT_READY",
            payload={
                "analysis_type": analysis_type,
                "evidence_count": len(evidence),
                "key_point_count": len(result["analysis"].get("key_points", [])),
                "citation_verification_passed": verification.ok,
                "citation_verification_errors": verification.errors,
            },
            step_order=1,
        )
        run_store.finish_step(step2_id, "SUCCESS", payload={"answer_preview": result["answer"][:200]})
        run_store.finish_step(
            step1_id,
            "SUCCESS",
            payload={"evidence_count": len(evidence), "status": status.value},
        )
        run_store.finish_run(
            run_id,
            status.value,
            payload={
                "analysis_type": analysis_type,
                "evidence_count": len(evidence),
                "trace_id": trace_id,
                "patch_count": 0,
            },
        )

        return ReaderResponse(
            run_id=run_id,
            mode="analyze",
            status=status,
            answer=result["answer"] if status == ReaderState.RESPONDED else "INSUFFICIENT_EVIDENCE",
            citations=evidence,
            evidence=evidence,
            trace_id=trace_id,
            patches=[],
            analysis=result["analysis"] if status == ReaderState.RESPONDED else {
                "analysis_type": analysis_type,
                "summary": "INSUFFICIENT_EVIDENCE",
                "key_points": [],
                "evidence": [],
                "limitations": result["analysis"].get("limitations", []),
            },
            errors=errors,
        )

    def _infer_analysis_type(self, request: ReaderRequest) -> str:
        text = f"{request.target_type or ''} {request.question}"
        if any(token in text for token in ("关系", "师徒", "兄弟", "敌", "朋友")):
            return "relation"
        return "character"

    async def _analyze_character(
        self,
        request: ReaderRequest,
        trace_id: int,
        tool_store: MysqlToolCallStore,
        run_id: int,
        step_id: int,
    ) -> dict[str, Any]:
        target = _clean_text(request.target_name) or self._guess_target_name(request.question)
        evidence: list[EvidenceItem] = []
        limitations: list[str] = []
        key_points: list[dict[str, Any]] = []

        entity_call = tool_store.create_tool_call(
            "structured_entity_lookup",
            agent_run_id=run_id,
            agent_step_id=step_id,
            input_json={"book_id": request.book_id, "target_name": target},
        )
        entity = self._find_entity(request.book_id, target)
        relations = RelationFactStore(self.conn).find_by_entity(request.book_id, entity["canonical_name"]) if entity else []
        tool_store.finish_tool_call(
            entity_call,
            output_json={
                "entity_found": bool(entity),
                "entity_id": entity.get("id") if entity else None,
                "relation_count": len(relations),
            },
        )

        relation_summaries: list[str] = []
        aliases: list[str] = []
        if entity:
            desc = _clean_text(entity.get("description"), 360)
            aliases = [str(a) for a in _json_list(entity.get("aliases_json"))[:5]]
            profile_excerpt = desc or f"{entity.get('canonical_name')}，类型：{entity.get('entity_type') or 'UNKNOWN'}"
            evidence.append(EvidenceItem(
                source_type="entity",
                source_id=int(entity["id"]),
                chapter_id=entity.get("first_chapter_id"),
                excerpt=profile_excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=0.9,
            ))
            key_points.append({
                "claim": self._character_identity_claim(entity),
                "evidence_refs": [0],
            })
            if desc:
                key_points.append({"claim": self._compress_description(desc), "evidence_refs": [0]})
            if aliases:
                key_points.append({"claim": f"常见别名包括：{'、'.join(aliases)}。", "evidence_refs": [0]})
        else:
            limitations.append(f"未在实体档案中找到目标：{target or request.question}")

        for rel in relations[:3]:
            rel_excerpt = (
                f"{rel.get('source_entity_name')} -{rel.get('relation_type')}- "
                f"{rel.get('target_entity_name')}"
            )
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="relation",
                source_id=int(rel.get("id") or 0),
                chapter_id=rel.get("first_chapter_id"),
                excerpt=rel_excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=float(rel.get("confidence") or 0.7),
            ))
            relation_summaries.append(rel_excerpt)
            key_points.append({"claim": f"关系线索：{rel_excerpt}。", "evidence_refs": [idx]})

        retrieval_query = f"{target or request.question} 人物 身份 性格 事迹"
        retrieval_items = await self._retrieval_evidence(
            retrieval_query, request.book_id, request.options.top_k, trace_id, tool_store, run_id, step_id
        )
        if not entity and target:
            retrieval_items = [item for item in retrieval_items if target in item.excerpt]
            if not retrieval_items:
                limitations.append(
                    "实体档案未命中，且检索证据未包含完整目标名；已按证据不足处理。"
                )
        evidence.extend(retrieval_items)

        for idx, item in enumerate(evidence):
            self._add_trace_item(trace_id, item, idx)

        if len(evidence) > len(key_points):
            key_points.append({
                "claim": "原文/章事实检索提供了补充语境，适合作为进一步人工复核依据。",
                "evidence_refs": list(range(len(key_points), min(len(evidence), len(key_points) + 3))),
            })
        if not evidence:
            limitations.append("结构化数据和检索结果都没有提供可引用证据。")

        summary = self._character_summary(target, entity, aliases, relation_summaries, key_points)
        analysis = self._build_analysis("character", target, summary, key_points, evidence, limitations)
        analysis = await self._synthesize_analysis(request, analysis, evidence)
        return {"answer": self._format_answer(analysis), "analysis": analysis, "evidence": evidence}

    async def _analyze_relation(
        self,
        request: ReaderRequest,
        trace_id: int,
        tool_store: MysqlToolCallStore,
        run_id: int,
        step_id: int,
    ) -> dict[str, Any]:
        names = self._parse_relation_targets(request)
        evidence: list[EvidenceItem] = []
        limitations: list[str] = []
        key_points: list[dict[str, Any]] = []

        relation_call = tool_store.create_tool_call(
            "structured_relation_lookup",
            agent_run_id=run_id,
            agent_step_id=step_id,
            input_json={"book_id": request.book_id, "targets": names},
        )
        relations = self._find_relations(request.book_id, names)
        tool_store.finish_tool_call(
            relation_call,
            output_json={"target_count": len(names), "relation_count": len(relations)},
        )

        relation_types: list[str] = []
        for rel in relations[:6]:
            rel_excerpt = (
                f"{rel.get('source_entity_name')} -{rel.get('relation_type')}- "
                f"{rel.get('target_entity_name')}"
            )
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="relation",
                source_id=int(rel.get("id") or 0),
                chapter_id=rel.get("first_chapter_id"),
                excerpt=rel_excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=float(rel.get("confidence") or 0.75),
            ))
            if rel.get("relation_type"):
                relation_types.append(str(rel.get("relation_type")))
            key_points.append({"claim": f"结构化关系记录显示：{rel_excerpt}。", "evidence_refs": [idx]})

        if not names:
            limitations.append("未能从 target_name 或 question 中解析出关系分析对象。")
        elif not relations:
            limitations.append(f"未找到 {'、'.join(names)} 的直接结构化关系记录。")

        retrieval_query = request.target_name or request.question
        evidence.extend(await self._retrieval_evidence(
            retrieval_query, request.book_id, request.options.top_k, trace_id, tool_store, run_id, step_id
        ))
        for idx, item in enumerate(evidence):
            self._add_trace_item(trace_id, item, idx)

        if len(evidence) > len(key_points):
            key_points.append({
                "claim": "检索证据提供了关系语境，但最小 analyze 版本不做模型推断扩写。",
                "evidence_refs": list(range(len(key_points), min(len(evidence), len(key_points) + 3))),
            })
        if not evidence:
            limitations.append("结构化关系和检索结果都没有提供可引用证据。")

        target = "、".join(names) if names else (request.target_name or request.question)
        summary = self._relation_summary(names, relation_types, bool(relations), bool(evidence))
        analysis = self._build_analysis("relation", target, summary, key_points, evidence, limitations)
        analysis = await self._synthesize_analysis(request, analysis, evidence)
        return {"answer": self._format_answer(analysis), "analysis": analysis, "evidence": evidence}

    async def _retrieval_evidence(
        self,
        query: str,
        book_id: int,
        top_k: int,
        trace_id: int,
        tool_store: MysqlToolCallStore,
        run_id: int,
        step_id: int,
    ) -> list[EvidenceItem]:
        call_id = tool_store.create_tool_call(
            "hybrid_search",
            agent_run_id=run_id,
            agent_step_id=step_id,
            input_json={"query": query, "book_id": book_id, "top_k": min(top_k, 8)},
        )
        items: list[EvidenceItem] = []
        try:
            results = await RetrievalRunner(self.conn).hybrid_search(query, book_id, top_k=min(top_k, 8))
            for result in results[:5]:
                item = self._result_to_evidence(result)
                if item:
                    items.append(item)
            tool_store.finish_tool_call(call_id, output_json={"result_count": len(items)})
        except Exception as exc:
            logger.warning("Analyze hybrid search failed: %s", exc)
            tool_store.finish_tool_call(call_id, status="FAILED", error_message=str(exc))
        return items

    def _result_to_evidence(self, result: dict[str, Any]) -> EvidenceItem | None:
        source = result.get("source") or "chunk"
        source_id = int(result.get("id") or 0)
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        chapter_id = metadata.get("chapter_id")
        if source == "chunk":
            excerpt = self._get_chunk_excerpt(source_id)
            source_type = "chunk"
        elif source == "chapter_fact":
            excerpt = self._get_fact_excerpt(source_id)
            source_type = "chapter_fact"
        else:
            return None
        if not excerpt:
            return None
        return EvidenceItem(
            source_type=source_type,
            source_id=source_id,
            chapter_id=chapter_id,
            excerpt=excerpt,
            evidence_level=EvidenceLevel.NEAR,
            relevance_score=min(float(result.get("score") or 0.5), 1.0),
        )

    def _find_entity(self, book_id: int, target: str) -> dict[str, Any] | None:
        if not target:
            return None
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM novel_entity_profile
                   WHERE book_id = %s AND status = 'ACTIVE'
                     AND (canonical_name = %s OR aliases_json LIKE %s)
                   ORDER BY mention_count DESC LIMIT 1""",
                (book_id, target, f"%{target}%"),
            )
            row = cursor.fetchone()
            if row:
                return row
            cursor.execute(
                """SELECT * FROM novel_entity_profile
                   WHERE book_id = %s AND status = 'ACTIVE'
                     AND (canonical_name LIKE %s OR aliases_json LIKE %s)
                   ORDER BY mention_count DESC LIMIT 1""",
                (book_id, f"%{target}%", f"%{target}%"),
            )
            return cursor.fetchone()

    def _find_relations(self, book_id: int, names: list[str]) -> list[dict[str, Any]]:
        if not names:
            return []
        with self.conn.cursor() as cursor:
            if len(names) >= 2:
                a, b = names[0], names[1]
                cursor.execute(
                    """SELECT * FROM novel_relation_fact
                       WHERE book_id = %s AND status = 'ACTIVE'
                         AND ((source_entity_name LIKE %s AND target_entity_name LIKE %s)
                           OR (source_entity_name LIKE %s AND target_entity_name LIKE %s))
                       ORDER BY strength DESC, confidence DESC LIMIT 8""",
                    (book_id, f"%{a}%", f"%{b}%", f"%{b}%", f"%{a}%"),
                )
                rows = cursor.fetchall()
                if rows:
                    return rows
            first = names[0]
            cursor.execute(
                """SELECT * FROM novel_relation_fact
                   WHERE book_id = %s AND status = 'ACTIVE'
                     AND (source_entity_name LIKE %s OR target_entity_name LIKE %s)
                   ORDER BY strength DESC, confidence DESC LIMIT 8""",
                (book_id, f"%{first}%", f"%{first}%"),
            )
            return cursor.fetchall()

    def _get_chunk_excerpt(self, chunk_id: int) -> str:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT content FROM novel_chunk WHERE id = %s", (chunk_id,))
            row = cursor.fetchone()
            return _clean_text(row.get("content"), 360) if row else ""

    def _get_fact_excerpt(self, fact_id: int) -> str:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT summary, fact_json FROM novel_chapter_fact WHERE id = %s", (fact_id,))
            row = cursor.fetchone()
        if not row:
            return ""
        summary = _clean_text(row.get("summary"), 300)
        if summary:
            return summary
        try:
            fact_json = json.loads(row.get("fact_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            return ""
        events = fact_json.get("events") if isinstance(fact_json, dict) else []
        if isinstance(events, list) and events:
            event = events[0]
            if isinstance(event, dict):
                return _clean_text(event.get("description") or event.get("summary"), 300)
        return ""

    def _guess_target_name(self, question: str) -> str:
        text = question.strip()
        for token in ("分析", "人物", "角色", "关系", "是谁", "怎么样", "如何"):
            text = text.replace(token, " ")
        parts = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
        return parts[0] if parts else text[:20]

    def _parse_relation_targets(self, request: ReaderRequest) -> list[str]:
        raw = request.target_name or request.question
        for sep in ("和", "与", "、", ",", "，", "/", "|", "；", ";"):
            raw = raw.replace(sep, " ")
        candidates = [
            p.strip()
            for p in re.split(r"\s+", raw)
            if 2 <= len(p.strip()) <= 12
        ]
        filtered = []
        stop_tokens = ("分析", "关系", "什么", "如何", "他们", "之间", "请问")
        for item in candidates:
            clean = item
            for token in stop_tokens:
                clean = clean.replace(token, "")
            clean = clean.strip()
            if clean and clean not in filtered:
                filtered.append(clean)
        return filtered[:2]

    def _add_trace_item(self, trace_id: int, item: EvidenceItem, rank: int) -> None:
        try:
            MysqlRetrievalTraceStore(self.conn).add_item(
                trace_id,
                {
                    "source_type": item.source_type,
                    "source_id": item.source_id,
                    "chapter_id": item.chapter_id or 0,
                    "evidence_level": item.evidence_level.value,
                    "rank": rank,
                    "selected_for_answer": True,
                },
            )
        except Exception as exc:
            logger.warning("Failed to add analyze trace item %d: %s", rank, exc)

    def _build_analysis(
        self,
        analysis_type: str,
        target: str,
        summary: str,
        key_points: list[dict[str, Any]],
        evidence: list[EvidenceItem],
        limitations: list[str],
    ) -> dict[str, Any]:
        return {
            "analysis_type": analysis_type,
            "target": target,
            "summary": summary,
            "key_points": key_points,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "limitations": limitations,
        }

    async def _synthesize_analysis(
        self,
        request: ReaderRequest,
        analysis: dict[str, Any],
        evidence: list[EvidenceItem],
    ) -> dict[str, Any]:
        if not evidence:
            return analysis
        evidence_lines = []
        for idx, item in enumerate(evidence[:8], start=1):
            excerpt = _clean_text(item.excerpt, 220)
            evidence_lines.append(
                f"E{idx}. {item.source_type}#{item.source_id}: {excerpt}"
            )
        draft_points = []
        for idx, point in enumerate(analysis.get("key_points", [])[:6], start=1):
            draft_points.append(f"{idx}. {point.get('claim', '')}")
        prompt = f"""请基于给定证据，写出面向读者的中文小说分析结果。

目标：{analysis.get('target')}
分析类型：{analysis.get('analysis_type')}
用户问题：{request.question}

已有结构化线索：
{chr(10).join(draft_points) or '无'}

证据：
{chr(10).join(evidence_lines)}

要求：
- 最终结果要像自然回答，不要输出字段名、内部类型或调试格式。
- 先给 2-4 句话的综合判断，再给 2-4 条关键结论。
- 可以进行文学分析，但每个结论必须能被上面的证据支撑。
- 不要大段复述原文；引用证据只作支撑。
- 不确定的部分要说明“证据不足以确认”。
"""
        try:
            client = deepseek_client if request.options.provider == "deepseek" else llama_client
            text = await client.chat(
                [
                    {"role": "system", "content": "你是小说阅读分析助手。证据是分析材料，最终输出应是自然、精炼、有判断的读者回答。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.35,
                max_tokens=900,
            )
            text = (text or "").strip()
            if self._looks_like_reader_answer(text):
                synthesized = dict(analysis)
                synthesized["summary"] = text
                synthesized["key_points"] = self._points_from_text(text, analysis.get("key_points", []))
                synthesized["generated_by_model"] = request.options.provider
                return synthesized
        except Exception as exc:
            if "Event loop is closed" not in str(exc):
                logger.warning("Analyze model synthesis failed: %s", exc)
        return analysis

    def _looks_like_reader_answer(self, text: str) -> bool:
        if len(text) < 20:
            return False
        lower = text.lower()
        bad_prefixes = ("summary:", "key_point_", "{", "[")
        if lower.startswith(bad_prefixes):
            return False
        if "source_type" in lower or "evidence_refs" in lower:
            return False
        return True

    def _points_from_text(self, text: str, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for line in text.splitlines():
            clean = re.sub(r"^\s*(?:[-*]|\d+[.、])\s*", "", line).strip()
            if clean and len(clean) >= 8 and clean not in points:
                points.append({"claim": clean, "evidence_refs": []})
            if len(points) >= 4:
                break
        return points or fallback[:4]

    def _character_identity_claim(self, entity: dict[str, Any]) -> str:
        name = entity.get("canonical_name") or "该人物"
        entity_type = str(entity.get("entity_type") or "").upper()
        if entity_type == "CHARACTER":
            return f"{name}是作品中的核心人物之一。"
        if entity_type:
            return f"{name}在结构化档案中被标注为 {entity_type}。"
        return f"{name}在结构化档案中有明确记录。"

    def _compress_description(self, desc: str) -> str:
        parts = [p.strip(" ；;。") for p in re.split(r"[；;。]", desc) if p.strip(" ；;。")]
        if not parts:
            return desc
        deduped: list[str] = []
        for part in parts:
            if part not in deduped:
                deduped.append(part)
        return "；".join(deduped[:3]) + "。"

    def _character_summary(
        self,
        target: str,
        entity: dict[str, Any] | None,
        aliases: list[str],
        relation_summaries: list[str],
        key_points: list[dict[str, Any]],
    ) -> str:
        name = (entity or {}).get("canonical_name") or target or "该人物"
        desc = ""
        for point in key_points:
            claim = point.get("claim", "")
            if claim and not claim.startswith("常见别名") and "关系线索" not in claim and "核心人物" not in claim:
                desc = claim
                break
        clauses = [f"{name}是作品中的重要人物。"]
        if desc:
            clauses.append(desc.rstrip("。"))
        if aliases:
            clauses.append(f"常见别名有{'、'.join(aliases[:3])}")
        if relation_summaries:
            clauses.append(f"关系线索以{relation_summaries[0]}为代表")
        return "；".join(clauses[:3]) + "。"

    def _relation_summary(
        self,
        names: list[str],
        relation_types: list[str],
        has_structured_relation: bool,
        has_evidence: bool,
    ) -> str:
        if not names or not has_evidence:
            return "INSUFFICIENT_EVIDENCE"
        pair = "和".join(names[:2]) if len(names) >= 2 else names[0]
        if has_structured_relation and relation_types:
            unique_types = []
            for relation_type in relation_types:
                if relation_type not in unique_types:
                    unique_types.append(relation_type)
            return f"现有结构化证据显示，{pair}的核心关系是{'、'.join(unique_types[:2])}；检索证据可用于补充具体情节语境。"
        return f"现有检索证据显示，{pair}存在可分析的关系语境，但直接结构化关系记录不足。"

    def _format_answer(self, analysis: dict[str, Any]) -> str:
        if analysis.get("generated_by_model"):
            return str(analysis["summary"]).strip()
        lines = [analysis["summary"]]
        points = analysis.get("key_points", [])[:4]
        if points:
            lines.append("")
            lines.append("关键结论：")
        for i, point in enumerate(points, start=1):
            lines.append(f"{i}. {point.get('claim', '')}")
        if analysis.get("limitations"):
            lines.append("")
            lines.append("限制：" + "；".join(analysis["limitations"]))
        return "\n".join(lines)
