"""
Schemas for entity extraction, candidates, and review.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class EntityItem(BaseModel):
    """Single entity from model output."""
    name: str
    type: str = Field(default="UNKNOWN", pattern=r"^(CHARACTER|LOCATION|ITEM|ORG|TITLE|UNKNOWN)$")
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    evidence_text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertain: bool = False


class EntityExtractionOutput(BaseModel):
    """Expected JSON structure from the model."""
    chapter_id: int = 0
    chunk_id: int = 0
    entities: List[EntityItem] = Field(default_factory=list)
    uncertain_items: List[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    """Trigger entity extraction for a chunk or book."""
    book_source_id: int
    chunk_ids: Optional[List[int]] = None
    limit_chunks: Optional[int] = Field(default=None, ge=1, le=100)


class ExtractResponse(BaseModel):
    """Response after triggering extraction."""
    agent_run_id: Optional[int] = None
    chunks_queued: int
    status: str
    message: str


class CandidateInfo(BaseModel):
    """Entity candidate as stored in the database."""
    id: int
    book_source_id: Optional[int]
    book_id: Optional[int]
    chapter_id: Optional[int]
    chunk_id: Optional[int]
    name: str
    entity_type: str
    evidence_text: str
    confidence: float
    uncertain: bool
    status: str
    created_at: str


class ReviewAction(BaseModel):
    """Review action on a candidate."""
    action: str = Field(..., pattern=r"^(approve|reject|edit)$")
    reviewer: str = Field(default="remote-agent")
    comment: str = ""
    # For edit action:
    new_name: Optional[str] = None
    new_type: Optional[str] = None
    new_confidence: Optional[float] = None


class ReviewResponse(BaseModel):
    """Response after review action."""
    candidate_id: int
    action: str
    status: str
    message: str
    entity_profile_id: Optional[int] = None
