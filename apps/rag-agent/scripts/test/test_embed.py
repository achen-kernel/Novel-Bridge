"""Quick embedding model test"""
from sentence_transformers import SentenceTransformer
import time

t0 = time.time()
model = SentenceTransformer(
    "/home/wk/novelbridge/models/Qwen3-Embedding-0.6B/Qwen/Qwen3-Embedding-0___6B",
    device="cuda:1"
)
emb = model.encode(["test sentence"], show_progress_bar=False)
print(f"OK: {len(emb[0])} dims in {time.time()-t0:.2f}s")
