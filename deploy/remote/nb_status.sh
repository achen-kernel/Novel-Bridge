#!/usr/bin/env bash
# ============================================================
# NovelBridge — 远程服务状态检查
# 快速查看每个服务是否在监听预期端口。
# 用法: bash deploy/remote/nb_status.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f ports.env ]]; then
  set -a
  source ports.env
  set +a
fi

# 状态符号
UP_ICON="✓"
DOWN_ICON="✗"
MOCK_ICON="~"

check_port_listen() {
  local port="$1"
  if ss -tlnp 2>/dev/null | grep -q ":$port "; then
    return 0
  fi
  return 1
}

echo ""
echo "========================================"
echo "  NovelBridge — 远程服务状态"
echo "========================================"
echo "  服务器根目录: ${NB_REMOTE_DEPLOY_DIR:-/home/wk/novelbridge}"
echo ""

# MySQL
if check_port_listen "${MYSQL_PORT:-13306}"; then
  echo "  [$UP_ICON] MySQL          :${MYSQL_PORT:-13306}"
else
  echo "  [$DOWN_ICON] MySQL          :${MYSQL_PORT:-13306}"
fi

# Neo4j
if check_port_listen "${NEO4J_BOLT_PORT:-17687}"; then
  echo "  [$UP_ICON] Neo4j-Bolt     :${NEO4J_BOLT_PORT:-17687}"
else
  echo "  [$DOWN_ICON] Neo4j-Bolt     :${NEO4J_BOLT_PORT:-17687}"
fi
if check_port_listen "${NEO4J_HTTP_PORT:-17474}"; then
  echo "  [$UP_ICON] Neo4j-HTTP     :${NEO4J_HTTP_PORT:-17474}"
else
  echo "  [$DOWN_ICON] Neo4j-HTTP     :${NEO4J_HTTP_PORT:-17474}"
fi

# Chroma（内嵌在 rag-agent 中，无需独立端口检查）
echo "  [ ] Chroma         (embedded in rag-agent)"

# llama-server
if check_port_listen "${LLAMA_PORT:-18080}"; then
  echo "  [$MOCK_ICON] llama-server   :${LLAMA_PORT:-18080}"
  if [[ "$(pgrep -f 'llama-server' 2>/dev/null || true)" != "" ]]; then
    echo "               PID: $(pgrep -f 'llama-server' | head -3 | tr '\n' ' ')"
  fi
else
  echo "  [$DOWN_ICON] llama-server   :${LLAMA_PORT:-18080}"
fi

# rag-agent
if check_port_listen "${RAG_AGENT_PORT:-18081}"; then
  echo "  [$UP_ICON] rag-agent      :${RAG_AGENT_PORT:-18081}"
  RAG_PID=$(pgrep -f 'app.main' 2>/dev/null || true)
  if [[ -n "$RAG_PID" ]]; then
    echo "               PID: $(echo $RAG_PID | head -3 | tr '\n' ' ')"
  fi
else
  echo "  [$DOWN_ICON] rag-agent      :${RAG_AGENT_PORT:-18081}"
fi

echo ""
echo "----------------------------------------"
echo "  端口占用进程详情"
echo "----------------------------------------"
for port_name in MYSQL_PORT NEO4J_BOLT_PORT NEO4J_HTTP_PORT LLAMA_PORT RAG_AGENT_PORT; do
  port_val="${!port_name:-}"
  if [[ -n "$port_val" ]] && check_port_listen "$port_val"; then
    echo "  :$port_val — $(ss -tlnp 2>/dev/null | grep ":$port_val " | head -1 | tr -s ' ')"
  fi
done
echo ""
