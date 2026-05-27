#!/usr/bin/env bash
# NovelBridge 健康检查脚本
# 用法: ./nb_healthcheck.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    set -a; source .env; set +a
fi
if [ -f ports.env ]; then
    set -a; source ports.env; set +a
fi

MYSQL_PORT="${MYSQL_PORT:-13306}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-17474}"
QDRANT_PORT="${QDRANT_PORT:-16333}"
LLAMA_PORT="${LLAMA_PORT:-18080}"
EMBEDDING_PORT="${EMBEDDING_PORT:-18082}"
RAG_AGENT_PORT="${RAG_AGENT_PORT:-18081}"

check_service() {
    local name=$1
    local status=$2
    if [ "$status" = "UP" ]; then
        echo "[UP]   $name"
    else
        echo "[DOWN] $name"
    fi
}

# MySQL
if docker exec novelbridge-mysql mysqladmin ping -u root --password="${MYSQL_ROOT_PASSWORD:-}" --silent 2>/dev/null; then
    check_service "MySQL (:${MYSQL_PORT})" "UP"
else
    check_service "MySQL (:${MYSQL_PORT})" "DOWN"
fi

# Neo4j HTTP
if curl -sf "http://127.0.0.1:${NEO4J_HTTP_PORT}/" > /dev/null 2>&1; then
    check_service "Neo4j HTTP (:${NEO4J_HTTP_PORT})" "UP"
else
    check_service "Neo4j HTTP (:${NEO4J_HTTP_PORT})" "DOWN"
fi

# Qdrant (正确端点: /healthz)
if curl -sf "http://127.0.0.1:${QDRANT_PORT}/healthz" > /dev/null 2>&1; then
    check_service "Qdrant (:${QDRANT_PORT})" "UP"
else
    check_service "Qdrant (:${QDRANT_PORT})" "DOWN"
fi

# llama-server
if curl -sf "http://127.0.0.1:${LLAMA_PORT}/v1/models" > /dev/null 2>&1; then
    check_service "llama-server 9B (:${LLAMA_PORT})" "UP"
else
    check_service "llama-server 9B (:${LLAMA_PORT})" "DOWN"
fi

# embedding llama-server
if curl -sf "http://127.0.0.1:${EMBEDDING_PORT}/v1/embeddings" \
    -H 'Content-Type: application/json' \
    -d '{"input":"ping","model":"default"}' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d["data"][0]["embedding"]) == 1024' \
    > /dev/null 2>&1; then
    check_service "Qwen3-Embedding (:${EMBEDDING_PORT})" "UP"
else
    check_service "Qwen3-Embedding (:${EMBEDDING_PORT})" "DOWN"
fi

# rag-agent
if curl -sf "http://127.0.0.1:${RAG_AGENT_PORT}/health" > /dev/null 2>&1; then
    check_service "rag-agent (:${RAG_AGENT_PORT})" "UP"
else
    check_service "rag-agent (:${RAG_AGENT_PORT})" "DOWN"
fi
