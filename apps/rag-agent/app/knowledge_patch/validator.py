"""KnowledgePatch validation rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.knowledge_patch.schemas import KnowledgePatch, PatchType, RiskLevel


HIGH_RISK_TYPES = {
    PatchType.ALIAS_ADD,
    PatchType.ALIAS_BLOCK,
    PatchType.ENTITY_SPLIT,
    PatchType.ENTITY_MERGE,
}

CRITICAL_TYPES = {
    PatchType.ENTITY_SPLIT,
    PatchType.ENTITY_MERGE,
}


class PatchValidationResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)


class KnowledgePatchValidator:
    """@NB-EVIDENCE validates candidate patches before review."""

    def validate(self, patch: KnowledgePatch) -> PatchValidationResult:
        errors: list[str] = []
        if not patch.evidence:
            errors.append("KnowledgePatch requires at least one L2 evidence item.")
        if patch.patch_type in HIGH_RISK_TYPES and patch.risk_level not in {
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        }:
            errors.append(f"{patch.patch_type} must be high or critical risk.")
        if patch.patch_type in CRITICAL_TYPES and patch.risk_level != RiskLevel.CRITICAL:
            errors.append(f"{patch.patch_type} must be critical risk.")
        if patch.patch_type in CRITICAL_TYPES and not patch.target_id:
            errors.append(f"{patch.patch_type} requires target_id.")
        return PatchValidationResult(ok=not errors, errors=errors)

