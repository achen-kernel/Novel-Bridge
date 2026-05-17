"""
Validate structured entity extraction output.

Runs after JSON parse to check:
- Required fields exist
- entity_type is valid enum
- confidence is 0-1
- evidence_text is non-empty
- No empty names
"""

import json
from typing import Optional

VALID_TYPES = {"CHARACTER", "LOCATION", "ITEM", "ORG", "TITLE", "UNKNOWN"}


class ValidationResult:
    def __init__(self, ok: bool = True, errors: list = None, entities: list = None):
        self.ok = ok
        self.errors = errors or []
        self.entities = entities or []

    def add_error(self, error: str):
        self.ok = False
        self.errors.append(error)


def parse_and_validate(raw_output: str) -> ValidationResult:
    """Parse JSON string and validate structure."""
    result = ValidationResult()

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        return ValidationResult(ok=False, errors=[f"JSON parse error: {e}"])

    if not isinstance(data, dict):
        return ValidationResult(ok=False, errors=["Top-level is not a JSON object"])

    entities = data.get("entities", [])
    if not isinstance(entities, list):
        return ValidationResult(ok=False, errors=["'entities' is not an array"])

    valid_entities = []
    for i, ent in enumerate(entities):
        entity_errors = _validate_single_entity(ent, i)
        if entity_errors:
            for err in entity_errors:
                result.add_error(err)
        else:
            valid_entities.append(ent)

    result.entities = valid_entities
    return result


def _validate_single_entity(ent: dict, idx: int) -> list:
    """Validate a single entity dict. Returns list of error strings (empty = valid)."""
    errors = []

    name = ent.get("name", "")
    if not name or not name.strip():
        errors.append(f"Entity #{idx}: 'name' is empty")

    etype = ent.get("type", "")
    if not etype:
        errors.append(f"Entity #{idx} ('{name}'): 'type' is missing")
    elif etype not in VALID_TYPES:
        errors.append(f"Entity #{idx} ('{name}'): invalid type '{etype}', must be one of {VALID_TYPES}")

    evidence = ent.get("evidence_text", "")
    if not evidence or not evidence.strip():
        errors.append(f"Entity #{idx} ('{name}'): 'evidence_text' is empty")

    confidence = ent.get("confidence", -1)
    if confidence is None or not isinstance(confidence, (int, float)):
        errors.append(f"Entity #{idx} ('{name}'): 'confidence' is not a number")
    elif confidence < 0 or confidence > 1:
        errors.append(f"Entity #{idx} ('{name}'): 'confidence' {confidence} out of range [0,1]")

    return errors
