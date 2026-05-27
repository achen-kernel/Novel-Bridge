"""Diagnose empty answer issue — run against real MySQL via SSH tunnel."""
import sys, asyncio, logging
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

logging.basicConfig(level=logging.INFO)

from app.clients.mysql_client import MysqlClient
from app.qa.qa_runner import QaRunner


async def main():
    db = MysqlClient()
    conn = db.connect()

    # 1. Check book 6 exists
    with conn.cursor() as c:
        c.execute("SELECT id, title FROM novel_book WHERE id = 6")
        book = c.fetchone()
        print(f"[BOOK] {book}")

        c.execute("SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 6")
        print(f"[CHUNKS] {c.fetchone()}")

        c.execute("SELECT COUNT(*) as cnt FROM novel_chapter WHERE book_id = 6")
        print(f"[CHAPTERS] {c.fetchone()}")

        c.execute("SELECT COUNT(*) as cnt FROM novel_entity_profile WHERE book_id = 6")
        print(f"[ENTITIES] {c.fetchone()}")

    from app.qa.retrieval_runner import RetrievalRunner
    retriever = RetrievalRunner(conn)

    # 2. Check search before LLM call
    results = await retriever.hybrid_search("孙悟空是谁？", 6, top_k=8)
    print(f"[SEARCH] {len(results)} results:")
    for r in results[:5]:
        print(f"  source={r.get('source')} id={r.get('id')} score={r.get('score'):.4f}")

    # 3. Run full answer
    runner = QaRunner(conn)
    print("\n[QA] Calling QaRunner.answer()...")
    result = await runner.answer(
        session_id=0,
        book_id=6,
        question="孙悟空是谁？",
        use_deepseek=False,
    )
    answer = result.get("answer", "")
    citations = result.get("citations", [])
    print(f"[QA] answer len={len(answer)}, citations={len(citations)}")
    print(f"[QA] answer preview: {answer[:300]}")
    print(f"[QA] citations: {citations[:5]}")

    # 4. Also try with DeepSeek to compare
    print("\n[QA-DS] Calling with DeepSeek...")
    result2 = await runner.answer(  # type: ignore[has-type]
        session_id=0,
        book_id=6,
        question="孙悟空是谁？",
        use_deepseek=True,
    )
    answer2 = result2.get("answer", "")
    citations2 = result2.get("citations", [])
    print(f"[QA-DS] answer len={len(answer2)}, citations={len(citations2)}")
    print(f"[QA-DS] answer preview: {answer2[:300]}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
