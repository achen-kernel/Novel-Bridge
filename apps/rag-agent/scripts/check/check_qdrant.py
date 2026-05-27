"""Check Qdrant index state for Books 6,7,9,10"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

qdrant = QdrantClient(host="127.0.0.1", port=16333)
for col in ["novel_chunks", "novel_chapter_facts"]:
    info = qdrant.get_collection(col)
    print(f"{col}: {info.points_count} total")
    for book_id in [6, 7, 9, 10]:
        cnt = qdrant.count(
            collection_name=col,
            count_filter=Filter(must=[FieldCondition(key="book_id", match=MatchValue(value=book_id))])
        )
        print(f"  book {book_id}: {cnt.count}")
