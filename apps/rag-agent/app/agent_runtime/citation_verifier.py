"""Citation verification contract.

The first implementation is deliberately conservative: a citation is valid only
when it points to an allowed L2 source and carries an id.

Relaxed for knowledge-source types (entity/relation/event/citation) which may
reference entities by name rather than numeric ID — source_id=0 is acceptable
for those types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent_runtime.schemas import EvidenceItem

# Source types that may legitimately have source_id=0 because they reference
# named entities rather than numeric record IDs.
_SOURCE_TYPES_ALLOWING_ZERO_ID = frozenset({
    "entity",
    "relation",
    "event",
    "citation",
    "chapter_fact",
})


class CitationVerificationResult(BaseModel):
    ok: bool
    checked_count: int = 0
    errors: list[str] = Field(default_factory=list)


class CitationVerifier:
    """@NB-EVIDENCE verifies that answer citations point to L2 evidence sources."""

    def verify(self, evidence: list[EvidenceItem]) -> CitationVerificationResult:
        errors: list[str] = []
        for item in evidence:
            st = item.source_type
            if st not in _SOURCE_TYPES_ALLOWING_ZERO_ID and item.source_id <= 0:
                errors.append(
                    f"{st} citation has invalid source_id={item.source_id} "
                    f"(expected positive id for {st} type)"
                )
            if not item.excerpt:
                errors.append(f"{st}:{item.source_id} has empty excerpt")
        return CitationVerificationResult(
            ok=not errors,
            checked_count=len(evidence),
            errors=errors,
        )
