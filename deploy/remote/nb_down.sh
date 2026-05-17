#!/usr/bin/env bash
# ============================================================
# NovelBridge — 远程一键停止
# 逆序停止所有服务。
# 用法: bash deploy/remote/nb_down.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f ports.env ]]; then
  set -a
  source ports.env
  set +a
fi

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

LOG_DIR="${LOG_DIR:-/home/wk/novelbridge/logs}"
mkdir -p "$LOG_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== 停止服务（逆序）==="

# 1. rag-agent
log "停止 rag-agent..."
pkill -f "app.main.*--port ${RAG_AGENT_PORT:-18081}" 2>/dev/null && log "rag-agent 已停止" || log "rag-agent 未运行"

# 2. llama-server
log "停止 llama-server..."
pkill -f "llama-server.*--port ${LLAMA_PORT:-18080}" 2>/dev/null && log "llama-server 已停止" || log "llama-server 未运行"

# 3. Docker 服务
log "停止 Neo4j..."
docker compose down neo4j 2>/dev/null || true

log "停止 MySQL..."
docker compose down mysql 2>/dev/null || true

log "=== 所有服务已停止 ==="
