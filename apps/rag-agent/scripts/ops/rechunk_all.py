"""
Re-chunk all 5 books with new force-split chunker (800-1500 chars per chunk).
Step 1: Delete old chunks
Step 2: Create new chunks from existing chapters
"""
import logging, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.mysql_client import MysqlClient
from app.pipeline.chunker import chunk_chapter
from app.stores.chunk_store import ChunkStore
from app.stores.chapter_store import ChapterStore

BOOKS = [6, 7, 8, 9, 10]

db = MysqlClient()
conn = db.connect()

try:
    chapter_store = ChapterStore(conn)
    chunk_store = ChunkStore(conn)

    for book_id in BOOKS:
        log.info(f"\n{'='*50}")
        log.info(f"Processing Book {book_id}")

        # Step 1: Delete old chunks
        with conn.cursor() as c:
            c.execute("DELETE FROM novel_chunk WHERE book_id=%s", (book_id,))
            conn.commit()
            deleted = c.rowcount
        log.info(f"  Deleted {deleted} old chunks")

        # Step 2: Read chapters
        chapters = chapter_store.get_chapters_by_book(book_id)
        log.info(f"  {len(chapters)} chapters to process")

        # Step 3: Create new chunks
        total_chunks = 0
        for ch in chapters:
            ch_id = ch["id"]
            content = ch.get("raw_content", "") or ""
            start_offset = ch.get("start_offset", 0) or 0

            chunks = chunk_chapter(
                chapter_id=ch_id,
                book_id=book_id,
                chapter_text=content,
                chapter_start_offset=start_offset,
            )

            for ck in chunks:
                chunk_store.insert_chunk(
                    book_id=book_id,
                    chapter_id=ch_id,
                    chunk_index=ck["chunk_index"],
                    content=ck["content"],
                    start_offset=ck["start_offset"],
                    end_offset=ck["end_offset"],
                )
            total_chunks += len(chunks)

        # Step 4: Update book chunk_count
        with conn.cursor() as c:
            c.execute("UPDATE novel_book SET chunk_count=%s WHERE id=%s", (total_chunks, book_id))
            conn.commit()

        log.info(f"  Created {total_chunks} new chunks")
        log.info(f"  Book chunk_count updated to {total_chunks}")

finally:
    conn.close()

log.info(f"\n{'='*50}")
log.info("ALL BOOKS RE-CHUNKED")
log.info(f"{'='*50}")

