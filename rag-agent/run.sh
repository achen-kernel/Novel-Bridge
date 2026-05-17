#!/usr/bin/env bash
# ============================================================
# rag-agent — 启动脚本（Linux 远程）
# 用法: bash run.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载本地 .env（如果有）
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

PORT="${RAG_AGENT_PORT:-18081}"

# 激活虚拟环境（如果有）
if [[ -n "${RAG_AGENT_VENV:-}" && -f "$RAG_AGENT_VENV/bin/activate" ]]; then
  source "$RAG_AGENT_VENV/bin/activate"
elif [[ -d .venv ]]; then
  source .venv/bin/activate
fi

# 确保依赖已安装
pip install -q -r requirements.txt 2>/dev/null || true

echo "Starting rag-agent on 0.0.0.0:$PORT ..."
python -m app.main --port "$PORT"
