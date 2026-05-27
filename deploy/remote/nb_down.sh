#!/usr/bin/env bash
# NovelBridge 一键停止脚本
# 用法: ./nb_down.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    set -a; source .env; set +a
fi
if [ -f ports.env ]; then
    set -a; source ports.env; set +a
fi

echo "[INFO] 停止 llama-server 9B + embedding..."
"${SCRIPT_DIR}/stop_llama.sh"

echo "[INFO] 停止 rag-agent..."
if [ -f /tmp/nb_rag_agent.pid ]; then
    PID=$(cat /tmp/nb_rag_agent.pid)
    if kill "$PID" 2>/dev/null; then
        echo "[INFO] 已停止 rag-agent (PID: $PID)"
    else
        echo "[WARN] rag-agent (PID: $PID) 未运行"
    fi
    rm -f /tmp/nb_rag_agent.pid
fi

echo "[INFO] 停止 Docker 服务..."
docker compose down

echo "[INFO] 清理 PID 文件..."
rm -f /tmp/nb_llama.pid /tmp/nb_llama_9b.pid /tmp/nb_embedding.pid /tmp/nb_rag_agent.pid

echo "[INFO] NovelBridge 已停止"
