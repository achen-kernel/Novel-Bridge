#!/usr/bin/env bash
# ============================================================
# NovelBridge — 快速重启 rag-agent（不重启其他服务）
# ============================================================
set -euo pipefail

RAG_DIR="/home/wk/novelbridge/apps/rag-agent"
LOG_DIR="${LOG_DIR:-/home/wk/novelbridge/logs/rag-agent}"
PID_FILE="/home/wk/novelbridge/runtime/pids/rag-agent.pid"

# 停止旧进程
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping old rag-agent (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 2
  fi
fi
# 确保端口释放
fuser -k 18081/tcp 2>/dev/null || true
sleep 1

# 启动新进程
echo "Starting rag-agent..."
PYTHONPATH="$RAG_DIR" nohup "$RAG_DIR/.venv/bin/python" -m app.main --port 18081 \
  > "$LOG_DIR/rag-agent.log" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "rag-agent PID: $NEW_PID"

# 等待就绪
for i in $(seq 1 15); do
  if curl -s --max-time 2 http://127.0.0.1:18081/health >/dev/null 2>&1; then
    echo "rag-agent ready (${i}s)"
    exit 0
  fi
  sleep 1
done

echo "WARNING: rag-agent not responding after 15s, check logs: $LOG_DIR/rag-agent.log"
exit 1
