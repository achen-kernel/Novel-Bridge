import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

from app.api import books as books_api
from app.api import browse as browse_api
from app.api import config_api as config_api
from app.api import eval as eval_api
from app.api import facts as facts_api
from app.api import frontend as frontend_api
from app.api import health as health_api
from app.api import pipeline_api as pipeline_api
from app.api import pipeline_v2 as pipeline_v2_api
from app.api import qa as qa_api
from app.api import knowledge_patch as knowledge_patch_api
from app.api import preprocess_agent as preprocess_agent_api
from app.api import reader_agent as reader_agent_api
from app.clients.mysql_client import MysqlClient
from app.config import settings

db_client = MysqlClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    books_api.init_router(db_client)
    browse_api.init_router(db_client)
    eval_api.init_router(db_client)
    facts_api.init_router(db_client)
    pipeline_v2_api.init_router(db_client)
    frontend_api.init_router(db_client)
    health_api.init_router(db_client)
    pipeline_api.init_router(db_client)
    qa_api.init_router(db_client)
    knowledge_patch_api.init_router(db_client)
    preprocess_agent_api.init_router(db_client)
    reader_agent_api.init_router(db_client)

    # 初始化 Pipeline Task 持久化（MySQL 不可用时降级为纯内存模式）
    from app.pipeline.task_manager import task_manager
    from app.stores.task_store import TaskStore
    try:
        task_manager.set_store(TaskStore(db_client.connect()))
        task_manager.restore(limit=100)
    except Exception as e:
        logger.warning("TaskStore init failed (MySQL not reachable?), running in memory-only mode: %s", e)

    # 初始化 Neo4j 客户端（惰性连接，配置完在首次写操作时自动建立连接）

    from app.clients.neo4j_client import neo4j_client
    neo4j_client.configure(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    # 可选预加载 embedding 模型。默认关闭，避免本地未配置模型时阻塞 /health 和 UI 启动。
    # 启动 MemoryManager 定时持久化
    from app.api.reader_agent import _periodic_save
    memory_save_task = asyncio.create_task(_periodic_save())

    if settings.embedding_preload:
        from app.clients.embedding_client import embedding_client
        embedding_client._load_model()

    yield
    # shutdown
    # 持久化所有会话记忆
    from app.api.reader_agent import _save_all_memories_sync
    _save_all_memories_sync()
    memory_save_task.cancel()
    db_client.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    lifespan=lifespan,
)

app.state.settings = settings
app.state.db_client = db_client

# 托管静态文件（CSS/JS/HTML 模板资源）
from pathlib import Path
from fastapi.staticfiles import StaticFiles
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(health_api.router, prefix="", tags=["health"])
app.include_router(books_api.router, tags=["books"])
app.include_router(browse_api.router, tags=["browse"])
app.include_router(config_api.router, tags=["config"])
app.include_router(eval_api.router, tags=["eval"])
app.include_router(frontend_api.router, tags=["frontend"])
app.include_router(facts_api.router, tags=["facts"])
app.include_router(pipeline_api.router, tags=["pipeline"])
app.include_router(qa_api.router, tags=["qa"])
app.include_router(knowledge_patch_api.router, tags=["knowledge-patches"])
app.include_router(preprocess_agent_api.router, tags=["preprocess-agent"])
app.include_router(pipeline_v2_api.router, tags=["pipeline-v2"])
app.include_router(reader_agent_api.router, tags=["reader-agent"])


@app.get("/")
async def root():
    return RedirectResponse(url="/demo")
