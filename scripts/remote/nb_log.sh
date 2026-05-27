#!/usr/bin/env bash
# NovelBridge 日志查看脚本
# 用法:
#   ./nb_log.sh                    # 列出可用的日志源
#   ./nb_log.sh rag                # rag-agent 日志（实时跟踪）
#   ./nb_log.sh llama              # llama-server 日志
#   ./nb_log.sh mysql              # MySQL docker 日志
#   ./nb_log.sh neo4j              # Neo4j docker 日志
#   ./nb_log.sh pipeline 1         # Book 1 的 pipeline 日志
#   ./nb_log.sh pipeline 1 --tail  # 只看末尾 50 行
#   ./nb_log.sh errors             # 所有日志中的错误
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_DIR/deploy/remote"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"

cd "$DEPLOY_DIR"
if [ -f .env ]; then set -a; source .env; set +a; fi
LOG_DIR="${LOG_DIR:-/home/wk/novelbridge/logs}"

SERVICE="${1:-help}"
shift || true

case "$SERVICE" in
    llama)
        echo "[INFO] 跟踪 llama-server 日志 (${LOG_DIR}/llama-server.log)"
        tail -f "${LOG_DIR}/llama-server.log"
        ;;
    rag)
        echo "[INFO] 跟踪 rag-agent 日志 (${LOG_DIR}/rag-agent.log)"
        tail -f "${LOG_DIR}/rag-agent.log"
        ;;
    mysql)
        echo "[INFO] 跟踪 MySQL docker 日志"
        docker logs -f novelbridge-mysql
        ;;
    neo4j)
        echo "[INFO] 跟踪 Neo4j docker 日志"
        docker logs -f novelbridge-neo4j
        ;;
    pipeline|pl)
        BOOK_ID="${1:-}"
        if [ -z "$BOOK_ID" ]; then
            echo "[ERROR] 请指定 Book ID: ./nb_log.sh pipeline <book_id>"
            echo "  可用 pipeline 日志:"
            for f in "$LOG_DIR"/book-*-pipeline.log; do
                [ -f "$f" ] || continue
                echo "    $(basename "$f" | sed 's/book-\(.*\)-pipeline.log/  Book \1/')"
            done
            exit 1
        fi
        LOG_FILE="${LOG_DIR}/book-${BOOK_ID}-pipeline.log"
        if [ ! -f "$LOG_FILE" ]; then
            echo "[ERROR] 找不到 Book $BOOK_ID 的 pipeline 日志: $LOG_FILE"
            exit 1
        fi
        shift
        if [ "${1:-}" = "--tail" ]; then
            echo "[INFO] Book $BOOK_ID pipeline 日志 (末尾 50 行):"
            tail -50 "$LOG_FILE"
        else
            echo "[INFO] 跟踪 Book $BOOK_ID pipeline 日志"
            tail -f "$LOG_FILE"
        fi
        ;;
    errors|err)
        echo "[INFO] 扫描所有日志中的错误..."
        echo "=== rag-agent.log ==="
        grep -n -i "ERROR\|Traceback\|Error\|exception" "${LOG_DIR}/rag-agent.log" 2>/dev/null | tail -20 || echo "(无)"
        echo ""
        echo "=== llama-server.log ==="
        grep -n -i "ERROR\|Traceback\|Error\|exception" "${LOG_DIR}/llama-server.log" 2>/dev/null | tail -20 || echo "(无)"
        echo ""
        echo "=== Pipeline 日志 ==="
        for f in "$LOG_DIR"/book-*-pipeline.log; do
            [ -f "$f" ] || continue
            fname=$(basename "$f")
            matches=$(grep -n -i "ERROR\|FAILED\|Traceback\|exception" "$f" 2>/dev/null | tail -10)
            if [ -n "$matches" ]; then
                echo "--- $fname ---"
                echo "$matches"
            fi
        done
        ;;
    all)
        echo "[INFO] 同时跟踪所有日志 (Ctrl+C 退出)..."
        echo "=== llama-server ==="
        tail -f "${LOG_DIR}/llama-server.log" &
        echo "=== rag-agent ==="
        tail -f "${LOG_DIR}/rag-agent.log" &
        echo "=== mysql ==="
        docker logs -f novelbridge-mysql &
        echo "=== neo4j ==="
        docker logs -f novelbridge-neo4j &
        wait
        ;;
    list|ls)
        echo "可用的日志源:"
        echo "  rag        rag-agent 日志 (${LOG_DIR}/rag-agent.log)"
        echo "  llama      llama-server 日志 (${LOG_DIR}/llama-server.log)"
        echo "  mysql      MySQL docker 日志"
        echo "  neo4j      Neo4j docker 日志"
        echo "  pipeline   Pipeline 运行日志 (按 book)"
        echo "  errors     所有日志中的错误汇总"
        echo "  all        同时跟踪所有"
        echo ""
        echo "Pipeline 日志:"
        for f in "$LOG_DIR"/book-*-pipeline.log; do
            [ -f "$f" ] || continue
            echo "  $(basename "$f" | sed 's/book-\(.*\)-pipeline.log/  Book \1/')"
        done
        ;;
    help|*)
        echo "用法: $0 <service> [参数]"
        echo ""
        echo "服务:"
        echo "  rag                  跟踪 rag-agent 日志"
        echo "  llama                跟踪 llama-server 日志"
        echo "  mysql                跟踪 MySQL 日志"
        echo "  neo4j                跟踪 Neo4j 日志"
        echo "  pipeline <book_id>   跟踪指定书的 pipeline 日志"
        echo "  pipeline <book_id> --tail  只看末尾 50 行"
        echo "  errors               查看所有错误"
        echo "  all                  同时跟踪所有服务日志"
        echo "  list                 列出所有日志源"
        echo ""
        echo "示例:"
        echo "  $0 rag                     # 看 rag-agent 实时日志"
        echo "  $0 pipeline 1              # 看 Book 1 的 pipeline 进度"
        echo "  $0 pipeline 1 --tail       # 看 Book 1 的 pipeline 结果"
        echo "  $0 errors                  # 看所有错误"
        ;;
esac
