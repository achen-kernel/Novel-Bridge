"""
Re-run narrative builder (P5) for all books to fix event fact aggregation.
Clears old mention/fact data first, then rebuilds with fixed EventFactStore.
"""
import logging, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients.mysql_client import MysqlClient
from app.pipeline.narrative_builder import NarrativeBuilder

BOOKS = [6, 7, 8, 9, 10]

db = MysqlClient()
conn = db.connect()

try:
    for book_id in BOOKS:
        log.info(f"\n{'='*50}")
        log.info(f"Processing Book {book_id}")

        # Step 1: Clear old data
        with conn.cursor() as c:
            for table in ["novel_event_fact", "novel_event_mention",
                           "novel_relation_fact", "novel_relation_mention"]:
                c.execute(f"DELETE FROM {table} WHERE book_id=%s", (book_id,))
                deleted = c.rowcount
                log.info(f"  Cleared {deleted} from {table}")
            conn.commit()

        # Step 2: Run narrative builder
        builder = NarrativeBuilder(db)
        result = builder.build_from_book(book_id)
        log.info(f"  Result: {result}")

finally:
    conn.close()

log.info(f"\n{'='*50}")
log.info("ALL BOOKS NARRATIVE REBUILT")
log.info(f"{'='*50}")

