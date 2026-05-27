"""Re-index only Book 7 chunks with smart splitting"""
import os
# Enable PyTorch expandable segments to reduce GPU memory fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import asyncio, logging, sys
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
from app.pipeline.index_runner import IndexRunner
from app.clients.mysql_client import MysqlClient

db = MysqlClient()
runner = IndexRunner(db)
result = asyncio.run(runner.index_book(7, reindex=True))
print("Book 7 done:", result)
