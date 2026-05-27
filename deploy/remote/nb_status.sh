#!/usr/bin/env bash
# NovelBridge remote service status.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

[ -f .env ] && { set -a; source .env; set +a; }
[ -f ports.env ] && { set -a; source ports.env; set +a; }

MYSQL_PORT="${MYSQL_PORT:-13306}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-17474}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-17687}"
QDRANT_PORT="${QDRANT_PORT:-16333}"
LLAMA_PORT="${LLAMA_PORT:-18080}"
EMBEDDING_PORT="${EMBEDDING_PORT:-18082}"
RAG_AGENT_PORT="${RAG_AGENT_PORT:-18081}"

container_status() {
  local name="$1"
  if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
    local status
    status="$(docker ps --filter "name=${name}" --format '{{.Status}}')"
    echo "[UP]   ${name} ${status}"
  else
    echo "[DOWN] ${name}"
  fi
}

process_status() {
  local name="$1"
  local port="$2"
  local pid
  pid="$(pgrep -f "llama-server.*port ${port}" 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    echo "[UP]   ${name} (:${port}) pid=${pid}"
  else
    echo "[DOWN] ${name} (:${port})"
  fi
}

container_status novelbridge-mysql
container_status novelbridge-neo4j
container_status novelbridge-qdrant
process_status "llama-server 9B" "$LLAMA_PORT"
process_status "embedding llama-server" "$EMBEDDING_PORT"

if curl -sf "http://127.0.0.1:${RAG_AGENT_PORT}/health" >/dev/null 2>&1; then
  echo "[UP]   rag-agent (:${RAG_AGENT_PORT})"
else
  echo "[DOWN] rag-agent (:${RAG_AGENT_PORT})"
fi

echo ""
echo "Tunnel:"
echo "  ssh -N -L ${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT} \\"
echo "         -L ${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT} \\"
echo "         -L ${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT} \\"
echo "         -L ${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT} \\"
echo "         -L ${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT} \\"
echo "         -L ${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT} \\"
echo "         wk@192.168.3.50"
