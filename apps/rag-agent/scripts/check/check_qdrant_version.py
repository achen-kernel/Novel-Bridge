import qdrant_client
from importlib.metadata import version
print(f"Version: {version('qdrant-client')}")
c = qdrant_client.QdrantClient(url="http://127.0.0.1:16333", timeout=30)

# Search methods
for m in ['search', 'query', 'query_points', 'scroll', 'retrieve']:
    exists = hasattr(c, m)
    print(f"  has '{m}': {exists}")

# Try query_points
try:
    result = c.query_points(
        collection_name="novel_chunks",
        query=[0.0]*1024,
        limit=1
    )
    print("query_points works!")
except Exception as e:
    print(f"query_points failed: {e}")

# Try search
try:
    result = c.search(
        collection_name="novel_chunks",
        query_vector=[0.0]*1024,
        limit=1
    )
    print("search works!")
except Exception as e:
    print(f"search failed: {e}")

# List collection names
try:
    cols = c.get_collections().collections
    print(f"Collections: {[col.name for col in cols]}")
except Exception as e:
    print(f"get_collections failed: {e}")
