"""
NovelBridge — Neo4j client.

Writes approved graph data: Book, Chapter, Chunk, Entity nodes + relationships.
"""

import os
from typing import Optional

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")


class Neo4jClient:
    """Neo4j driver wrapper for graph writes."""

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def health(self) -> bool:
        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    # ---- Node writes ----

    def upsert_book(self, book_id: int, book_source_id: int, title: str):
        with self._driver.session() as session:
            session.run(
                """
                MERGE (b:Book {book_id: $book_id})
                SET b.book_source_id = $book_source_id,
                    b.title = $title,
                    b.updated_at = timestamp()
                """,
                book_id=book_id, book_source_id=book_source_id, title=title,
            )

    def upsert_chapter(self, chapter_id: int, book_id: int, chapter_number: int, title: str):
        with self._driver.session() as session:
            session.run(
                """
                MERGE (c:Chapter {chapter_id: $chapter_id})
                SET c.book_id = $book_id,
                    c.chapter_number = $chapter_number,
                    c.title = $title,
                    c.updated_at = timestamp()
                """,
                chapter_id=chapter_id, book_id=book_id,
                chapter_number=chapter_number, title=title or "",
            )

    def upsert_chunk(self, chunk_id: int, chapter_id: int, book_id: int, chunk_index: int):
        with self._driver.session() as session:
            session.run(
                """
                MERGE (c:Chunk {chunk_id: $chunk_id})
                SET c.chapter_id = $chapter_id,
                    c.book_id = $book_id,
                    c.chunk_index = $chunk_index,
                    c.updated_at = timestamp()
                """,
                chunk_id=chunk_id, chapter_id=chapter_id,
                book_id=book_id, chunk_index=chunk_index,
            )

    def upsert_entity(self, entity_profile_id: int, book_id: int, name: str, entity_type: str):
        with self._driver.session() as session:
            session.run(
                """
                MERGE (e:Entity {entity_profile_id: $entity_profile_id})
                SET e.book_id = $book_id,
                    e.name = $name,
                    e.type = $entity_type,
                    e.updated_at = timestamp()
                """,
                entity_profile_id=entity_profile_id, book_id=book_id,
                name=name, entity_type=entity_type,
            )

    # ---- Relationship writes ----

    def relate_book_chapter(self, book_id: int, chapter_id: int):
        with self._driver.session() as session:
            session.run(
                """
                MATCH (b:Book {book_id: $book_id})
                MATCH (c:Chapter {chapter_id: $chapter_id})
                MERGE (b)-[:HAS_CHAPTER]->(c)
                """,
                book_id=book_id, chapter_id=chapter_id,
            )

    def relate_chapter_chunk(self, chapter_id: int, chunk_id: int):
        with self._driver.session() as session:
            session.run(
                """
                MATCH (c:Chapter {chapter_id: $chapter_id})
                MATCH (ch:Chunk {chunk_id: $chunk_id})
                MERGE (c)-[:HAS_CHUNK]->(ch)
                """,
                chapter_id=chapter_id, chunk_id=chunk_id,
            )

    def relate_entity_chunk(
        self,
        entity_profile_id: int,
        chunk_id: int,
        candidate_id: int,
        model_run_id: int,
        evidence_text: str,
        confidence: float,
        status: str = "APPROVED",
    ):
        with self._driver.session() as session:
            session.run(
                """
                MATCH (e:Entity {entity_profile_id: $entity_profile_id})
                MATCH (ch:Chunk {chunk_id: $chunk_id})
                MERGE (e)-[r:APPEARS_IN {
                    candidate_id: $candidate_id,
                    model_run_id: $model_run_id
                }]->(ch)
                SET r.evidence_text = $evidence_text,
                    r.confidence = $confidence,
                    r.status = $status,
                    r.reviewed_at = timestamp()
                """,
                entity_profile_id=entity_profile_id,
                chunk_id=chunk_id,
                candidate_id=candidate_id,
                model_run_id=model_run_id,
                evidence_text=evidence_text,
                confidence=confidence,
                status=status,
            )

    def close(self):
        self._driver.close()

    def __del__(self):
        self.close()
