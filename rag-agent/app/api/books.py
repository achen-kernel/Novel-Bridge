"""
Book management API endpoints.
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.clients.mysql_client import MySQLClient
from app.clients.llama_cpp_client import LlamaCppClient
from app.clients.neo4j_client import Neo4jClient
from app.stores.book_source_store import BookSourceStore
from app.stores.chapter_store import ChapterStore
from app.stores.chunk_store import ChunkStore
from app.schemas.book_build import (
    BookUploadRequest, BookUploadResponse,
    BuildTriggerRequest, BuildTriggerResponse,
)

router = APIRouter(prefix="/api/books", tags=["books"])


def _get_stores():
    db = MySQLClient()
    return db, BookSourceStore(db)


@router.post("/upload", response_model=BookUploadResponse)
async def upload_book(req: BookUploadRequest):
    """Upload a book as raw text (for testing without Java backend)."""
    db = MySQLClient()
    try:
        store = BookSourceStore(db)
        book_source_id = store.insert(
            title=req.title,
            author=req.author,
            raw_text=req.raw_text,
            source_filename=req.source_filename,
            file_type=req.file_type,
        )
        char_count = len(req.raw_text)
        return BookUploadResponse(
            id=book_source_id,
            title=req.title,
            status="UPLOADED",
            char_count=char_count,
            message=f"Book '{req.title}' uploaded as book_source #{book_source_id}",
        )
    finally:
        db.close()


@router.post("/trigger-build", response_model=BuildTriggerResponse)
async def trigger_build(req: BuildTriggerRequest):
    """
    Trigger the full build pipeline for a book_source_id.

    This starts a background book build. For simplicity in Demo 5B,
    the runner runs inline. For production, use a task queue.
    """
    from app.runners.book_build_runner import BookBuildRunner

    db = MySQLClient()
    llm = LlamaCppClient()
    neo4j = Neo4jClient()

    try:
        # Check book source exists
        book_source_store = BookSourceStore(db)
        book_source = book_source_store.get_by_id(req.book_source_id)
        if not book_source:
            raise HTTPException(status_code=404, detail=f"Book source #{req.book_source_id} not found")

        runner = BookBuildRunner(db=db, llm=llm, neo4j=neo4j)
        result = runner.build(
            book_source_id=req.book_source_id,
            extract_chunks=True,
        )

        return BuildTriggerResponse(
            agent_run_id=result.get("agent_run_id", 0),
            book_source_id=req.book_source_id,
            status=result["status"],
            message=f"Build {result['status']}: "
                    f"{result.get('chapters_created', 0)} chapters, "
                    f"{result.get('chunks_created', 0)} chunks, "
                    f"{result.get('candidates_created', 0)} candidates",
        )
    finally:
        db.close()
        llm.close()
        neo4j.close()


@router.get("/sources")
async def list_book_sources():
    """List all uploaded book sources."""
    from app.clients.mysql_client import MySQLClient
    from app.stores.book_source_store import BookSourceStore

    db = MySQLClient()
    try:
        store = BookSourceStore(db)
        sources = store.list_all()
        return {"sources": sources, "count": len(sources)}
    finally:
        db.close()


@router.get("/sources/{book_source_id}")
async def get_book_source(book_source_id: int):
    """Get a book source by ID (without raw_text by default)."""
    from app.clients.mysql_client import MySQLClient
    from app.stores.book_source_store import BookSourceStore

    db = MySQLClient()
    try:
        store = BookSourceStore(db)
        source = store.get_by_id(book_source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Book source #{book_source_id} not found")
        # Don't return full raw_text by default
        if "raw_text" in source:
            source["raw_text_length"] = len(source["raw_text"])
            del source["raw_text"]
        return source
    finally:
        db.close()


@router.get("/sources/{book_source_id}/chapters")
async def get_book_chapters(book_source_id: int):
    """Get chapters for a book source."""
    db = MySQLClient()
    try:
        store = ChapterStore(db)
        chapters = store.get_by_book_source(book_source_id)
        return {"chapters": chapters, "count": len(chapters)}
    finally:
        db.close()


@router.get("/sources/{book_source_id}/chunks")
async def get_book_chunks(book_source_id: int):
    """Get chunks for a book source."""
    db = MySQLClient()
    try:
        store = ChunkStore(db)
        chunks = store.get_by_book_source(book_source_id)
        return {"chunks": chunks, "count": len(chunks)}
    finally:
        db.close()
