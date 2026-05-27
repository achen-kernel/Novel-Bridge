"""KnowledgePatch service — propose, validate, review.

The service layer enforces:
- No auto-merge
- No automatic entity_merge / entity_split
- High/critical risk patches always go to PENDING_REVIEW
- Review actions: ACCEPT, REJECT, NEEDS_MORE_EVIDENCE, SUPERSEDE
"""

from __future__ import annotations

from app.knowledge_patch.schemas import (
    KnowledgePatch,
    PatchStatus,
    PatchType,
    RiskLevel,
)
from app.knowledge_patch.store import MysqlKnowledgePatchStore
from app.knowledge_patch.validator import (
    CRITICAL_TYPES,
    HIGH_RISK_TYPES,
    KnowledgePatchValidator,
    PatchValidationResult,
)

# Mapping from action string to target PatchStatus
ACTION_STATUS_MAP: dict[str, PatchStatus] = {
    "ACCEPT": PatchStatus.ACCEPTED,
    "REJECT": PatchStatus.REJECTED,
    "NEEDS_MORE_EVIDENCE": PatchStatus.NEEDS_MORE_EVIDENCE,
    "SUPERSEDE": PatchStatus.SUPERSEDED,
}


def _map_action(action: str | None, approved: bool | None) -> str:
    """Resolve action from request. Backward compat with approved: bool."""
    if action and action.upper() in ACTION_STATUS_MAP:
        return action.upper()
    if approved is True:
        return "ACCEPT"
    if approved is False:
        return "REJECT"
    return "REVIEW"


class KnowledgePatchService:
    """Orchestrates KnowledgePatch lifecycle: PROPOSED → PENDING_REVIEW."""

    def __init__(
        self,
        store: MysqlKnowledgePatchStore,
        validator: KnowledgePatchValidator | None = None,
    ) -> None:
        self.store = store
        self.validator = validator or KnowledgePatchValidator()

    def propose(self, patch: KnowledgePatch) -> dict:
        """Validate and propose a KnowledgePatch."""
        result = self.validator.validate(patch)
        if not result.ok:
            return {
                "ok": False,
                "patch_id": None,
                "status": patch.status.value,
                "errors": result.errors,
            }

        if patch.patch_type in CRITICAL_TYPES:
            patch.status = PatchStatus.PROPOSED
        elif patch.patch_type in HIGH_RISK_TYPES:
            patch.status = PatchStatus.PENDING_REVIEW
        else:
            patch.status = PatchStatus.PENDING_REVIEW

        patch_id = self.store.create_patch(patch)
        return {
            "ok": True,
            "patch_id": patch_id,
            "status": patch.status.value,
            "errors": [],
        }

    def review(
        self,
        patch_id: int,
        approved: bool | None = None,
        *,
        action: str = "",
        review_note: str = "",
        reviewed_by: str = "human",
        risk_override: str | None = None,
    ) -> dict:
        """Review a KnowledgePatch with a specific action.

        Supported actions: ACCEPT, REJECT, NEEDS_MORE_EVIDENCE, SUPERSEDE.
        Backward compat: if action is empty, falls back to approved: bool.

        Does NOT auto-merge.  ACCEPTED does not modify formal tables.
        """
        resolved_action = _map_action(action or None, approved)
        target_status = ACTION_STATUS_MAP.get(resolved_action)

        if target_status is None:
            return {
                "ok": False,
                "patch_id": patch_id,
                "status": "",
                "errors": [f"Unknown review action: {action}"],
            }

        result = self.store.update_status(
            patch_id,
            target_status,
            action=resolved_action,
            review_note=review_note,
            reviewed_by=reviewed_by,
            risk_override=risk_override,
        )

        if not result["ok"]:
            return {
                "ok": False,
                "patch_id": patch_id,
                "status": "",
                "errors": result["errors"],
            }

        return {
            "ok": True,
            "patch_id": patch_id,
            "status": target_status.value,
            "errors": [],
        }
