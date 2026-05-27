"""
Create chunks for Book 7 from existing chapters (after cleanup deleted chunks).
"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger()

BOOK_ID = 7

def main():
    from app.clients.mysql_client import MysqlClient
    from app.stores.chapter_store import ChapterStore
    from app.stores.chunk_store import ChunkStore
    from app.pipeline.chunker import chunk_chapter

    db = MysqlClient()
    conn = db.connect()
    try:
        chapter_store = ChapterStore(conn)
        chunk_store = ChunkStore(conn)

        chapters = chapter_store.get_chapters_by_book(BOOK_ID)
        log.info(f"Book {BOOK_ID}: {len(chapters)} chapters to chunk")

        total_chunks = 0
        for ch in chapters:
            ch_id = ch['id']
            content = ch.get('raw_content', '') or ''
            start_offset = ch.get('start_offset', 0) or 0

            # Create chunks
            chunks = chunk_chapter(
                chapter_id=ch_id,
                book_id=BOOK_ID,
                chapter_text=content,
                chapter_start_offset=start_offset,
            )

            # Insert chunks
            for ck in chunks:
                chunk_store.insert_chunk(
                    book_id=BOOK_ID,
                    chapter_id=ch_id,
                    chunk_index=ck['chunk_index'],
                    content=ck['content'],
                    start_offset=ck['start_offset'],
                    end_offset=ck['end_offset'],
                )
            total_chunks += len(chunks)
            log.info(f"  Ch {ch['chapter_number']} (id={ch_id}): {len(chunks)} chunks ({len(content)} chars)")

        # Update book chunk count
        with conn.cursor() as c:
            c.execute("UPDATE novel_book SET chunk_count=%s, status='BUILT' WHERE id=%s", (total_chunks, BOOK_ID))
            conn.commit()

        log.info(f"\nDone: {total_chunks} total chunks created for Book {BOOK_ID}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()

