#!/usr/bin/env bash
# NovelBridge 一键启动脚本
# 用法: ./nb_up.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    set -a; source .env; set +a
else
    echo "[ERROR] .env 文件不存在，请从 .env.example 复制并填写"
    exit 1
fi

if [ -f ports.env ]; then
    set -a; source ports.env; set +a
fi

# 创建日志目录
REMOTE_ROOT="${REMOTE_ROOT:-/home/wk/novelbridge}"
LOG_DIR="${LOG_DIR:-${REMOTE_ROOT}/logs}"
mkdir -p "${LOG_DIR}/llama-9b" "${LOG_DIR}/embedding" "${LOG_DIR}/rag-agent" "${LOG_DIR}/pipeline"

echo "[INFO] 启动 Docker 服务: mysql neo4j qdrant..."
docker compose up -d mysql neo4j qdrant

echo "[INFO] 启动 llama-server 9B..."
"${SCRIPT_DIR}/start_llama_9b.sh"

echo "[INFO] 启动 Qwen3-Embedding llama-server..."
"${SCRIPT_DIR}/start_embedding.sh"

echo "[INFO] 启动 rag-agent..."
if [ -d "${RAG_AGENT_DIR:-}" ] && [ -x "${RAG_AGENT_VENV:-}/bin/python" ]; then
    nohup "${RAG_AGENT_VENV}/bin/python" -m uvicorn app.main:app \
        --host 127.0.0.1 \
        --port "${RAG_AGENT_PORT:-18081}" \
        --workers 1 \
        --log-level info \
        > "${LOG_DIR}/rag-agent/rag-agent.log" 2>&1 &
    echo $! > /tmp/nb_rag_agent.pid
    echo "[INFO] rag-agent PID: $(cat /tmp/nb_rag_agent.pid)"
else
    echo "[WARN] RAG_AGENT_DIR 或虚拟环境未就绪，跳过 rag-agent"
fi

echo "[INFO] 等待服务启动..."
sleep 5

echo ""
echo "=========================================="
echo " NovelBridge 服务启动状态"
echo "=========================================="
echo "MySQL:    127.0.0.1:${MYSQL_PORT:-13306}"
echo "Neo4j:    127.0.0.1:${NEO4J_HTTP_PORT:-17474} (HTTP) / ${NEO4J_BOLT_PORT:-17687} (Bolt)"
echo "Qdrant:   127.0.0.1:${QDRANT_PORT:-16333}"
echo "llama:    127.0.0.1:${LLAMA_PORT:-18080}"
echo "embed:    127.0.0.1:${EMBEDDING_PORT:-18082}"
echo "rag:      127.0.0.1:${RAG_AGENT_PORT:-18081}"
echo "=========================================="
