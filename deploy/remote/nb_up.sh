#!/usr/bin/env bash
# ============================================================
# NovelBridge — 远程一键启动
# 在 Linux 服务器上按依赖顺序启动所有服务。
# 依赖：ports.env, .env, docker-compose.yml 在同一目录
# 用法: bash deploy/remote/nb_up.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---- 加载端口配置 ----
if [[ ! -f ports.env ]]; then
  echo "ERROR: 未找到 ports.env" >&2
  exit 1
fi
set -a
source ports.env
set +a

# 加载 secrets（.env 可选，不强制）
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
else
  echo "WARNING: 未找到 .env，secrets 使用默认/空值"
fi

# 根目录
NB_ROOT="${NB_REMOTE_DEPLOY_DIR:-/home/wk/novelbridge}"

# ---- 必需变量检查 ----
: "${LOG_DIR:?请设置 LOG_DIR（在 .env 中）}"
mkdir -p "$LOG_DIR/llama.cpp" "$LOG_DIR/rag-agent" "$LOG_DIR/mysql" "$LOG_DIR/neo4j" "$LOG_DIR/chroma"

: "${LLAMA_MODEL_PATH:?请设置 LLAMA_MODEL_PATH（在 .env 中）}"
if [[ ! -f "$LLAMA_MODEL_PATH" ]]; then
  echo "ERROR: 模型文件不存在: $LLAMA_MODEL_PATH" >&2
  exit 1
fi

# ---- 工具函数 ----
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_port() {
  local host="$1" port="$2" name="$3"
  if ss -tlnp | grep -q "${host}:${port}"; then
    log "WARNING: $name 端口 $port 已被占用，进程: $(ss -tlnp | grep ":${port} " | head -1)"
    return 1
  fi
  return 0
}

wait_for_port() {
  local host="$1" port="$2" name="$3" timeout="${4:-30}"
  log "等待 $name ($host:$port) 就绪..."
  for i in $(seq 1 "$timeout"); do
    if ss -tlnp | grep -q "${host}:${port}"; then
      log "$name 已就绪（第 ${i}s）"
      return 0
    fi
    sleep 1
  done
  log "ERROR: $name 在 ${timeout}s 内未就绪" >&2
  return 1
}

# ---- 端口预检 ----
log "=== 检查端口占用 ==="
check_port "127.0.0.1" "$MYSQL_PORT" "MySQL" || true
check_port "127.0.0.1" "$NEO4J_BOLT_PORT" "Neo4j" || true
check_port "127.0.0.1" "$LLAMA_PORT" "llama-server" || true
check_port "0.0.0.0" "$RAG_AGENT_PORT" "rag-agent" || true

# ---- 1. MySQL ----
log "=== 启动 MySQL (Docker) ==="
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-$NB_ROOT/data/mysql}"
mkdir -p "$MYSQL_DATA_DIR"
MYSQL_LOG_DIR="$LOG_DIR/mysql"
docker compose up -d mysql 2>&1 | tee -a "$LOG_DIR/nb_up.log" || true
wait_for_port "127.0.0.1" "$MYSQL_PORT" "MySQL" 60

# ---- 2. Neo4j ----
log "=== 启动 Neo4j (Docker) ==="
NEO4J_DATA_DIR="${NEO4J_DATA_DIR:-$NB_ROOT/data/neo4j}"
mkdir -p "$NEO4J_DATA_DIR"
docker compose up -d neo4j 2>&1 | tee -a "$LOG_DIR/nb_up.log" || true
wait_for_port "127.0.0.1" "$NEO4J_BOLT_PORT" "Neo4j-Bolt" 60

# ---- 3. Chroma 数据目录（rag-agent 内嵌，只需确保目录存在） ----
CHROMA_DATA_DIR="${CHROMA_DATA_DIR:-$NB_ROOT/data/chroma}"
mkdir -p "$CHROMA_DATA_DIR"
log "Chroma 数据目录: $CHROMA_DATA_DIR（rag-agent 内嵌，无需独立容器）"

# ---- 4. llama-server ----
log "=== 启动 llama-server ==="
LLAMA_BIN="${LLAMA_BIN:-llama-server}"
if command -v "$LLAMA_BIN" &>/dev/null || [[ -x "$LLAMA_BIN" ]]; then
  if ss -tlnp | grep -q "127.0.0.1:${LLAMA_PORT}"; then
    log "llama-server 已在运行，跳过"
  else
    nohup "$LLAMA_BIN" \
      --host "$LLAMA_HOST" \
      --port "$LLAMA_PORT" \
      -m "$LLAMA_MODEL_PATH" \
      --ctx-size 8192 \
      --no-mmap \
      > "$LOG_DIR/llama.cpp/llama-server.log" 2>&1 &
    LLAMA_PID=$!
    log "llama-server PID: $LLAMA_PID"
    echo "$LLAMA_PID" > "$NB_ROOT/runtime/pids/llama-server.pid" 2>/dev/null || true
    wait_for_port "127.0.0.1" "$LLAMA_PORT" "llama-server" 120
  fi
else
  log "WARNING: llama-server 命令未找到（$LLAMA_BIN），跳过（mock 模式）"
fi

# ---- 5. rag-agent ----
log "=== 启动 rag-agent ==="
RAG_AGENT_DIR="${RAG_AGENT_DIR:-$NB_ROOT/apps/rag-agent}"
if [[ -d "$RAG_AGENT_DIR" ]]; then
  if ss -tlnp | grep -q "0.0.0.0:${RAG_AGENT_PORT}"; then
    log "rag-agent 已在运行，跳过"
  else
    cd "$RAG_AGENT_DIR"
    if [[ -n "${RAG_AGENT_VENV:-}" && -f "$RAG_AGENT_VENV/bin/activate" ]]; then
      source "$RAG_AGENT_VENV/bin/activate"
    fi
    nohup python -m app.main --port "$RAG_AGENT_PORT" \
      > "$LOG_DIR/rag-agent/rag-agent.log" 2>&1 &
    RAG_PID=$!
    log "rag-agent PID: $RAG_PID"
    echo "$RAG_PID" > "$NB_ROOT/runtime/pids/rag-agent.pid" 2>/dev/null || true
    cd "$SCRIPT_DIR"
    wait_for_port "0.0.0.0" "$RAG_AGENT_PORT" "rag-agent" 30
  fi
else
  log "WARNING: RAG_AGENT_DIR 不存在: $RAG_AGENT_DIR，跳过（mock 模式）"
fi

# ---- 最终健康检查 ----
log "=== 执行健康检查 ==="
bash "$SCRIPT_DIR/nb_healthcheck.sh" || true

log "=== 启动完成 ==="
log "Spring Boot 配置: http://<remote-ip>:$RAG_AGENT_PORT"
log "查看日志目录: $LOG_DIR"
echo ""
echo "一键停止: bash $SCRIPT_DIR/nb_down.sh"
echo "查看状态: bash $SCRIPT_DIR/nb_status.sh"
