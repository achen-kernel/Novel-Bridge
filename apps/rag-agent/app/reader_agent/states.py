"""ReaderAgent state contract."""

from enum import Enum


class ReaderState(str, Enum):
    NEW_TASK = "NEW_TASK"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    SCOPE_RESOLVED = "SCOPE_RESOLVED"
    PLAN_READY = "PLAN_READY"
    CONTEXT_ROUTED = "CONTEXT_ROUTED"
    CONTEXT_LOADED = "CONTEXT_LOADED"
    EVIDENCE_SEARCHING = "EVIDENCE_SEARCHING"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    DRAFT_READY = "DRAFT_READY"
    VERIFIED = "VERIFIED"
    RESPONDED = "RESPONDED"
    PATCH_DRAFTED = "PATCH_DRAFTED"
    PATCH_VALIDATED = "PATCH_VALIDATED"
    PATCH_PENDING_REVIEW = "PATCH_PENDING_REVIEW"
    NEED_FOLLOWUP = "NEED_FOLLOWUP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


READER_TRANSITIONS = [
    (ReaderState.NEW_TASK, ReaderState.INTENT_CLASSIFIED),
    (ReaderState.INTENT_CLASSIFIED, ReaderState.SCOPE_RESOLVED),
    (ReaderState.SCOPE_RESOLVED, ReaderState.PLAN_READY),
    (ReaderState.PLAN_READY, ReaderState.CONTEXT_ROUTED),
    (ReaderState.CONTEXT_ROUTED, ReaderState.CONTEXT_LOADED),
    (ReaderState.CONTEXT_LOADED, ReaderState.EVIDENCE_SEARCHING),
    (ReaderState.EVIDENCE_SEARCHING, ReaderState.EVIDENCE_COLLECTED),
    (ReaderState.EVIDENCE_COLLECTED, ReaderState.DRAFT_READY),
    (ReaderState.DRAFT_READY, ReaderState.VERIFIED),
    (ReaderState.VERIFIED, ReaderState.RESPONDED),
    (ReaderState.DRAFT_READY, ReaderState.PATCH_DRAFTED),
    (ReaderState.PATCH_DRAFTED, ReaderState.PATCH_VALIDATED),
    (ReaderState.PATCH_VALIDATED, ReaderState.PATCH_PENDING_REVIEW),
]

for _state in list(ReaderState):
    if _state not in {
        ReaderState.RESPONDED,
        ReaderState.FAILED,
        ReaderState.CANCELED,
        ReaderState.INSUFFICIENT_EVIDENCE,
    }:
        READER_TRANSITIONS.extend(
            [
                (_state, ReaderState.NEED_FOLLOWUP),
                (_state, ReaderState.INSUFFICIENT_EVIDENCE),
                (_state, ReaderState.FAILED),
                (_state, ReaderState.CANCELED),
            ]
        )
