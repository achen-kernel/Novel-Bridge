"""Re-index only Book 9 chunks with fixed params"""
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import asyncio, logging, sys
logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout)])

from app.pipeline.index_runner import IndexRunner
from app.clients.mysql_client import MysqlClient

db = MysqlClient()
runner = IndexRunner(db)
result = asyncio.run(runner.index_book(9, reindex=True))
print("Book 9 done:", result)
