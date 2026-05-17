#!/usr/bin/env bash
# ============================================================
# NovelBridge — 打包远端变更供本地同步
# 用法: bash scripts/remote/nb_pack_sync.sh
# 输出: /home/wk/novelbridge/sync.tar.gz
#
# 传到本地（在本地 PowerShell 执行）：
#   scp wk@192.168.3.50:/home/wk/novelbridge/sync.tar.gz .
#   tar xzf sync.tar.gz
# ============================================================
set -euo pipefail

ROOT="/home/wk/novelbridge"
OUTPUT="$ROOT/sync.tar.gz"

echo "=== NovelBridge 远端打包 ==="
echo "输出: $OUTPUT"
echo ""

# 要打包的目录/文件（排除运行时/密码/缓存）
cd "$ROOT"

tar czf "$OUTPUT" \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  AGENTS_remote.md \
  novel_bridge_demo_5_gbnf_开发需求文档_v_0_1.md \
  .vtl/vtl-adapter.json \
  apps/rag-agent/app/ \
  apps/rag-agent/requirements.txt \
  apps/rag-agent/run.sh \
  deploy/remote/ \
  scripts/remote/ \
  docs/learn_remote/ \
  .opencode/skills/vibe-learn_remote/ \
  2>&1

echo ""
echo "=== 打包完成 ==="
ls -lh "$OUTPUT"

echo ""
echo "=== 传到本地 ==="
echo "# 在本地 PowerShell 执行："
echo "scp wk@192.168.3.50:/home/wk/novelbridge/sync.tar.gz ."
echo "tar xzf sync.tar.gz"
echo ""
echo "=== 注意 ==="
echo "本地路径差异：apps/rag-agent/ → rag-agent/"
echo "解压后手动把 apps/rag-agent/ 内容移到 rag-agent/"
