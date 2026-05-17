"""
Schemas for book upload and build trigger.
"""

from pydantic import BaseModel, Field
from typing import Optional


class BookUploadRequest(BaseModel):
    """Upload a book as raw text."""
    title: str = Field(..., description="Book title")
    author: str = Field(default="", description="Book author")
    raw_text: str = Field(..., description="Full book text content")
    source_filename: str = Field(default="upload.txt", description="Original filename")
    file_type: str = Field(default="txt", description="File type")


class BookUploadResponse(BaseModel):
    """Response after book upload."""
    id: int
    title: str
    status: str
    char_count: int
    message: str


class BuildTriggerRequest(BaseModel):
    """Trigger the full build pipeline for a book_source_id."""
    book_source_id: int = Field(..., description="ID in novel_book_source")
    force_rebuild: bool = Field(default=False, description="Rebuild even if artifacts exist")


class BuildTriggerResponse(BaseModel):
    """Response after triggering build."""
    agent_run_id: int
    book_source_id: int
    status: str
    message: str


class BookSourceInfo(BaseModel):
    """Book source record info."""
    id: int
    title: str
    author: str
    source_filename: str
    file_type: str
    file_size: int
    content_hash: str
    status: str
    raw_text_length: int
    created_at: str
