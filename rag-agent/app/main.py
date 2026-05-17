"""
NovelBridge — rag-agent 主应用

Demo 5B 职责：
- /health 及子路径健康检查端点
- /api/books/upload — 书籍上传
- /api/books/trigger-build — 触发完整构建管线
- /extract/entities — 实体抽取触发
- /review/candidates — 候选实体审核
- /admin/reload-prompts — 重载 Prompt
- /admin/reload-grammars — 重载 Grammar
"""

import argparse
import os
from contextlib import asynccontextmanager

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.books import router as books_router
from app.api.extract import router as extract_router
from app.api.review import router as review_router

RAG_AGENT_PORT = int(os.getenv("RAG_AGENT_PORT", "18081"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[rag-agent] Demo 5B 启动于端口 {RAG_AGENT_PORT}")
    from app.clients.mysql_client import MySQLClient
    from app.clients.llama_cpp_client import LlamaCppClient
    from app.clients.neo4j_client import Neo4jClient
    db = MySQLClient()
    llm = LlamaCppClient()
    neo4j = Neo4jClient()
    print(f"[rag-agent] MySQL: {db.conn.open}, LLM: {llm.health()}, Neo4j: {neo4j.health()}")
    db.close()
    llm.close()
    neo4j.close()
    yield
    print("[rag-agent] 关闭")


app = FastAPI(
    title="NovelBridge rag-agent",
    version="0.2.0",
    description="模型编排与检索服务 — Demo 5B",
    lifespan=lifespan,
)

# ---- Register routers ----
app.include_router(health_router)
app.include_router(books_router)
app.include_router(extract_router)
app.include_router(review_router)


# ---- /build endpoint — called by Java/Spring Boot after book upload ----
# Build runs in background thread; returns immediately with agent_run_id.
import asyncio
import datetime
from fastapi import Query, WebSocket, WebSocketDisconnect


@app.websocket("/build")
async def build_websocket(websocket: WebSocket):
    """Catch Java HTTP clients that send Upgrade headers (treating as WS)."""
    await websocket.accept()
    await websocket.send_json({"status": "ERROR", "message": "Use HTTP POST /build?source_id=X instead of WebSocket"})
    await websocket.close()


def _run_build_in_background(book_source_id: int, agent_run_id: int):
    """Run full build pipeline in a background thread."""
    import threading, time
    from app.clients.mysql_client import MySQLClient
    from app.clients.llama_cpp_client import LlamaCppClient
    from app.clients.neo4j_client import Neo4jClient
    from app.runners.book_build_runner import BookBuildRunner

    # Increase UvicornLogHandler's capture level for background thread
    import logging
    bg_logger = logging.getLogger("rag-agent.build")

    def _do_build():
        # Small delay to let Java transaction commit
        time.sleep(3)
        bg_logger.info(f"[build #{book_source_id}] Background build starting (agent_run #{agent_run_id})")
        db = MySQLClient()
        llm = LlamaCppClient()
        neo4j = Neo4jClient()
        try:
            runner = BookBuildRunner(db=db, llm=llm, neo4j=neo4j)
            result = runner.build(book_source_id=book_source_id, extract_chunks=True)
            bg_logger.info(f"[build #{book_source_id}] Complete: {result['status']}, "
                           f"chapters={result.get('chapters_created', 0)}, "
                           f"chunks={result.get('chunks_created', 0)}, "
                           f"candidates={result.get('candidates_created', 0)}")
        except Exception as e:
            bg_logger.exception(f"[build #{book_source_id}] Background error: {e}")
        finally:
            db.close()
            llm.close()
            neo4j.close()

    thread = threading.Thread(target=_do_build, daemon=True, name=f"build-{book_source_id}")
    thread.start()
    bg_logger.info(f"[build #{book_source_id}] Background thread launched")


import logging
logger = logging.getLogger("uvicorn")

@app.api_route("/build", methods=["GET", "POST"])
async def build_book(source_id: int = Query(..., alias="source_id",
                                            description="book_source_id from novel_book_source")):
    """
    Trigger the full build + entity extraction pipeline for a book_source_id.
    Returns immediately; build runs in background.
    No longer checks MySQL existence to avoid transaction visibility issues.
    """
    logger.info(f"/build HANDLER ENTERED: source_id={source_id}")
    from app.clients.mysql_client import get_connection

    # Use a FRESH connection (not MySQLClient wrapper) to avoid any connection issues
    fresh_conn = get_connection()
    try:
        with fresh_conn.cursor() as cur:
            # Log what we're checking
            cur.execute("SELECT DATABASE() as db")
            db_name = cur.fetchone()["db"]
            logger.info(f"/build connected to database: {db_name}")

            cur.execute("SELECT id, title, status FROM novel_book_source WHERE id = %s", (source_id,))
            row = cur.fetchone()
            if row:
                logger.info(f"/build found source: id={row['id']}, title={repr(row['title'])}, status={row['status']}")
                book_id = row["id"]
            else:
                # Maybe the record was written but not yet visible - log and continue anyway
                logger.warning(f"/build source_id={source_id} NOT FOUND in MySQL; proceeding with build anyway")
                book_id = source_id

            # Create AgentRun
            now = datetime.datetime.now()
            cur.execute(
                "INSERT INTO novel_agent_run (run_type, book_id, status, started_at) VALUES ('BOOK_BUILD', %s, 'RUNNING', %s)",
                (book_id, now),
            )
            agent_run_id = cur.lastrowid

        # Start background build (it will retry finding the source)
        _run_build_in_background(source_id, agent_run_id)

        return {
            "status": "BUILDING",
            "book_source_id": source_id,
            "agent_run_id": agent_run_id,
            "message": f"Build started for book_source #{source_id}, check agent_run #{agent_run_id} for progress",
        }
    finally:
        fresh_conn.close()


# ---- Admin stubs ----
from fastapi import APIRouter
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/reload-prompts")
async def reload_prompts():
    """重载 Prompt 模板（下次抽取时生效）。"""
    # In Demo 5B, prompts are read from files on each call, so reload is implicit
    return {"status": "OK", "detail": "Prompts are loaded from disk on each extraction call"}


@admin_router.post("/reload-grammars")
async def reload_grammars():
    """重载 GBNF Grammar（下次抽取时生效）。"""
    return {"status": "NOT_IMPLEMENTED", "detail": "GBNF grammar support is planned for hardened phase"}


app.include_router(admin_router)


# ---- 入口 ----

def main():
    parser = argparse.ArgumentParser(description="NovelBridge rag-agent")
    parser.add_argument("--port", type=int, default=RAG_AGENT_PORT,
                        help=f"监听端口（默认 {RAG_AGENT_PORT}）")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="监听地址（默认 0.0.0.0）")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
