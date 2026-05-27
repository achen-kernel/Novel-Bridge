"""Smoke test for Stage 3 Agent skeleton.

Run from apps/rag-agent:
    python scripts/test/test_agent_runtime_skeleton.py
"""

import asyncio
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.agent_runtime import StateMachine, ToolRegistry, TransitionError
from app.agent_runtime.citation_verifier import CitationVerifier
from app.agent_runtime.schemas import EvidenceItem, EvidenceLevel
from app.agent_runtime.tool_executor import ToolExecutor
from app.knowledge_patch.schemas import KnowledgePatch, PatchType, RiskLevel
from app.knowledge_patch.validator import KnowledgePatchValidator
from app.preprocess_agent.states import PREPROCESS_TRANSITIONS, PreprocessState
from app.reader_agent.schemas import ReaderRequest
from app.reader_agent.states import READER_TRANSITIONS, ReaderState


def test_state_machines():
    reader = StateMachine(
        ReaderState.NEW_TASK,
        READER_TRANSITIONS,
    )
    assert reader.transition(ReaderState.INTENT_CLASSIFIED) == ReaderState.INTENT_CLASSIFIED.value
    try:
        reader.transition(ReaderState.RESPONDED)
    except TransitionError:
        pass
    else:
        raise AssertionError("illegal reader transition was accepted")

    preprocess = StateMachine(
        PreprocessState.NEW,
        PREPROCESS_TRANSITIONS,
    )
    assert preprocess.transition(PreprocessState.SOURCE_REGISTERED) == PreprocessState.SOURCE_REGISTERED.value


async def test_tool_executor():
    registry = ToolRegistry()

    @registry.register("echo")
    def echo(value: str):
        return {"value": value}

    record = await ToolExecutor(registry).execute("echo", payload={"value": "ok"})
    assert record.status == "SUCCESS"
    assert record.output_json == {"value": "ok"}


def test_citation_and_patch_validation():
    evidence = EvidenceItem(
        source_type="chunk",
        source_id=1,
        chapter_id=1,
        excerpt="sample",
        evidence_level=EvidenceLevel.DIRECT,
        relevance_score=1.0,
    )
    assert CitationVerifier().verify([evidence]).ok

    patch = KnowledgePatch(
        book_id=1,
        patch_type=PatchType.ENTITY_MERGE,
        target_type="entity",
        target_id=1,
        payload={"merge_with": 2},
        evidence=[evidence],
        risk_level=RiskLevel.CRITICAL,
    )
    assert KnowledgePatchValidator().validate(patch).ok


def test_reader_schema():
    req = ReaderRequest(book_id=1, question="问题")
    assert req.mode == "answer"
    assert req.options.require_citations is True
    analyze_req = ReaderRequest(
        mode="analyze",
        book_id=1,
        question="分析人物",
        analysis_type="character",
        target_name="孙悟空",
    )
    assert analyze_req.analysis_type == "character"
    assert analyze_req.target_name == "孙悟空"


def test_store_imports():
    from app.agent_runtime.run_store import MysqlAgentRunStore
    from app.agent_runtime.model_call_store import MysqlModelCallStore
    from app.agent_runtime.trace_store import MysqlRetrievalTraceStore
    # Verify classes have expected constructor signatures
    import inspect
    assert "conn" in inspect.signature(MysqlAgentRunStore.__init__).parameters
    assert "conn" in inspect.signature(MysqlModelCallStore.__init__).parameters
    assert "conn" in inspect.signature(MysqlRetrievalTraceStore.__init__).parameters
    print("  [PASS] store modules import & constructors OK")


async def main():
    test_state_machines()
    await test_tool_executor()
    test_citation_and_patch_validation()
    test_reader_schema()
    test_store_imports()
    print("\nagent runtime skeleton smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())
