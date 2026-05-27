"""
Standalone script to index Books 6, 7, 9, 10 into Qdrant on the remote server.
Run on remote: conda activate llamacpp && python _index_remote.py
Or SCP this file and run it.
"""
import asyncio, time, logging, sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger()

from app.pipeline.index_runner import IndexRunner
from app.clients.mysql_client import MysqlClient

BOOKS = [6, 7, 9, 10]

async def main():
    log.info("=" * 60)
    log.info("REMOTE INDEX START for Books 6, 7, 9, 10")
    log.info("=" * 60)
    
    db = MysqlClient()
    runner = IndexRunner(db)

    for book_id in BOOKS:
        log.info(f"\n--- Indexing Book {book_id} ---")
        t0 = time.time()
        try:
            result = await runner.index_book(book_id, reindex=True)
            elapsed = time.time() - t0
            log.info(f"  Book {book_id} DONE in {elapsed:.1f}s: "
                     f"chunks={result.get('chunks_indexed', 0)}, "
                     f"facts={result.get('facts_indexed', 0)}")
        except Exception as e:
            elapsed = time.time() - t0
            log.error(f"  Book {book_id} FAILED after {elapsed:.1f}s: {e}")

    log.info(f"\n{'=' * 60}")
    log.info("ALL BOOKS INDEXING COMPLETE")
    log.info(f"{'=' * 60}")

if __name__ == "__main__":
    asyncio.run(main())
