from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "novelbridge-rag-agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 13306
    mysql_user: str = "novel_bridge"
    mysql_password: str = ""
    mysql_database: str = "novel_bridge"

    # Qdrant
    qdrant_url: str = "http://127.0.0.1:16333"
    qdrant_collection_chunks: str = "novel_chunks"
    qdrant_collection_chapter_facts: str = "novel_chapter_facts"

    # Embedding
    embedding_provider: str = "llama"  # local | llama
    embedding_api_url: str = "http://127.0.0.1:18082/v1/embeddings"
    embedding_base_url: str = "http://127.0.0.1:18082"
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_model_local_path: str = "/home/wk/novelbridge/models/Qwen3-Embedding-0.6B/Qwen/Qwen3-Embedding-0___6B"
    embedding_dim: int = 1024
    embedding_distance: str = "cosine"
    embedding_device: str = "cpu"
    embedding_preload: bool = False
    embedding_timeout: float = 30.0
    embedding_health_timeout: float = 10.0

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 300

    # Local LLM (llama-server)
    llama_base_url: str = "http://127.0.0.1:18080"
    llama_max_tokens: int = 16384
    llama_ctx_size: int = 65536

    # Neo4j
    neo4j_uri: str = "bolt://127.0.0.1:17687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
