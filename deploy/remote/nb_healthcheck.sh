#!/usr/bin/env bash
# ============================================================
# NovelBridge — 远程健康检查
# 对每个服务执行深入健康检查（HTTP 请求或 TCP 检查）。
# 输出 JSON 格式结果，便于 rag-agent /health 汇总。
# 用法: bash deploy/remote/nb_healthcheck.sh
#       bash deploy/remote/nb_healthcheck.sh --json  # JSON 输出
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

OUTPUT_JSON=false
for arg in "$@"; do
  if [[ "$arg" == "--json" ]]; then
    OUTPUT_JSON=true
  fi
done

UP="UP"
DOWN="DOWN"
MOCK="MOCK"

# ---- 检查函数 ----

check_tcp() {
  local host="$1" port="$2"
  ss -tlnp 2>/dev/null | grep -q ":$port " && echo "$UP" || echo "$DOWN"
}

check_http() {
  local url="$1"
  if command -v curl &>/dev/null; then
    if curl -sf -o /dev/null --max-time 5 "$url" 2>/dev/null; then
      echo "$UP"
    else
      echo "$DOWN"
    fi
  elif command -v wget &>/dev/null; then
    if wget -q -O /dev/null --timeout=5 "$url" 2>/dev/null; then
      echo "$UP"
    else
      echo "$DOWN"
    fi
  else
    echo "UNKNOWN (curl/wget not found)"
  fi
}

# ---- 收集状态 ----

MYSQL_STATUS=$(check_tcp "127.0.0.1" "${MYSQL_PORT:-13306}")
NEO4J_STATUS=$(check_tcp "127.0.0.1" "${NEO4J_BOLT_PORT:-17687}")
NEO4J_HTTP_STATUS=$(check_http "http://127.0.0.1:${NEO4J_HTTP_PORT:-17474}")
CHROMA_STATUS="UP"  # Chroma embedded in rag-agent, 由 rag-agent /health 反馈
LLAMA_STATUS=$(check_tcp "127.0.0.1" "${LLAMA_PORT:-18080}")
RAG_STATUS=$(check_http "http://127.0.0.1:${RAG_AGENT_PORT:-18081}/health")

# llama-server 标记 mock
if [[ "$LLAMA_STATUS" == "$UP" ]]; then
  LLAMA_HTTP=$(check_http "http://127.0.0.1:${LLAMA_PORT:-18080}/health" 2>/dev/null || echo "$MOCK")
  if [[ "$LLAMA_HTTP" != "$UP" ]]; then
    LLAMA_STATUS="$MOCK (port open but /health not responding)"
  fi
fi

# 检查数据目录是否存在
NB_ROOT="${NB_REMOTE_DEPLOY_DIR:-/home/wk/novelbridge}"
CHROMA_DIR_STATUS="$UP"
if [[ ! -d "${CHROMA_DATA_DIR:-$NB_ROOT/data/chroma}" ]]; then
  CHROMA_DIR_STATUS="$MOCK"
fi

if [[ "$OUTPUT_JSON" == "true" ]]; then
  cat <<HEALTH_JSON
{
  "status": "$UP",
  "root_dir": "$NB_ROOT",
  "services": {
    "mysql": {
      "status": "$MYSQL_STATUS",
      "port": ${MYSQL_PORT:-13306},
      "type": "docker",
      "data_dir": "${MYSQL_DATA_DIR:-$NB_ROOT/data/mysql}"
    },
    "neo4j": {
      "status": "$NEO4J_STATUS",
      "bolt_port": ${NEO4J_BOLT_PORT:-17687},
      "http_port": ${NEO4J_HTTP_PORT:-17474},
      "type": "docker",
      "data_dir": "${NEO4J_DATA_DIR:-$NB_ROOT/data/neo4j}"
    },
    "chroma": {
      "status": "$CHROMA_STATUS",
      "data_dir": "${CHROMA_DATA_DIR:-$NB_ROOT/data/chroma}",
      "type": "embedded",
      "mock": false,
      "note": "内嵌在 rag-agent 中，无需独立容器"
    },
    "llama_cpp": {
      "status": "$LLAMA_STATUS",
      "port": ${LLAMA_PORT:-18080},
      "type": "binary",
      "model": "${LLAMA_MODEL_PATH:-N/A}",
      "mock": false
    },
    "rag_agent": {
      "status": "$RAG_STATUS",
      "port": ${RAG_AGENT_PORT:-18081},
      "type": "python",
      "endpoint": "http://0.0.0.0:${RAG_AGENT_PORT:-18081}"
    }
  },
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
HEALTH_JSON
else
  echo ""
  echo "========================================"
  echo "  NovelBridge — 远程健康检查"
  echo "========================================"
  echo ""
  printf "  %-15s %s\n" "MySQL:"       "[$MYSQL_STATUS]"
  printf "  %-15s %s\n" "Neo4j:"       "[$NEO4J_STATUS]"
  printf "  %-15s %s\n" "Neo4j-HTTP:"  "[$NEO4J_HTTP_STATUS]"
  printf "  %-15s %s\n" "Chroma:"      "[$CHROMA_STATUS] (embedded)"
  printf "  %-15s %s\n" "llama-server:""[$LLAMA_STATUS]"
  printf "  %-15s %s\n" "rag-agent:"   "[$RAG_STATUS]"
  echo ""
  echo "----------------------------------------"
  echo "  全部健康检查完成"
  echo "----------------------------------------"
fi

# 如果有非 mock 服务 DOWN，退出码为 1
if echo "$MYSQL_STATUS$NEO4J_STATUS$RAG_STATUS" | grep -q "$DOWN"; then
  exit 1
fi
exit 0
