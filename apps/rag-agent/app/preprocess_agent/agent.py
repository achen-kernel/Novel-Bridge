"""PreprocessAgent orchestration — wraps existing pipeline stages.

Each action writes AgentRun/AgentStep and delegates to the existing
app.pipeline module without duplicating its logic.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncio
import hashlib

from app.agent_runtime.run_store import MysqlAgentRunStore
from app.clients.mysql_client import MysqlClient
from app.pipeline.dataset_exporter import DatasetExporter
from app.pipeline.entity_governance_runner import EntityGovernanceRunner
from app.pipeline.fact_pipeline_runner import FactPipelineRunner
from app.pipeline.graph_projector import GraphProjector
from app.pipeline.index_runner import IndexRunner
from app.preprocess_agent.schemas import (
    PreprocessPlanResponse,
    PreprocessPlanStep,
    PreprocessRequest,
    PreprocessResult,
)
from app.preprocess_agent.states import PREPROCESS_TRANSITIONS, PreprocessState
from app.quality.quality_workflow import QualityWorkflow

logger = logging.getLogger(__name__)


def _get_book_counts(conn, book_id: int) -> dict[str, int]:
    """Read-only counts for plan estimated_effect — never writes data."""
    counts: dict[str, int] = {}
    with conn.cursor() as c:
        for qkey, sql in (
            ("chapters", "SELECT COUNT(*) as n FROM novel_chapter WHERE book_id = %s"),
            ("chunks", "SELECT COUNT(*) as n FROM novel_chunk WHERE book_id = %s"),
            ("chapter_facts", "SELECT COUNT(*) as n FROM novel_chapter_fact WHERE book_id = %s"),
            ("entity_profiles", "SELECT COUNT(*) as n FROM novel_entity_profile WHERE book_id = %s"),
            ("relations", "SELECT COUNT(*) as n FROM novel_relation_fact WHERE book_id = %s"),
            ("events", "SELECT COUNT(*) as n FROM novel_event_fact WHERE book_id = %s"),
        ):
            try:
                c.execute(sql, (book_id,))
                row = c.fetchone()
                counts[qkey] = row["n"] if row else 0
            except Exception:
                counts[qkey] = -1
    return counts


def _compute_confirm_token(
    book_id: int,
    start_state: str,
    target_state: str,
    dangerous_states: list[str],
) -> str:
    """Deterministic SHA256 token for dangerous action guard.

    This is a safety guardrail, not an auth system.  The real permission
    layer belongs in the Java/product API boundary.
    """
    raw = f"{book_id}|{start_state}|{target_state}|{sorted(dangerous_states)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_dangerous_states(
    start_idx: int,
    target_idx: int,
    all_states: list,
    plan_meta: dict,
    handlers: dict,
) -> tuple[list[str], list[str]]:
    """Return (dangerous_state_values, confirm_required_state_values)."""
    dangerous: list[str] = []
    confirm_req: list[str] = []
    for idx in range(start_idx + 1, target_idx + 1):
        state = all_states[idx]
        meta = plan_meta.get(state)
        handler = handlers.get(state)
        if meta is None or handler is None:
            continue
        if meta.get("required_confirmation"):
            confirm_req.append(state.value)
        if meta.get("danger_level") in ("high", "critical"):
            dangerous.append(state.value)
    return dangerous, confirm_req


def _estimate_effect(state: "PreprocessState", counts: dict[str, int]) -> dict[str, int]:
    """Estimate the effect of an action based on read-only counts (dry-run)."""
    if state.value == "CHAPTER_FACTS_BUILT":
        return {
            "chapters_to_process": counts.get("chapters", 0),
            "existing_facts": counts.get("chapter_facts", 0),
        }
    if state.value == "ENTITIES_GOVERNED":
        return {
            "chapters_to_govern": counts.get("chapters", 0),
            "existing_profiles": counts.get("entity_profiles", 0),
        }
    if state.value == "QUALITY_CHECKED":
        return {
            "entities_to_normalize": counts.get("entity_profiles", 0),
            "relations_to_dedup": counts.get("relations", 0),
            "events_to_summarize": counts.get("events", 0),
        }
    if state.value == "INDEXED":
        return {
            "chunks_to_index": counts.get("chunks", 0),
            "facts_to_index": counts.get("chapter_facts", 0),
        }
    if state.value == "GRAPH_PROJECTED":
        return {
            "entities_to_project": counts.get("entity_profiles", 0),
            "relations_to_project": counts.get("relations", 0),
            "events_to_project": counts.get("events", 0),
        }
    if state.value == "DATASET_EXPORTED":
        return {
            "facts_available": counts.get("chapter_facts", 0),
        }
    return {}


class PreprocessAgent:
    """@NB-ENTRYPOINT Stage 3C wrapper around existing pipeline stages.

    Usage:
        agent = PreprocessAgent(db_client)
        result = await agent.run(PreprocessRequest(
            book_id=6,
            start_state=PreprocessState.CHAPTER_FACTS_BUILT,
            target_state=PreprocessState.INDEXED,
        ))
    """

    # Map PreprocessState → handler method name
    ACTION_HANDLERS: dict[PreprocessState, str] = {
        PreprocessState.CHAPTER_FACTS_BUILT: "_action_build_chapter_facts",
        PreprocessState.ENTITIES_GOVERNED: "_action_govern_entities",
        PreprocessState.QUALITY_CHECKED: "_action_run_quality",
        PreprocessState.INDEXED: "_action_index_retrieval",
        PreprocessState.GRAPH_PROJECTED: "_action_project_graph",
        PreprocessState.DATASET_EXPORTED: "_action_export_dataset",
    }

    # Static metadata for each action's danger level and effect description.
    # Used by plan() — does NOT execute any pipeline logic.
    ACTION_PLAN_META: dict[PreprocessState, dict[str, Any]] = {
        PreprocessState.CHAPTER_FACTS_BUILT: {
            "danger_level": "high",
            "description": "Build ChapterFacts from extracted chunk data. "
                           "May add or overwrite fact records per chapter.",
            "required_confirmation": True,
        },
        PreprocessState.ENTITIES_GOVERNED: {
            "danger_level": "high",
            "description": "Run alias decisions, entity profile building, "
                           "chapter views. Modifies entity governance tables.",
            "required_confirmation": True,
        },
        PreprocessState.QUALITY_CHECKED: {
            "danger_level": "high",
            "description": "Entity name normalization, relation dedup, event "
                           "summarization. Directly modifies quality tables.",
            "required_confirmation": True,
        },
        PreprocessState.INDEXED: {
            "danger_level": "medium",
            "description": "Index chunks + ChapterFacts into Qdrant. "
                           "May add duplicate vectors if already indexed.",
            "required_confirmation": True,
        },
        PreprocessState.GRAPH_PROJECTED: {
            "danger_level": "critical",
            "description": "Project entities/relations/events into Neo4j. "
                           "clear_first=True will delete existing graph data.",
            "required_confirmation": True,
        },
        PreprocessState.DATASET_EXPORTED: {
            "danger_level": "medium",
            "description": "Export reviewed ChapterFacts as JSONL. "
                           "May overwrite existing export files.",
            "required_confirmation": False,
        },
    }

    def __init__(self, db: MysqlClient) -> None:
        self.db = db

    async def plan(self, book_id: int, start_state: PreprocessState,
                   target_state: PreprocessState) -> PreprocessPlanResponse:
        """Dry-run: enumerate steps without executing or writing any data."""
        all_states = list(PreprocessState)
        try:
            start_idx = all_states.index(start_state)
            target_idx = all_states.index(target_state)
        except ValueError:
            return PreprocessPlanResponse(
                book_id=book_id,
                start_state=start_state.value,
                target_state=target_state.value,
                warnings=["Invalid state value"],
            )

        if start_idx > target_idx:
            return PreprocessPlanResponse(
                book_id=book_id,
                start_state=start_state.value,
                target_state=target_state.value,
                warnings=["start_state is after target_state — nothing to do"],
            )

        steps: list[PreprocessPlanStep] = []
        has_high = False
        has_critical = False

        # Read-only data counts for estimated_effect
        conn = self.db.connect()
        counts = _get_book_counts(conn, book_id)

        for idx in range(start_idx + 1, target_idx + 1):
            state = all_states[idx]
            meta = self.ACTION_PLAN_META.get(state)
            handler = self.ACTION_HANDLERS.get(state)

            if meta is None or handler is None:
                steps.append(PreprocessPlanStep(
                    action=state.value,
                    will_run=False,
                    skip_reason=f"Action not implemented for state {state.value}",
                    danger_level="low",
                    required_confirmation=False,
                ))
                continue

            dl = meta["danger_level"]
            if dl == "high":
                has_high = True
            elif dl == "critical":
                has_critical = True

            estimated = _estimate_effect(state, counts)
            ws: list[str] = []
            if not estimated:
                ws.append("Estimated effect is empty — needs_schema_support may apply")

            steps.append(PreprocessPlanStep(
                action=state.value,
                will_run=True,
                skip_reason="",
                danger_level=dl,
                required_confirmation=meta["required_confirmation"],
                estimated_effect=estimated,
                needs_schema_support=False,  # overridden below if needed
                warnings=ws,
            ))

            # Flag needs_schema_support for actions that lack version tracking fields
            if state in (PreprocessState.CHAPTER_FACTS_BUILT,):
                ws.append(
                    "Idempotency check requires pipeline_version/prompt_version/"
                    "schema_version fields which are not yet tracked"
                )
                steps[-1].needs_schema_support = True

        # Compute confirm token if there are dangerous actions
        dangerous_actions, confirm_actions = _get_dangerous_states(
            start_idx, target_idx, all_states,
            self.ACTION_PLAN_META, self.ACTION_HANDLERS,
        )
        required_token = ""
        hint = ""
        if confirm_actions:
            required_token = _compute_confirm_token(
                book_id, start_state.value, target_state.value, dangerous_actions,
            )
            hint = (
                f"This plan contains {len(confirm_actions)} action(s) that require confirmation: "
                f"{', '.join(confirm_actions)}. "
                f"Pass confirm_token='{required_token}' to execute."
            )

        return PreprocessPlanResponse(
            book_id=book_id,
            start_state=start_state.value,
            target_state=target_state.value,
            steps=steps,
            has_high_risk=has_high,
            has_critical_risk=has_critical,
            required_confirm_token=required_token,
            confirmation_hint=hint,
        )

    async def run(self, request: PreprocessRequest) -> PreprocessResult:
        """Walk from start_state to target_state, executing handlers for each."""
        conn = self.db.connect()
        run_store = MysqlAgentRunStore(conn)
        completed: list[str] = []
        errors: list[str] = []

        # ---- Resolve the state chain from start to target ----
        all_states = list(PreprocessState)
        try:
            start_idx = all_states.index(request.start_state)
            target_idx = all_states.index(request.target_state)
        except ValueError as e:
            return PreprocessResult(
                book_id=request.book_id,
                status=PreprocessState.FAILED,
                errors=[f"Invalid state in request: {e}"],
            )

        if start_idx > target_idx:
            return PreprocessResult(
                book_id=request.book_id,
                status=PreprocessState.FAILED,
                errors=[
                    f"start_state {request.start_state} is after "
                    f"target_state {request.target_state}"
                ],
            )

        if start_idx == target_idx:
            # Nothing to do
            return PreprocessResult(
                book_id=request.book_id,
                status=request.start_state,
                completed_actions=completed,
            )

        # ---- Confirm token guard (4B.2) ----
        dangerous_actions, confirm_actions = _get_dangerous_states(
            start_idx, target_idx, all_states,
            self.ACTION_PLAN_META, self.ACTION_HANDLERS,
        )
        if confirm_actions:
            expected_token = _compute_confirm_token(
                request.book_id,
                request.start_state.value,
                request.target_state.value,
                dangerous_actions,
            )
            if not request.confirm_token:
                return PreprocessResult(
                    book_id=request.book_id,
                    status=PreprocessState.NEED_REVIEW,
                    errors=[
                        f"Dangerous action(s) {confirm_actions} require confirm_token. "
                        f"Plan first or pass confirm_token='{expected_token}'."
                    ],
                    required_confirm_token=expected_token,
                )
            if request.confirm_token != expected_token:
                return PreprocessResult(
                    book_id=request.book_id,
                    status=PreprocessState.FAILED,
                    errors=[
                        f"Confirm token mismatch. Expected '{expected_token}', "
                        f"got '{request.confirm_token}'."
                    ],
                    required_confirm_token=expected_token,
                )

        # ---- Create the agent run ----
        run_id = run_store.create_run(
            agent_name="PreprocessAgent",
            mode=f"{request.start_state.value}->{request.target_state.value}",
            payload={
                "book_id": request.book_id,
                "start_state": request.start_state.value,
                "target_state": request.target_state.value,
                "options": request.options,
            },
        )

        # ---- Walk through states, executing handlers ----
        target_reached = False
        try:
            for idx in range(start_idx + 1, target_idx + 1):
                state = all_states[idx]
                handler_name = self.ACTION_HANDLERS.get(state)
                if handler_name is None:
                    # No handler for this state — just skip (no-op transition)
                    logger.info("No handler for state %s, skipping", state)
                    continue

                handler = getattr(self, handler_name, None)
                if handler is None:
                    raise RuntimeError(
                        f"Handler {handler_name} not implemented for {state}"
                    )

                step_id = run_store.create_step(
                    run_id,
                    state.value,
                    payload={
                        "book_id": request.book_id,
                        "state": state.value,
                        "options": request.options,
                    },
                    step_order=idx,
                )

                try:
                    result: dict[str, Any] = await handler(request.book_id)
                    # Sync connection after handler — some pipeline modules
                    # (e.g. QualityWorkflow) may close the shared connection.
                    conn = self.db.connect()
                    run_store = MysqlAgentRunStore(conn)
                    run_store.finish_step(
                        step_id,
                        "SUCCESS",
                        payload=result,
                    )
                    completed.append(state.value)
                except Exception as e:
                    logger.exception("Action %s failed for book %s", state.value, request.book_id)
                    # Sync connection before writing failure
                    try:
                        conn = self.db.connect()
                        run_store = MysqlAgentRunStore(conn)
                    except Exception:
                        pass
                    run_store.finish_step(
                        step_id,
                        "FAILED",
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                    run_store.finish_run(
                        run_id,
                        "FAILED",
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )
                    return PreprocessResult(
                        book_id=request.book_id,
                        status=PreprocessState.FAILED,
                        run_id=run_id,
                        completed_actions=completed,
                        errors=[f"{state.value} failed: {e}"],
                    )

            target_reached = True

        except Exception as e:
            logger.exception("PreprocessAgent run failed")
            run_store.finish_run(
                run_id,
                "FAILED",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return PreprocessResult(
                book_id=request.book_id,
                status=PreprocessState.FAILED,
                run_id=run_id,
                completed_actions=completed,
                errors=[str(e)],
            )

        # ---- Sync connection before finishing run ----
        conn = self.db.connect()
        run_store = MysqlAgentRunStore(conn)

        # ---- Finish run ----
        final_state = request.target_state if target_reached else request.start_state
        run_store.finish_run(
            run_id,
            "SUCCESS" if target_reached else "FAILED",
            payload={
                "book_id": request.book_id,
                "completed_actions": completed,
                "final_state": final_state.value,
            },
        )
        return PreprocessResult(
            book_id=request.book_id,
            status=final_state,
            run_id=run_id,
            completed_actions=completed,
            errors=errors,
        )

    # ---- Action handlers ----

    async def _action_build_chapter_facts(self, book_id: int) -> dict[str, Any]:
        """BUILD_CHAPTER_FACTS: wrap FactPipelineRunner.process_book().

        The pipeline internally creates its own AgentRun/AgentStep records
        via ModelRunStore.  The PreprocessAgent step wraps the entire
        pipeline call as one observable unit.
        """
        runner = FactPipelineRunner(self.db, use_model=True)
        result = await runner.process_book(book_id)
        if result.get("status") == "error":
            raise RuntimeError(result.get("error", "Unknown pipeline error"))
        return {
            "book_id": book_id,
            "chapters_processed": result.get("chapters_processed", 0),
            "success_count": result.get("success_count", 0),
            "pipeline_run_id": result.get("run_id"),
        }

    async def _action_index_retrieval(self, book_id: int) -> dict[str, Any]:
        """INDEX_RETRIEVAL: wrap IndexRunner.index_book().

        Vectorizes chunks + ChapterFacts and indexes into Qdrant.
        """
        runner = IndexRunner(self.db)
        result = await runner.index_book(book_id, reindex=False)
        if result.get("status") == "error":
            raise RuntimeError(result.get("error", "Unknown index error"))
        return {
            "book_id": book_id,
            "chunks_indexed": result.get("chunks_indexed", 0),
            "facts_indexed": result.get("facts_indexed", 0),
            "failed": result.get("failed", 0),
        }

    async def _action_govern_entities(self, book_id: int) -> dict[str, Any]:
        """GOVERN_ENTITIES: wrap EntityGovernanceRunner.process_book().

        Runs alias decision, entity profile building, chapter views.
        Synchronous — runs in thread pool to avoid blocking the event loop.
        """
        runner = EntityGovernanceRunner(self.db)

        def _run() -> dict[str, Any]:
            return runner.process_book(book_id)

        result = await asyncio.to_thread(_run)
        if result.get("status") == "error":
            raise RuntimeError(result.get("error", "Unknown governance error"))
        return {
            "book_id": book_id,
            "profiles_created": result.get("profiles_created", 0),
            "decisions_made": result.get("decisions_made", 0),
            "pipeline_run_id": result.get("run_id"),
        }

    async def _action_run_quality(self, book_id: int) -> dict[str, Any]:
        """RUN_QUALITY: wrap QualityWorkflow.run_all().

        Runs entity name normalizer + relation deduper + event summarizer.
        Uses dry_run=False to actually apply changes.
        """
        workflow = QualityWorkflow(self.db)
        result = await workflow.run_all(
            book_id=book_id,
            dry_run=False,
            use_deepseek=False,
        )
        if result.get("status") != "ok":
            raise RuntimeError(result.get("message", "Unknown quality error"))
        changes = result.get("summary", {}).get("changes", {})
        return {
            "book_id": book_id,
            "entity_names_synced": changes.get("entity_name_normalizer", 0),
            "relations_deduped": changes.get("relation_deduper", 0),
            "event_summaries_filled": changes.get("event_summarizer", 0),
        }

    async def _action_project_graph(self, book_id: int) -> dict[str, Any]:
        """PROJECT_GRAPH: wrap GraphProjector.project_book().

        Projects MySQL entities/relations/events into Neo4j.
        Synchronous — runs in thread pool.
        """
        conn = self.db.connect()
        projector = GraphProjector(conn)

        def _run() -> dict[str, Any]:
            return projector.project_book(book_id, clear_first=True)

        result = await asyncio.to_thread(_run)
        return {
            "book_id": book_id,
            "entities_projected": result.get("entities_created", 0),
            "relations_projected": result.get("relations_created", 0),
            "events_projected": result.get("events_created", 0),
        }

    async def _action_export_dataset(self, book_id: int) -> dict[str, Any]:
        """EXPORT_DATASET: wrap DatasetExporter.export_chapter_facts().

        Exports reviewed ChapterFacts as JSONL training data.
        """
        exporter = DatasetExporter(self.db)
        result = exporter.export_chapter_facts(book_id=book_id)
        if result.get("status") == "error":
            raise RuntimeError(result.get("message", "Unknown export error"))
        return {
            "book_id": book_id,
            "samples": result.get("samples", 0),
            "file": result.get("file", ""),
        }
