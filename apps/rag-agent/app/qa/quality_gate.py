"""@NB-ENTRYPOINT P1 Retrieval Quality Gate — decision tree for retry/fallback.

Evaluates retrieval results and decides: pass → generator | retry → broader rewrite | fail → INSUFFICIENT_EVIDENCE.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

MIN_CONTEXTS = 3      # Minimum contexts to proceed
MIN_SCORE = 0.4       # Minimum relevance score to count as "good"
MAX_RETRIES = 1       # Max broader retries before failing


class GateDecision(str, Enum):
    PASS = "pass"
    RETRY_BROADER = "retry_broader"
    RETRY_ENTITY = "retry_entity"
    FAIL_INSUFFICIENT = "fail_insufficient"


@dataclass
class GateResult:
    decision: GateDecision
    contexts: list[dict] = field(default_factory=list)
    reason: str = ""
    needs_broader: bool = False  # True → caller should rewrite broader and retry
    entity_name: str | None = None  # Set when RETRY_ENTITY, for brute-force LIKE


def evaluate(
    contexts: list[dict],
    entity_name: str | None = None,
    retry_count: int = 0,
) -> GateResult:
    """Evaluate retrieval quality and decide next action.

    Decision tree (from redesign-plan.md):
    1. len(contexts) >= MIN_CTX?
       ├── YES → max_score >= MIN_SCORE? → PASS
       │         └── NO → entity brute-force LIKE? → RETRY_ENTITY / FAIL
       └── NO  → retry_count < MAX_RETRIES? → RETRY_BROADER
                 └── retried already → FAIL_INSUFFICIENT
    """
    if not contexts:
        if retry_count < MAX_RETRIES:
            return GateResult(decision=GateDecision.RETRY_BROADER, reason="检索结果为空，需 broader 重试", needs_broader=True)
        return GateResult(decision=GateDecision.FAIL_INSUFFICIENT, reason="检索结果为空，已重试仍不足")

    max_score = max((c.get("score") or 0) for c in contexts[:MIN_CONTEXTS])
    has_good = any((c.get("score") or 0) >= MIN_SCORE for c in contexts[:MIN_CONTEXTS])

    # PASS: enough contexts with good scores
    if len(contexts) >= MIN_CONTEXTS and has_good:
        return GateResult(decision=GateDecision.PASS, contexts=contexts, reason=f"通过: {len(contexts)} 条, 最高分={max_score:.2f}")

    # Scores too low or not enough contexts — try entity brute-force if available
    if entity_name:
        return GateResult(decision=GateDecision.RETRY_ENTITY, reason=f"分低或量不足({len(contexts)}条, max={max_score:.2f}), 尝试实体搜索", entity_name=entity_name)

    # No entity to fall back to — broader retry or fail
    if retry_count < MAX_RETRIES:
        return GateResult(decision=GateDecision.RETRY_BROADER, reason=f"上下文不足({len(contexts)}条, max={max_score:.2f}), broader 重试", needs_broader=True)

    return GateResult(decision=GateDecision.FAIL_INSUFFICIENT, reason=f"已重试仍不足({len(contexts)}条, max={max_score:.2f})")
