"""
Clean Book 7 (鑱婃枊蹇楀紓) - remove all processed data, keep original chapters and book record.
Cleans: MySQL facts/chunks/entities/relations/events/agent_runs + Qdrant vectors
"""
import sys, os, logging, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger()

BOOK_ID = 7
LOG_PREFIX = "[Clean B7]"

def clean_mysql():
    """Delete all processed data for book_id=7 from MySQL, keep novel_book + novel_chapter"""
    from app.clients.mysql_client import MysqlClient
    conn = MysqlClient().connect()
    deleted = {}
    try:
        with conn.cursor() as c:
            # Order matters: delete child tables first, then parent-referencing tables
            tables_in_order = [
                # Citations & training samples (depend on facts/chunks)
                ("novel_citation", "DELETE FROM novel_citation WHERE book_id=%s"),
                ("novel_training_sample", "DELETE FROM novel_training_sample WHERE book_id=%s"),
                # Agent runtime traces
                ("novel_model_call", "DELETE FROM novel_model_call WHERE book_id=%s"),
                ("novel_agent_step", "DELETE FROM novel_agent_step WHERE agent_run_id IN (SELECT id FROM novel_agent_run WHERE book_id=%s)"),
                ("novel_agent_run", "DELETE FROM novel_agent_run WHERE book_id=%s"),
                # Narrative graph
                ("novel_plot_stage", "DELETE FROM novel_plot_stage WHERE book_id=%s"),
                ("novel_event_fact", "DELETE FROM novel_event_fact WHERE book_id=%s"),
                ("novel_event_mention", "DELETE FROM novel_event_mention WHERE book_id=%s"),
                ("novel_relation_fact", "DELETE FROM novel_relation_fact WHERE book_id=%s"),
                ("novel_relation_mention", "DELETE FROM novel_relation_mention WHERE book_id=%s"),
                # Entity governance
                ("novel_alias_decision", "DELETE FROM novel_alias_decision WHERE book_id=%s"),
                ("novel_entity_profile", "DELETE FROM novel_entity_profile WHERE book_id=%s"),
                ("novel_entity_mention", "DELETE FROM novel_entity_mention WHERE book_id=%s"),
                # Core facts and chunks
                ("novel_chapter_fact", "DELETE FROM novel_chapter_fact WHERE book_id=%s"),
                ("novel_chunk", "DELETE FROM novel_chunk WHERE book_id=%s"),
            ]
            for table, sql in tables_in_order:
                c.execute(sql, (BOOK_ID,))
                conn.commit()
                deleted[table] = c.rowcount
                log.info(f"  {LOG_PREFIX} MySQL {table}: deleted {c.rowcount} rows")

            # Reset book status to IMPORTED
            c.execute("UPDATE novel_book SET status='IMPORTED', chapter_count=25, chunk_count=0 WHERE id=%s", (BOOK_ID,))
            conn.commit()
            log.info(f"  {LOG_PREFIX} Reset book {BOOK_ID} status to IMPORTED")

            # Verify (handle both tuple and dict cursor)
            c.execute("SELECT COUNT(*) as cnt FROM novel_chapter WHERE book_id=%s", (BOOK_ID,))
            row = c.fetchone()
            chapters = row['cnt'] if isinstance(row, dict) else (row[0] if row else 0)
            log.info(f"  {LOG_PREFIX} Chapters kept: {chapters}")

            c.execute("SELECT COUNT(*) as cnt FROM novel_book WHERE id=%s", (BOOK_ID,))
            row2 = c.fetchone()
            books = row2['cnt'] if isinstance(row2, dict) else (row2[0] if row2 else 0)
            log.info(f"  {LOG_PREFIX} Book record kept: {books}")

    finally:
        conn.close()
    return deleted


def clean_qdrant():
    """Delete Qdrant vectors for book_id=7"""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList
    qdrant = QdrantClient(host='127.0.0.1', port=16333)
    collections = ['novel_chapter_facts', 'novel_chunks']
    deleted = {}
    for col in collections:
        try:
            info = qdrant.get_collection(col)
            total = info.points_count
            # Count book_id=7
            count_result = qdrant.count(
                collection_name=col,
                count_filter=Filter(must=[FieldCondition(key='book_id', match=MatchValue(value=BOOK_ID))])
            )
            book_cnt = count_result.count
            if book_cnt > 0:
                qdrant.delete(
                    collection_name=col,
                    points_selector=Filter(must=[FieldCondition(key='book_id', match=MatchValue(value=BOOK_ID))])
                )
                log.info(f"  {LOG_PREFIX} Qdrant {col}: deleted {book_cnt} vectors (was {total} total)")
                deleted[col] = book_cnt
            else:
                log.info(f"  {LOG_PREFIX} Qdrant {col}: 0 vectors for book {BOOK_ID} (total {total})")
                deleted[col] = 0
        except Exception as e:
            log.warning(f"  {LOG_PREFIX} Qdrant {col}: error - {e}")
            deleted[col] = -1
    return deleted


if __name__ == "__main__":
    start = datetime.datetime.now()
    log.info(f"{'='*60}")
    log.info(f"{LOG_PREFIX} START Book {BOOK_ID} cleanup at {start}")
    log.info(f"{'='*60}")

    log.info(f"\n{LOG_PREFIX} --- Phase 1: MySQL cleanup ---")
    mysql_result = clean_mysql()

    log.info(f"\n{LOG_PREFIX} --- Phase 2: Qdrant cleanup ---")
    qdrant_result = clean_qdrant()

    elapsed = (datetime.datetime.now() - start).total_seconds()
    log.info(f"\n{'='*60}")
    log.info(f"{LOG_PREFIX} CLEANUP COMPLETE in {elapsed:.1f}s")
    log.info(f"{LOG_PREFIX} MySQL deleted: {sum(mysql_result.values())} rows across {len(mysql_result)} tables")
    log.info(f"{LOG_PREFIX} Qdrant deleted: {sum(v for v in qdrant_result.values() if v > 0)} vectors")
    log.info(f"{LOG_PREFIX} Book {BOOK_ID} is now clean and ready for re-pipeline")
    log.info(f"{'='*60}")

