"""Re-index all 5 books to Qdrant with new chunks"""
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import asyncio, logging, sys
logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

from app.pipeline.index_runner import IndexRunner
from app.clients.mysql_client import MysqlClient

db = MysqlClient()
runner = IndexRunner(db)

for bid in [6, 7, 8, 9, 10]:
    print(f"\n--- Book {bid} ---")
    r = asyncio.run(runner.index_book(bid, reindex=True))
    print(f"  chunks={r['chunks_indexed']}, facts={r['facts_indexed']}")

print("\nALL DONE")
