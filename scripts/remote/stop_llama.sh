#!/usr/bin/env bash
# 停止 llama-server
set -euo pipefail
PID_FILE="${PID_FILE:-/tmp/nb_llama.pid}"
if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
fi
pkill -f llama-server 2>/dev/null || true
echo "[INFO] llama-server 已停止"
