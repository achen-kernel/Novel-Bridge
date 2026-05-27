"""Shared action naming contracts."""

from enum import Enum


class RuntimeAction(str, Enum):
    CLASSIFY_INTENT = "classify_intent"
    ROUTE_CONTEXT = "route_context"
    LOAD_CONTEXT = "load_context"
    SEARCH_EVIDENCE = "search_evidence"
    VERIFY_CITATIONS = "verify_citations"
    DRAFT_RESPONSE = "draft_response"
    PROPOSE_PATCH = "propose_patch"
