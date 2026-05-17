"""
Validate that evidence_text appears in the source chunk text.
"""


def evidence_in_chunk(evidence_text: str, chunk_text: str) -> bool:
    """Check if evidence_text is a substring of chunk_text."""
    if not evidence_text or not chunk_text:
        return False
    return evidence_text.strip() in chunk_text


def validate_evidence_list(entities: list, chunk_text: str) -> list:
    """Return list of entity names where evidence_text is NOT found."""
    missing = []
    for ent in entities:
        if not evidence_in_chunk(ent.get("evidence_text", ""), chunk_text):
            missing.append(ent.get("name", "UNKNOWN"))
    return missing
