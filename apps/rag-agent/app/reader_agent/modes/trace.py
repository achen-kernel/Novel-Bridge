"""ReaderAgent trace mode, minimal evidence-backed timeline."""

from __future__ import annotations

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
from app.reader_agent.schemas import ReaderRequest, ReaderResponse
from app.reader_agent.states import ReaderState

logger = logging.getLogger(__name__)


class TraceMode:
    """Minimal trace mode for character/item/setting targets.

    It builds a chapter-ordered timeline from existing chunks and ChapterFacts.
    No graph reasoning or model-generated facts are used in this first slice.
    """

    def __init__(self, conn=None) -> None:
        self.conn = conn

    async def run(self, request: ReaderRequest) -> ReaderResponse:
        if self.conn is None:
            return ReaderResponse(
                mode="trace",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent trace mode requires a MySQL connection."],
            )

        target_name = (request.target_name or request.target or "").strip()
        target_type = request.trace_target_type or request.target_type or "character"
        if target_type not in {"character", "item", "setting"}:
            return ReaderResponse(
                mode="trace",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent trace mode only supports character, item, and setting."],
            )
        if not target_name:
            return ReaderResponse(
                mode="trace",
                status=ReaderState.NEED_FOLLOWUP,
                errors=["ReaderAgent trace mode requires target_name."],
            )

        run_store = MysqlAgentRunStore(self.conn)
        trace_store = MysqlRetrievalTraceStore(self.conn)
        tool_store = MysqlToolCallStore(self.conn)

        run_id = run_store.create_run(
            agent_name="ReaderAgent",
            mode="trace",
            payload={
                "book_id": request.book_id,
                "question": request.question,
                "target_name": target_name,
                "target_type": target_type,
                "chapter_range": request.chapter_range,
                "options": request.options.model_dump(),
            },
        )
        step_id = run_store.create_step(
            run_id,
            "EVIDENCE_SEARCH",
            payload={
                "book_id": request.book_id,
                "target_name": target_name,
                "target_type": target_type,
                "chapter_range": request.chapter_range,
            },
            step_order=0,
        )
        trace_id = trace_store.create_trace(
            run_id,
            query=request.question or target_name,
            payload={"book_id": request.book_id, "mode": "trace"},
        )

        try:
            evidence, timeline = self._build_timeline(
                request, target_name, target_type, tool_store, run_id, step_id
            )
            for idx, item in enumerate(evidence):
                trace_store.add_item(
                    trace_id,
                    {
                        "source_type": item.source_type,
                        "source_id": item.source_id,
                        "chapter_id": item.chapter_id or 0,
                        "evidence_level": item.evidence_level.value,
                        "rank": idx,
                        "selected_for_answer": True,
                    },
                )
        except Exception as exc:
            logger.exception("ReaderAgent trace failed")
            run_store.finish_step(
                step_id,
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
                mode="trace",
                status=ReaderState.FAILED,
                trace_id=trace_id,
                errors=[f"ReaderAgent trace failed: {exc}"],
            )

        verification = CitationVerifier().verify(evidence)
        status = ReaderState.RESPONDED
        errors: list[str] = []
        if request.options.require_citations and (not evidence or not verification.ok):
            status = ReaderState.INSUFFICIENT_EVIDENCE
            errors.extend(verification.errors or ["No timeline evidence found"])

        draft_step_id = run_store.create_step(
            run_id,
            "DRAFT_READY",
            payload={
                "timeline_count": len(timeline),
                "evidence_count": len(evidence),
                "citation_verification_passed": verification.ok,
                "citation_verification_errors": verification.errors,
            },
            step_order=1,
        )
        answer = await self._format_answer(request, target_name, target_type, timeline, evidence)
        run_store.finish_step(draft_step_id, "SUCCESS", payload={"answer_preview": answer[:200]})
        run_store.finish_step(step_id, "SUCCESS", payload={
            "timeline_count": len(timeline),
            "timeline_preview": timeline[:8],
        })
        run_store.finish_run(
            run_id,
            status.value,
            payload={
                "target_name": target_name,
                "target_type": target_type,
                "timeline_count": len(timeline),
                "timeline_preview": timeline[:12],
                "presentation_summary": answer,
                "evidence_count": len(evidence),
                "trace_id": trace_id,
            },
        )

        return ReaderResponse(
            run_id=run_id,
            mode="trace",
            status=status,
            answer=answer if status == ReaderState.RESPONDED else "INSUFFICIENT_EVIDENCE",
            citations=evidence,
            evidence=evidence,
            trace_id=trace_id,
            patches=[],
            timeline=timeline if status == ReaderState.RESPONDED else [],
            errors=errors,
        )

    def _build_timeline(
        self,
        request: ReaderRequest,
        target_name: str,
        target_type: str,
        tool_store: MysqlToolCallStore,
        run_id: int,
        step_id: int,
    ) -> tuple[list[EvidenceItem], list[dict[str, Any]]]:
        call_id = tool_store.create_tool_call(
            "timeline_lookup",
            agent_run_id=run_id,
            agent_step_id=step_id,
            input_json={
                "book_id": request.book_id,
                "target_name": target_name,
                "target_type": target_type,
                "chapter_range": request.chapter_range,
            },
        )
        evidence: list[EvidenceItem] = []
        timeline: list[dict[str, Any]] = []

        chapter_min, chapter_max = self._chapter_bounds(request.chapter_range)
        relation_targets = self._relation_targets(target_name, request.question)
        if len(relation_targets) >= 2:
            relation_evidence, relation_timeline = self._relation_timeline(
                request, relation_targets[:2], chapter_min, chapter_max
            )
            offset = len(evidence)
            evidence.extend(relation_evidence)
            for item in relation_timeline:
                item["evidence_refs"] = [offset + ref for ref in item.get("evidence_refs", [])]
                timeline.append(item)

        with self.conn.cursor() as cursor:
            params: list[Any] = [request.book_id, f"%{target_name}%"]
            chapter_filter = ""
            if chapter_min is not None:
                chapter_filter += " AND chapter_id >= %s"
                params.append(chapter_min)
            if chapter_max is not None:
                chapter_filter += " AND chapter_id <= %s"
                params.append(chapter_max)
            params.append(min(request.options.top_k, 20))
            cursor.execute(
                f"""SELECT id, chapter_id, content
                    FROM novel_chunk
                    WHERE book_id = %s AND content LIKE %s {chapter_filter}
                    ORDER BY chapter_id, id
                    LIMIT %s""",
                params,
            )
            chunk_rows = cursor.fetchall()

        for row in chunk_rows:
            excerpt = self._excerpt_around(row.get("content") or "", target_name)
            if not excerpt:
                continue
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="chunk",
                source_id=int(row["id"]),
                chapter_id=row.get("chapter_id"),
                excerpt=excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=0.85,
            ))
            timeline.append({
                "chapter_id": row.get("chapter_id"),
                **self._chapter_meta(row.get("chapter_id")),
                "kind": "target_mention",
                "summary": self._summarize_context(target_name, excerpt, kind="target_mention"),
                "evidence_refs": [idx],
            })

        for fact in self._fact_hits(request.book_id, target_name, chapter_min, chapter_max, request.options.top_k):
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="chapter_fact",
                source_id=int(fact["id"]),
                chapter_id=fact.get("chapter_id"),
                excerpt=fact["excerpt"],
                evidence_level=EvidenceLevel.NEAR,
                relevance_score=0.65,
            ))
            timeline.append({
                "chapter_id": fact.get("chapter_id"),
                **self._chapter_meta(fact.get("chapter_id")),
                "kind": "chapter_fact",
                "summary": self._summarize_context(target_name, fact["excerpt"], kind="chapter_fact"),
                "evidence_refs": [idx],
            })

        timeline.sort(key=lambda item: (item.get("chapter_id") or 0, item.get("summary") or ""))
        tool_store.finish_tool_call(
            call_id,
            output_json={
                "timeline_count": len(timeline),
                "evidence_count": len(evidence),
                "relation_targets": relation_targets[:2],
            },
        )
        return evidence, timeline[: request.options.top_k]

    def _relation_timeline(
        self,
        request: ReaderRequest,
        names: list[str],
        chapter_min: int | None,
        chapter_max: int | None,
    ) -> tuple[list[EvidenceItem], list[dict[str, Any]]]:
        evidence: list[EvidenceItem] = []
        timeline: list[dict[str, Any]] = []
        a, b = names[0], names[1]
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT *
                   FROM novel_relation_fact
                   WHERE book_id = %s AND status = 'ACTIVE'
                     AND ((source_entity_name LIKE %s AND target_entity_name LIKE %s)
                       OR (source_entity_name LIKE %s AND target_entity_name LIKE %s))
                   ORDER BY first_chapter_id, last_chapter_id, strength DESC, confidence DESC
                   LIMIT 10""",
                (request.book_id, f"%{a}%", f"%{b}%", f"%{b}%", f"%{a}%"),
            )
            relation_rows = cursor.fetchall()

        for row in relation_rows:
            chapter_id = row.get("first_chapter_id") or row.get("last_chapter_id")
            if chapter_min is not None and chapter_id and chapter_id < chapter_min:
                continue
            if chapter_max is not None and chapter_id and chapter_id > chapter_max:
                continue
            excerpt = (
                f"{row.get('source_entity_name')} -{row.get('relation_type')}- "
                f"{row.get('target_entity_name')}"
            )
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="relation",
                source_id=int(row.get("id") or 0),
                chapter_id=chapter_id,
                excerpt=excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=float(row.get("confidence") or 0.75),
            ))
            timeline.append({
                "kind": "relation_state",
                "chapter_id": chapter_id,
                **self._chapter_meta(chapter_id),
                "summary": self._summarize_relation_state(row),
                "evidence_refs": [idx],
                "relation_type": row.get("relation_type"),
            })

        params: list[Any] = [request.book_id, f"%{a}%", f"%{b}%"]
        chapter_filter = ""
        if chapter_min is not None:
            chapter_filter += " AND chapter_id >= %s"
            params.append(chapter_min)
        if chapter_max is not None:
            chapter_filter += " AND chapter_id <= %s"
            params.append(chapter_max)
        params.append(min(request.options.top_k, 10))
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""SELECT id, chapter_id, content
                    FROM novel_chunk
                    WHERE book_id = %s AND content LIKE %s AND content LIKE %s {chapter_filter}
                    ORDER BY chapter_id, id
                    LIMIT %s""",
                params,
            )
            chunk_rows = cursor.fetchall()

        for row in chunk_rows:
            excerpt = self._excerpt_between(row.get("content") or "", a, b)
            if not excerpt:
                continue
            idx = len(evidence)
            evidence.append(EvidenceItem(
                source_type="chunk",
                source_id=int(row["id"]),
                chapter_id=row.get("chapter_id"),
                excerpt=excerpt,
                evidence_level=EvidenceLevel.DIRECT,
                relevance_score=0.8,
            ))
            timeline.append({
                "kind": "relation_context",
                "chapter_id": row.get("chapter_id"),
                **self._chapter_meta(row.get("chapter_id")),
                "summary": self._summarize_relation_context(a, b, excerpt),
                "evidence_refs": [idx],
            })

        return evidence, timeline

    def _fact_hits(
        self,
        book_id: int,
        target_name: str,
        chapter_min: int | None,
        chapter_max: int | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        params: list[Any] = [book_id, f"%{target_name}%", f"%{target_name}%"]
        chapter_filter = ""
        if chapter_min is not None:
            chapter_filter += " AND chapter_id >= %s"
            params.append(chapter_min)
        if chapter_max is not None:
            chapter_filter += " AND chapter_id <= %s"
            params.append(chapter_max)
        params.append(min(top_k, 10))
        with self.conn.cursor() as cursor:
            cursor.execute(
                f"""SELECT id, chapter_id, summary, fact_json
                    FROM novel_chapter_fact
                    WHERE book_id = %s
                      AND (summary LIKE %s OR fact_json LIKE %s) {chapter_filter}
                    ORDER BY chapter_id, id
                    LIMIT %s""",
                params,
            )
            rows = cursor.fetchall()
        hits: list[dict[str, Any]] = []
        for row in rows:
            text = row.get("summary") or row.get("fact_json") or ""
            excerpt = self._excerpt_around(str(text), target_name)
            if excerpt:
                hits.append({"id": row["id"], "chapter_id": row.get("chapter_id"), "excerpt": excerpt})
        return hits

    def _chapter_meta(self, chapter_id: Any) -> dict[str, Any]:
        if not chapter_id:
            return {"chapter_number": None, "chapter_title": ""}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT chapter_number, title FROM novel_chapter WHERE id = %s",
                    (chapter_id,),
                )
                row = cursor.fetchone()
            if not row:
                return {"chapter_number": None, "chapter_title": ""}
            return {
                "chapter_number": row.get("chapter_number"),
                "chapter_title": row.get("title") or "",
            }
        except Exception:
            return {"chapter_number": None, "chapter_title": ""}

    def _chapter_bounds(self, chapter_range: list[int]) -> tuple[int | None, int | None]:
        values = [int(v) for v in chapter_range if isinstance(v, int) and v > 0]
        if not values:
            return None, None
        if len(values) == 1:
            return values[0], values[0]
        return min(values[:2]), max(values[:2])

    def _excerpt_around(self, text: str, target_name: str) -> str:
        text = " ".join(str(text or "").split())
        idx = text.find(target_name)
        if idx < 0:
            return ""
        start = max(0, idx - 80)
        end = min(len(text), idx + len(target_name) + 140)
        return text[start:end]

    def _excerpt_between(self, text: str, a: str, b: str) -> str:
        text = " ".join(str(text or "").split())
        ia = text.find(a)
        ib = text.find(b)
        if ia < 0 or ib < 0:
            return ""
        start = max(0, min(ia, ib) - 80)
        end = min(len(text), max(ia + len(a), ib + len(b)) + 140)
        return text[start:end]

    def _relation_targets(self, target_name: str, question: str) -> list[str]:
        raw = target_name
        if not any(sep in raw for sep in ("和", "与", "、", ",", "，", "/", "|", ";", "；")):
            raw = question if "关系" in question else raw
        for sep in ("和", "与", "、", ",", "，", "/", "|", ";", "；"):
            raw = raw.replace(sep, " ")
        names: list[str] = []
        for token in re.split(r"\s+", raw):
            clean = token.strip()
            for noise in ("追踪", "分析", "关系", "变化", "之间", "的", "在西游记中", "线索"):
                clean = clean.replace(noise, "")
            if 2 <= len(clean) <= 12 and clean not in names:
                names.append(clean)
        return names[:2]

    def _summarize_context(self, target_name: str, excerpt: str, kind: str) -> str:
        text = excerpt or ""
        if kind == "chapter_fact":
            return f"{target_name} 在该章节事实中出现，提供了可追踪的结构化线索。"
        if any(token in text for token in ("师父", "徒弟", "唐僧", "三藏")):
            return f"{target_name} 与取经队伍或师徒关系发生关联。"
        if any(token in text for token in ("保", "救", "护", "随")):
            return f"{target_name} 的行动与保护、同行或任务推进有关。"
        return f"{target_name} 在该处被明确提及，可作为时间线证据。"

    def _summarize_relation_state(self, row: dict[str, Any]) -> str:
        source = row.get("source_entity_name") or "一方"
        target = row.get("target_entity_name") or "另一方"
        relation = row.get("relation_type") or "关系"
        return f"结构化关系记录表明：{source} 与 {target} 存在“{relation}”。"

    def _summarize_relation_context(self, a: str, b: str, excerpt: str) -> str:
        text = excerpt or ""
        if any(token in text for token in ("不保", "怪", "撇", "闷气", "不是")):
            return f"{a} 与 {b} 的关系出现冲突或分离迹象。"
        if any(token in text for token in ("还去保", "去保", "师父", "徒弟", "随", "保护")):
            return f"{a} 与 {b} 的师徒/同行关系得到恢复或继续推进。"
        if any(token in text for token in ("拜", "皈依", "正果", "取经")):
            return f"{a} 与 {b} 的关系被放入取经目标和修行秩序中。"
        return f"原文同时提到 {a} 与 {b}，构成关系变化的语境证据。"

    async def _format_answer(
        self,
        request: ReaderRequest,
        target_name: str,
        target_type: str,
        timeline: list[dict[str, Any]],
        evidence: list[EvidenceItem],
    ) -> str:
        if not timeline:
            return "证据不足：当前没有可追踪的时间线证据。"
        fallback = self._format_rule_answer(target_name, timeline)
        prompt_items = []
        for idx, item in enumerate(timeline[:6], start=1):
            chapter_number = item.get("chapter_number") or item.get("chapter_id") or "未知"
            prompt_items.append(f"{idx}. 第{chapter_number}章：{item.get('summary')}")
        prompt = (
            "请只根据下面的时间线证据，为小说关系追踪生成一个面向读者的中文总结。"
            "要求：先用一句话总括关系变化，再列最多3个阶段；不要复述长原文；不要编造未给出的信息。\n\n"
            f"追踪对象：{target_name} ({target_type})\n"
            + "\n".join(prompt_items)
        )
        try:
            client = deepseek_client if request.options.provider == "deepseek" else llama_client
            text = await client.chat(
                [
                    {"role": "system", "content": "你是小说阅读分析助手，只能基于给定证据做简洁总结。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=480,
            )
            if text and not text.lstrip().startswith('{"error"'):
                return text.strip()
        except Exception as exc:
            if "Event loop is closed" not in str(exc):
                logger.warning("Trace presentation summary failed: %s", exc)
        return fallback

    def _format_rule_answer(self, target_name: str, timeline: list[dict[str, Any]]) -> str:
        lines = [f"{target_name} 的时间线可以概括为：关系先被结构化记录确认，随后在具体情节中呈现互动、冲突或继续同行。"]
        for idx, item in enumerate(timeline[:3], start=1):
            chapter = item.get("chapter_number") or item.get("chapter_id") or "未知"
            title = f"《{item.get('chapter_title')}》" if item.get("chapter_title") else ""
            lines.append(f"{idx}. 第{chapter}章{title}：{item.get('summary')}")
        return "\n".join(lines)
