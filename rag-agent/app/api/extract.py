"""
Entity extraction API endpoints.

All model calls run in background thread to avoid blocking the event loop.
"""

import logging
import threading
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.clients.mysql_client import MySQLClient
from app.clients.llama_cpp_client import LlamaCppClient
from app.clients.neo4j_client import Neo4jClient
from app.stores.book_source_store import BookSourceStore
from app.stores.chunk_store import ChunkStore
from app.stores.model_run_store import ModelRunStore
from app.stores.candidate_store import CandidateStore
from app.schemas.entity_extract import ExtractRequest, ExtractResponse

logger = logging.getLogger("rag-agent.extract")
router = APIRouter(tags=["extract"])


@router.post("/extract/entities")
async def extract_entities(req: ExtractRequest):
    """
    Trigger entity extraction for chunks of a book source.
    Runs in background; returns immediately.
    """
    db = MySQLClient()
    try:
        book_source_store = BookSourceStore(db)
        book_source = book_source_store.get_by_id(req.book_source_id)
        if not book_source:
            raise HTTPException(status_code=404, detail=f"Book source #{req.book_source_id} not found")

        chunk_store = ChunkStore(db)
        if req.chunk_ids:
            chunks_to_process = []
            for cid in req.chunk_ids:
                chk = chunk_store.get_by_id(cid)
                if chk:
                    chunks_to_process.append(chk)
        else:
            limit = req.limit_chunks or 10
            chunks_to_process = chunk_store.get_unprocessed(req.book_source_id, limit)

        if not chunks_to_process:
            return {
                "chunks_queued": 0,
                "status": "NO_WORK",
                "message": "No unprocessed chunks found for entity extraction",
            }

        # Mark the chunks as queued
        chunk_ids = [c["id"] for c in chunks_to_process]
        logger.info(f"Queueing extraction for {len(chunk_ids)} chunks: {chunk_ids[:5]}...")

        # Start background extraction
        _run_extraction_in_background(
            book_source=book_source,
            chunks=chunks_to_process,
        )

        return {
            "chunks_queued": len(chunks_to_process),
            "status": "EXTRACTING",
            "message": f"Extraction started for {len(chunks_to_process)} chunks",
        }
    finally:
        db.close()


def _run_extraction_in_background(book_source: dict, chunks: list):
    """Run entity extraction for chunks in a background thread."""
    import time

    def _do_extract():
        logger.info(f"Background extraction starting for book_source #{book_source['id']}, {len(chunks)} chunks")
        db = MySQLClient()
        llm = LlamaCppClient()
        neo4j = Neo4jClient()
        try:
            model_run_store = ModelRunStore(db)
            candidate_store = CandidateStore(db)

            from app.runners.entity_extraction_runner import extract_entities_from_chunk

            for i, chunk in enumerate(chunks):
                logger.info(f"Extracting chunk {i+1}/{len(chunks)}: id={chunk['id']}")
                result = extract_entities_from_chunk(
                    chunk=chunk,
                    book_source=book_source,
                    llm=llm,
                    model_run_store=model_run_store,
                    candidate_store=candidate_store,
                )
                if result["status"] == "SUCCESS":
                    logger.info(f"  -> {result.get('candidate_count', 0)} candidates from chunk #{chunk['id']}")
                else:
                    logger.warning(f"  -> FAILED: {result.get('errors', [])[:2]}")
        except Exception as e:
            logger.exception(f"Background extraction error: {e}")
        finally:
            db.close()
            llm.close()
            neo4j.close()
            logger.info("Background extraction complete")

    thread = threading.Thread(target=_do_extract, daemon=True, name=f"extract-{book_source['id']}")
    thread.start()
    logger.info(f"Background extraction thread launched for book_source #{book_source['id']}")
