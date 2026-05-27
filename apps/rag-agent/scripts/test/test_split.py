"""Test the new smart text splitter"""
from app.utils.text_splitter import smart_split_text

# Test: three paragraphs with paragraph breaks
t = "这是第一段。" * 3000 + "\n\n" + "这是第二段。" * 3000 + "\n\n" + "这是第三段。" * 3000
print(f"Test text: {len(t)} chars")
segs = smart_split_text(t, max_chars=20000, parent_chunk_id=999)
for s in segs:
    print(f"  Segment {s.split_index}/{s.total_splits}: {len(s.text)} chars, strategy={s.split_strategy}, parent={s.parent_chunk_id}")
print(f"Total segments: {len(segs)}")

# Also verify the embedding_client MAX_CHARS
from app.clients.embedding_client import embedding_client
print(f"\nEmbedding MAX_CHARS: {embedding_client.MAX_CHARS}")
print("OK")
