#!/usr/bin/env bash
# NovelBridge llama-server 启动脚本
# 用法: ./start_llama.sh [--cuda <id>] [--port <port>]
# 默认: CUDA 卡 1, 端口 18080
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LLAMA_BIN="$PROJECT_DIR/apps/llama.cpp/build/bin/llama-server"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"

# 从 .env 加载模型路径
ENV_FILE="$PROJECT_DIR/deploy/remote/.env"
MODEL_PATH=""
if [ -f "$ENV_FILE" ]; then
    MODEL_PATH=$(grep -oP '^LLAMA_MODEL_PATH=\K.*' "$ENV_FILE" 2>/dev/null || echo "")
fi
MODEL_PATH="${MODEL_PATH:-$PROJECT_DIR/models/Qwen3.5-9B/Qwen3.5-9B-Q8_0.gguf}"

CUDA_DEVICE="${CUDA_DEVICE:-1}"
PORT="${LLAMA_PORT:-18080}"
CTX_SIZE="${LLAMA_CTX_SIZE:-65536}"
NGL="${LLAMA_NGL:-99}"
BATCH_SIZE="${LLAMA_BATCH_SIZE:-2048}"
UBATCH_SIZE="${LLAMA_UBATCH_SIZE:-2048}"
CHAT_TEMPLATE_FILE="${LLAMA_CHAT_TEMPLATE_FILE:-$(dirname "$MODEL_PATH")/chat_template.jinja}"

# 解析参数
while [ $# -gt 0 ]; do
    case "$1" in
        --cuda) shift; CUDA_DEVICE="$1"; shift ;;
        --port) shift; PORT="$1"; shift ;;
        *) shift ;;
    esac
done

mkdir -p "$LOG_DIR"

echo "[INFO] 启动 llama-server"
echo "  Model:    $MODEL_PATH"
echo "  CUDA:     $CUDA_DEVICE"
echo "  Port:     $PORT"
echo "  Context:  $CTX_SIZE"
echo "  Offload:  $NGL layers"
echo ""

# 停止旧实例
pkill -f "llama-server.*port ${PORT}" 2>/dev/null || true
sleep 1

# 用指定 CUDA 卡启动
CUDA_VISIBLE_DEVICES="$CUDA_DEVICE" nohup "$LLAMA_BIN" \
    --host 127.0.0.1 \
    --port "$PORT" \
    -m "$MODEL_PATH" \
    --ctx-size "$CTX_SIZE" \
    --batch-size "$BATCH_SIZE" \
    --ubatch-size "$UBATCH_SIZE" \
    -ngl "$NGL" \
    --chat-template-file "$CHAT_TEMPLATE_FILE" \
    --jinja --reasoning off \
    > "${LOG_DIR}/llama-server.log" 2>&1 &

LLAMA_PID=$!
echo "$LLAMA_PID" > /tmp/nb_llama.pid
echo "[INFO] llama-server PID: $LLAMA_PID"
echo "[INFO] 日志: ${LOG_DIR}/llama-server.log"

# 等待启动
sleep 3
if kill -0 "$LLAMA_PID" 2>/dev/null; then
    echo "[INFO] ✅ llama-server 启动成功 (CUDA:$CUDA_DEVICE, 端口:$PORT)"
else
    echo "[ERROR] ❌ llama-server 启动失败，检查日志:"
    tail -10 "${LOG_DIR}/llama-server.log"
    exit 1
fi
