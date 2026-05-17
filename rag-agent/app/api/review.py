"""
Review API endpoints for entity candidates.

Provides:
- List pending candidates
- Approve a candidate (→ entity_profile + Neo4j)
- Reject a candidate
- Edit and approve a candidate
"""

import datetime
from fastapi import APIRouter, HTTPException, Query

from app.clients.mysql_client import MySQLClient
from app.clients.neo4j_client import Neo4jClient
from app.stores.candidate_store import CandidateStore
from app.stores.graph_store import EntityProfileStore, ReviewRecordStore
from app.schemas.entity_extract import CandidateInfo, ReviewAction, ReviewResponse

router = APIRouter(tags=["review"])


def _candidate_to_info(c: dict) -> CandidateInfo:
    return CandidateInfo(
        id=c["id"],
        book_source_id=c.get("book_source_id"),
        book_id=c.get("book_id"),
        chapter_id=c.get("chapter_id"),
        chunk_id=c.get("chunk_id"),
        name=c["name"],
        entity_type=c.get("entity_type", "UNKNOWN"),
        evidence_text=c.get("evidence_text", ""),
        confidence=float(c.get("confidence", 0.0)),
        uncertain=bool(c.get("uncertain", False)),
        status=c["status"],
        created_at=c.get("created_at", ""),
    )


@router.get("/review/candidates")
async def list_candidates(
    book_source_id: int = Query(None, description="Filter by book source"),
    status: str = Query("PENDING_REVIEW", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
):
    """List entity candidates, optionally filtered by book_source_id and status."""
    db = MySQLClient()
    try:
        store = CandidateStore(db)
        if status == "PENDING_REVIEW":
            candidates = store.get_pending(book_source_id=book_source_id, limit=limit)
        else:
            if book_source_id:
                all_cands = store.get_by_book_source(book_source_id)
            else:
                # Fallback: get all pending
                all_cands = store.get_pending(limit=limit)
            candidates = [c for c in all_cands if c["status"] == status][:limit]

        return {
            "candidates": [_candidate_to_info(c) for c in candidates],
            "count": len(candidates),
            "pending_total": store.count_pending(book_source_id=book_source_id),
        }
    finally:
        db.close()


@router.post("/review/candidates/{candidate_id}/approve", response_model=ReviewResponse)
async def approve_candidate(candidate_id: int, action: ReviewAction = None):
    """
    Approve a candidate, write entity_profile, and optionally write to Neo4j.

    If action is not provided, uses default approval with the candidate's current values.
    """
    if action is None:
        action = ReviewAction(action="approve", reviewer="remote-agent")

    db = MySQLClient()
    neo4j = Neo4jClient()

    try:
        candidate_store = CandidateStore(db)
        candidate = candidate_store.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate #{candidate_id} not found")
        if candidate["status"] != "PENDING_REVIEW":
            raise HTTPException(
                status_code=400,
                detail=f"Candidate #{candidate_id} is already {candidate['status']}",
            )

        # Record the review
        review_store = ReviewRecordStore(db)
        review_store.insert(
            candidate_id=candidate_id,
            review_action="approve",
            reviewer=action.reviewer,
            comment=action.comment or "",
        )

        # Update candidate status
        candidate_store.update_status(candidate_id, "APPROVED")

        # Create entity_profile
        entity_profile_store = EntityProfileStore(db)
        profile_id = entity_profile_store.insert(
            book_id=candidate["book_id"],
            entity_name=candidate["name"],
            entity_type=candidate.get("entity_type", "UNKNOWN"),
            description=candidate.get("description", ""),
            aliases=candidate.get("aliases_json", "[]"),
            first_chapter_id=candidate.get("chapter_id"),
            last_chapter_id=candidate.get("chapter_id"),
        )

        # Write to Neo4j
        try:
            neo4j.upsert_book(
                book_id=candidate["book_id"],
                book_source_id=candidate.get("book_source_id", 0),
                title=f"Book #{candidate['book_id']}",
            )
            neo4j.upsert_entity(
                entity_profile_id=profile_id,
                book_id=candidate["book_id"],
                name=candidate["name"],
                entity_type=candidate.get("entity_type", "UNKNOWN"),
            )
            if candidate.get("chunk_id"):
                neo4j.upsert_chunk(
                    chunk_id=candidate["chunk_id"],
                    chapter_id=candidate.get("chapter_id", 0),
                    book_id=candidate["book_id"],
                    chunk_index=0,
                )
            if candidate.get("chunk_id") and profile_id:
                neo4j.relate_entity_chunk(
                    entity_profile_id=profile_id,
                    chunk_id=candidate["chunk_id"],
                    candidate_id=candidate["id"],
                    model_run_id=candidate.get("model_run_id", 0),
                    evidence_text=candidate.get("evidence_text", ""),
                    confidence=float(candidate.get("confidence", 0.0)),
                )
        except Exception as e:
            # Neo4j write is non-critical for Demo 5B
            print(f"[WARN] Neo4j write failed for candidate #{candidate_id}: {e}")

        return ReviewResponse(
            candidate_id=candidate_id,
            action="approve",
            status="APPROVED",
            message=f"Candidate '{candidate['name']}' approved, entity_profile #{profile_id} created",
            entity_profile_id=profile_id,
        )

    finally:
        db.close()
        neo4j.close()


@router.post("/review/candidates/{candidate_id}/reject", response_model=ReviewResponse)
async def reject_candidate(candidate_id: int, action: ReviewAction = None):
    """Reject a candidate without writing to entity_profile or Neo4j."""
    if action is None:
        action = ReviewAction(action="reject", reviewer="remote-agent")

    db = MySQLClient()
    try:
        candidate_store = CandidateStore(db)
        candidate = candidate_store.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate #{candidate_id} not found")

        review_store = ReviewRecordStore(db)
        review_store.insert(
            candidate_id=candidate_id,
            review_action="reject",
            reviewer=action.reviewer,
            comment=action.comment or "",
        )

        candidate_store.update_status(candidate_id, "REJECTED")

        return ReviewResponse(
            candidate_id=candidate_id,
            action="reject",
            status="REJECTED",
            message=f"Candidate '{candidate['name']}' rejected",
        )
    finally:
        db.close()


@router.post("/review/candidates/{candidate_id}/edit", response_model=ReviewResponse)
async def edit_candidate(candidate_id: int, action: ReviewAction):
    """
    Edit a candidate's fields, then approve it.

    Requires action.new_name, action.new_type, or action.new_confidence.
    """
    if not action.new_name and not action.new_type and action.new_confidence is None:
        raise HTTPException(status_code=400, detail="No edits provided (new_name, new_type, new_confidence)")

    db = MySQLClient()
    neo4j = Neo4jClient()

    try:
        candidate_store = CandidateStore(db)
        candidate = candidate_store.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate #{candidate_id} not found")

        # Build old/new values
        old_values = {}
        new_values = {}
        if action.new_name:
            old_values["name"] = candidate["name"]
            new_values["name"] = action.new_name
        if action.new_type:
            old_values["entity_type"] = candidate["entity_type"]
            new_values["entity_type"] = action.new_type
        if action.new_confidence is not None:
            old_values["confidence"] = candidate["confidence"]
            new_values["confidence"] = action.new_confidence

        # Record review
        review_store = ReviewRecordStore(db)
        review_store.insert(
            candidate_id=candidate_id,
            review_action="edit",
            old_values=old_values,
            new_values=new_values,
            reviewer=action.reviewer,
            comment=action.comment or "",
        )

        # Update candidate
        updates = {"status": "APPROVED"}
        if action.new_name:
            updates["name"] = action.new_name
        if action.new_type:
            updates["entity_type"] = action.new_type
        if action.new_confidence is not None:
            updates["confidence"] = action.new_confidence
        candidate_store.update_fields(candidate_id, **updates)

        # Create entity_profile with edited values
        final_name = action.new_name or candidate["name"]
        final_type = action.new_type or candidate.get("entity_type", "UNKNOWN")
        entity_profile_store = EntityProfileStore(db)
        profile_id = entity_profile_store.insert(
            book_id=candidate["book_id"],
            entity_name=final_name,
            entity_type=final_type,
            description=candidate.get("description", ""),
            aliases=candidate.get("aliases_json", "[]"),
            first_chapter_id=candidate.get("chapter_id"),
            last_chapter_id=candidate.get("chapter_id"),
        )

        # Neo4j write
        try:
            neo4j.upsert_book(
                book_id=candidate["book_id"],
                book_source_id=candidate.get("book_source_id", 0),
                title=f"Book #{candidate['book_id']}",
            )
            neo4j.upsert_entity(
                entity_profile_id=profile_id,
                book_id=candidate["book_id"],
                name=final_name,
                entity_type=final_type,
            )
            if candidate.get("chunk_id") and profile_id:
                neo4j.relate_entity_chunk(
                    entity_profile_id=profile_id,
                    chunk_id=candidate["chunk_id"],
                    candidate_id=candidate["id"],
                    model_run_id=candidate.get("model_run_id", 0),
                    evidence_text=candidate.get("evidence_text", ""),
                    confidence=float(action.new_confidence or candidate.get("confidence", 0.0)),
                )
        except Exception as e:
            print(f"[WARN] Neo4j write failed for candidate #{candidate_id}: {e}")

        return ReviewResponse(
            candidate_id=candidate_id,
            action="edit",
            status="APPROVED",
            message=f"Candidate '{candidate['name']}' edited and approved as '{final_name}'",
            entity_profile_id=profile_id,
        )

    finally:
        db.close()
        neo4j.close()
