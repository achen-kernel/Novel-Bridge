"""
Book build runner — orchestrates the full Demo 5B pipeline.

Flow:
1. Read book_source from MySQL
2. Create AgentRun record
3. Analyze structure → create chapters (AgentStep 1)
4. Build chunks (AgentStep 2)
5. Run entity extraction on each chunk (AgentStep 3)
6. Update AgentRun status
"""

import datetime
import traceback
from typing import Optional

from app.clients.mysql_client import MySQLClient
from app.clients.llama_cpp_client import LlamaCppClient
from app.clients.neo4j_client import Neo4jClient
from app.stores.book_source_store import BookSourceStore
from app.stores.chapter_store import ChapterStore
from app.stores.chunk_store import ChunkStore
from app.stores.model_run_store import ModelRunStore
from app.stores.candidate_store import CandidateStore
from app.stores.graph_store import EntityProfileStore, ReviewRecordStore
from app.runners.chapter_split_runner import split_chapters, detect_structure_type
from app.runners.chunk_build_runner import build_chunks
from app.runners.entity_extraction_runner import extract_entities_from_chunk

SPLITTER_VERSION = "chapter_split_v0.1"
CHUNK_VERSION = "chunk_v0.1"


class BookBuildRunner:
    """Orchestrate the full build pipeline for a book_source_id."""

    def __init__(self, db: MySQLClient = None, llm: LlamaCppClient = None, neo4j: Neo4jClient = None):
        self.db = db or MySQLClient()
        self.llm = llm or LlamaCppClient()
        self.neo4j = neo4j or Neo4jClient()
        self.book_source_store = BookSourceStore(self.db)
        self.chapter_store = ChapterStore(self.db)
        self.chunk_store = ChunkStore(self.db)
        self.model_run_store = ModelRunStore(self.db)
        self.candidate_store = CandidateStore(self.db)
        self.entity_profile_store = EntityProfileStore(self.db)
        self.review_store = ReviewRecordStore(self.db)

    def build(self, book_source_id: int, extract_chunks: bool = True,
              limit_chunks: Optional[int] = None) -> dict:
        """
        Run the full build pipeline.

        Returns a summary dict with status and counts.
        """
        summary = {
            "book_source_id": book_source_id,
            "status": "FAILED",
            "agent_run_id": None,
            "chapters_created": 0,
            "chunks_created": 0,
            "chunks_extracted": 0,
            "candidates_created": 0,
            "errors": [],
        }

        # 1. Read book source
        book_source = self.book_source_store.get_by_id(book_source_id)
        if not book_source:
            summary["errors"].append(f"book_source #{book_source_id} not found")
            return summary

        book_id = book_source["id"]  # For now, use book_source.id as book_id
        raw_text = book_source["raw_text"]
        title = book_source["title"]
        author = book_source.get("author", "")

        # 2. Create AgentRun
        agent_run_id = self._create_agent_run(book_source_id, book_id, title)
        summary["agent_run_id"] = agent_run_id

        try:
            # 3. Book overview step (LLM-assisted structure analysis)
            overview_step_id = self._create_step(agent_run_id, "BOOK_OVERVIEW", 1)
            from app.runners.book_overview_runner import generate_book_overview
            overview = generate_book_overview(
                book_source=book_source,
                llm=self.llm,
                db=self.db,
            )
            structure_type = overview.get("structure_type", "NONE")
            summary["structure_type"] = structure_type
            self._complete_step(overview_step_id, 1)

            # 4. Chapter split step (use LLM-detected structure type)
            chapter_step_id = self._create_step(agent_run_id, "SPLIT_CHAPTERS", 2)
            chapters = self._run_chapter_split(raw_text, book_source_id, book_id,
                                               title, structure_type=structure_type)
            summary["chapters_created"] = len(chapters)
            self._complete_step(chapter_step_id, len(chapters))

            if not chapters:
                summary["errors"].append("No chapters created")
                self._fail_agent_run(agent_run_id, "No chapters created")
                return summary

            # 5. Chunk build step
            chunk_step_id = self._create_step(agent_run_id, "BUILD_CHUNKS", 3)
            all_chunks = []
            for ch in chapters:
                c = ch  # ChapterSplitResult
                # We need to get the chapter_id from MySQL
                chapter_records = self.chapter_store.get_by_book_source(book_source_id)
                chapter_record = next((cr for cr in chapter_records
                                       if cr["chapter_number"] == ch.chapter_number), None)
                if not chapter_record:
                    continue
                chapter_chunks = self._run_chunk_build(c, chapter_record, book_source_id, book_id)
                all_chunks.extend(chapter_chunks)

            summary["chunks_created"] = len(all_chunks)
            self._complete_step(chunk_step_id, len(all_chunks))

            if extract_chunks and all_chunks:
                # 6. Entity extraction step
                extract_step_id = self._create_step(agent_run_id, "EXTRACT_ENTITIES", 4)

                chunks_to_process = all_chunks
                if limit_chunks:
                    chunks_to_process = all_chunks[:limit_chunks]

                for chk in chunks_to_process:
                    # Fetch the full chunk record from DB
                    chunk_record = self.chunk_store.get_by_id(chk) if isinstance(chk, int) else chk
                    if not chunk_record:
                        continue

                    extraction_result = extract_entities_from_chunk(
                        chunk=chunk_record,
                        book_source=book_source,
                        llm=self.llm,
                        model_run_store=self.model_run_store,
                        candidate_store=self.candidate_store,
                    )
                    if extraction_result["status"] == "SUCCESS":
                        summary["chunks_extracted"] += 1
                        summary["candidates_created"] += extraction_result.get("candidate_count", 0)
                    else:
                        summary["errors"].extend(extraction_result.get("errors", []))

                self._complete_step(extract_step_id, summary["chunks_extracted"])

            # Mark book source as built
            self.book_source_store.update_status(book_source_id, "BUILT")

            # Update AgentRun as success
            self._complete_agent_run(agent_run_id, summary)

            summary["status"] = "SUCCESS"

        except Exception as e:
            error_msg = f"Build failed: {traceback.format_exc()}"
            summary["errors"].append(error_msg)
            self._fail_agent_run(agent_run_id, error_msg)
            self.book_source_store.update_status(book_source_id, "BUILD_FAILED", error_msg)

        return summary

    # ---- Internal helpers ----

    def _create_agent_run(self, book_source_id: int, book_id: int, title: str) -> int:
        sql = """INSERT INTO novel_agent_run (run_type, book_id, status, started_at)
                 VALUES ('BOOK_BUILD', %s, 'RUNNING', %s)"""
        now = datetime.datetime.now()
        return self.db.insert(sql, (book_id, now))

    def _create_step(self, agent_run_id: int, step_type: str, order: int) -> int:
        sql = """INSERT INTO novel_agent_step (agent_run_id, step_type, step_order, status, started_at)
                 VALUES (%s, %s, %s, 'RUNNING', %s)"""
        now = datetime.datetime.now()
        return self.db.insert(sql, (agent_run_id, step_type, order, now))

    def _complete_step(self, step_id: int, result_count: int = 0):
        now = datetime.datetime.now()
        self.db.update(
            "UPDATE novel_agent_step SET status = 'SUCCESS', completed_at = %s, error_message = %s WHERE id = %s",
            (now, f"Processed {result_count} items", step_id),
        )

    def _fail_step(self, step_id: int, error: str):
        now = datetime.datetime.now()
        self.db.update(
            "UPDATE novel_agent_step SET status = 'FAILED', completed_at = %s, error_message = %s WHERE id = %s",
            (now, error[:500], step_id),
        )

    def _complete_agent_run(self, run_id: int, summary: dict):
        now = datetime.datetime.now()
        msg = f"Chapters: {summary['chapters_created']}, Chunks: {summary['chunks_created']}, "
        msg += f"Extracted: {summary['chunks_extracted']}, Candidates: {summary['candidates_created']}"
        self.db.update(
            "UPDATE novel_agent_run SET status = 'SUCCESS', completed_at = %s, error_message = %s WHERE id = %s",
            (now, msg, run_id),
        )

    def _fail_agent_run(self, run_id: int, error: str):
        now = datetime.datetime.now()
        self.db.update(
            "UPDATE novel_agent_run SET status = 'FAILED', completed_at = %s, error_message = %s WHERE id = %s",
            (now, error[:500], run_id),
        )

    def _run_chapter_split(self, raw_text: str, book_source_id: int,
                           book_id: int, title: str,
                           structure_type: str = None) -> list:
        """Run chapter split and persist to DB. Returns list of ChapterSplitResult.
        If structure_type is provided (from LLM overview), use it.
        Otherwise fall back to rule-based detection.
        """
        if not structure_type:
            structure_type = detect_structure_type(raw_text)
        chapters = split_chapters(raw_text, structure_type=structure_type)

        persisted = []
        for ch in chapters:
            chap_id = self.chapter_store.insert(
                book_source_id=book_source_id,
                book_id=book_id,
                chapter_number=ch.chapter_number,
                title=ch.title,
                structure_type=ch.structure_type,
                start_offset=ch.start_offset,
                end_offset=ch.end_offset,
                raw_content=ch.raw_content,
                char_count=len(ch.raw_content),
                splitter_version=SPLITTER_VERSION,
            )
            ch.db_id = chap_id
            persisted.append(ch)

        return persisted

    def _run_chunk_build(self, chapter_result, chapter_record: dict,
                         book_source_id: int, book_id: int) -> list:
        """Build chunks for a chapter and persist. Returns list of chunk record dicts."""
        chapter_text = chapter_result.raw_content
        chapter_start_offset = chapter_result.start_offset
        chapter_id = chapter_record["id"]

        chunks = build_chunks(chapter_text, chapter_start_offset)
        persisted_ids = []

        for ch in chunks:
            chunk_id = self.chunk_store.insert(
                book_source_id=book_source_id,
                book_id=book_id,
                chapter_id=chapter_id,
                chunk_index=ch.chunk_index,
                text=ch.text,
                start_offset=ch.start_offset,
                end_offset=ch.end_offset,
                char_count=ch.char_count,
                token_count=0,  # Will compute later if needed
                chunk_strategy=f"chars_{CHUNK_VERSION}",
                chunk_version=CHUNK_VERSION,
            )
            persisted_ids.append(chunk_id)

        return persisted_ids
