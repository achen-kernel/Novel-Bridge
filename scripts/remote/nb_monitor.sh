#!/usr/bin/env bash
# ============================================================
# NovelBridge 监控仪表盘
# 一键查看所有服务状态 + Pipeline 进展 + 最近日志
# 用法:
#   ./nb_monitor.sh              # 完整仪表盘
#   ./nb_monitor.sh --watch      # 每 10 秒刷新
#   ./nb_monitor.sh --errors     # 只显示最近的错误
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_DIR="$PROJECT_DIR/deploy/remote"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
STATUS_DIR="$LOG_DIR/status"
API_BASE="http://127.0.0.1:18081"

now() { date '+%Y-%m-%d %H:%M:%S'; }

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'
UP="✅"; DOWN="❌"; WARN="⚠️ "

# 标题
header() {
    clear 2>/dev/null || true
    echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         NovelBridge 远端监控仪表盘                  ║${NC}"
    echo -e "${BOLD}║         $(now)                    ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 服务状态
check_services() {
    echo -e "${BOLD}━━━ 服务状态 ━━━${NC}"

    # MySQL
    if docker exec novelbridge-mysql mysqladmin ping -u root -p"${MYSQL_PASSWORD}" --silent 2>/dev/null; then
        echo -e " ${UP} MySQL       :13306   运行中"
    else
        echo -e " ${DOWN} MySQL       :13306   ${RED}不可用${NC}"
    fi

    # Neo4j
    if curl -sf "http://127.0.0.1:17474/" > /dev/null 2>&1; then
        echo -e " ${UP} Neo4j       :17474/17687   运行中"
    else
        echo -e " ${DOWN} Neo4j       :17474/17687   ${RED}不可用${NC}"
    fi

    # Qdrant
    if curl -sf "http://127.0.0.1:16333/healthz" > /dev/null 2>&1; then
        echo -e " ${UP} Qdrant      :16333   运行中"
    else
        echo -e " ${DOWN} Qdrant      :16333   ${RED}不可用${NC}"
    fi

    # llama-server
    if curl -sf "http://127.0.0.1:18080/v1/models" > /dev/null 2>&1; then
        echo -e " ${UP} llama-server:18080   运行中"
        # 获取模型名
        local model
        model=$(curl -sf "http://127.0.0.1:18080/v1/models" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    models=[m['id'] for m in d.get('data',[])]
    print(models[0] if models else 'unknown')
except: print('unknown')" 2>/dev/null || echo "unknown")
        echo -e "    模型: $model"
    else
        echo -e " ${DOWN} llama-server:18080   ${RED}不可用${NC}"
    fi

    # rag-agent
    local rag_status
    rag_status=$(curl -sf "$API_BASE/health" 2>/dev/null || echo "")
    if [ -n "$rag_status" ]; then
        echo -e " ${UP} rag-agent   :18081   运行中"
        # 检查 systemd 状态
        if systemctl --user is-active rag-agent.service > /dev/null 2>&1; then
            echo -e "    方式: systemd (持久化)"
            local mem
            mem=$(systemctl --user show rag-agent.service -p MemoryCurrent --value 2>/dev/null || echo "?")
            echo -e "    内存: $((mem / 1024 / 1024))MB"
        fi
    else
        echo -e " ${DOWN} rag-agent   :18081   ${RED}不可用${NC}"
    fi

    echo ""
}

# Pipeline 状态
check_pipeline_status() {
    echo -e "${BOLD}━━━ Pipeline 运行状态 ━━━${NC}"

    # 检查是否有正在运行的 pipeline
    local pid_file="$LOG_DIR/.pipeline.pid"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e " ${YELLOW}▶${NC} Pipeline 进程运行中 (PID: $pid)"
        else
            echo -e " ${WARN} Pipeline PID 文件存在但进程已结束"
            rm -f "$pid_file"
        fi
    else
        echo -e " ${GREEN}○${NC} 当前无运行中的 Pipeline"
    fi

    # 读取每本书的状态文件
    echo ""
    local has_status=false
    for f in "$STATUS_DIR"/book-*.json; do
        [ -f "$f" ] || continue
        has_status=true
        local bid stage status msg ts
        bid=$(python3 -c "import json;print(json.load(open('$f')).get('book_id','?'))" 2>/dev/null)
        stage=$(python3 -c "import json;print(json.load(open('$f')).get('stage','?'))" 2>/dev/null)
        status=$(python3 -c "import json;print(json.load(open('$f')).get('status','?'))" 2>/dev/null)
        msg=$(python3 -c "import json;print(json.load(open('$f')).get('message',''))" 2>/dev/null)
        ts=$(python3 -c "import json;print(json.load(open('$f')).get('timestamp',''))" 2>/dev/null)

        local icon
        case "$status" in
            COMPLETED) icon="${UP}";;
            RUNNING)   icon="${YELLOW}▶${NC}";;
            FAILED)    icon="${RED}✗${NC}";;
            OK)        icon="${GREEN}✓${NC}";;
            *)         icon="${WARN}";;
        esac

        echo -e " Book #$bid | $icon $status | Stage: $stage | $msg"
        [ -n "$ts" ] && echo -e "         上次更新: $ts"
    done
    if ! $has_status; then
        echo -e " ${GREEN}(暂无 Pipeline 运行记录)${NC}"
    fi

    echo ""
}

# 最近的错误
check_recent_errors() {
    echo -e "${BOLD}━━━ 最近错误 / 异常 ━━━${NC}"

    local found=false
    # 搜索 rag-agent 日志中的 ERROR
    if [ -f "$LOG_DIR/rag-agent.log" ]; then
        local errors
        errors=$(grep -i "ERROR\|Traceback\|Error" "$LOG_DIR/rag-agent.log" 2>/dev/null | tail -10)
        if [ -n "$errors" ]; then
            found=true
            echo -e " ${RED}rag-agent.log 中的错误:${NC}"
            echo "$errors" | sed 's/^/   /'
        fi
    fi

    # 搜索 pipeline 日志中的 ERROR
    for f in "$LOG_DIR"/book-*-pipeline.log; do
        [ -f "$f" ] || continue
        local errors
        errors=$(grep -i "ERROR\|FAILED\|Traceback" "$f" 2>/dev/null | tail -5)
        if [ -n "$errors" ]; then
            found=true
            local fname
            fname=$(basename "$f")
            echo -e " ${RED}${fname} 中的错误:${NC}"
            echo "$errors" | sed 's/^/   /'
        fi
    done

    if ! $found; then
        echo -e " ${GREEN}(无错误记录)${NC}"
    fi
    echo ""
}

# 磁盘和日志空间
check_disk() {
    echo -e "${BOLD}━━━ 磁盘 / 日志空间 ━━━${NC}"
    echo -e " 日志目录: $LOG_DIR"
    du -sh "$LOG_DIR" 2>/dev/null | awk '{print "  大小: " $1}'
    echo -e " 日志文件数: $(find "$LOG_DIR" -name '*.log' 2>/dev/null | wc -l)"
    df -h / | tail -1 | awk '{print "  磁盘剩余: " $4 " / " $2}'
    echo ""
}

# 全仪表盘
dashboard() {
    header
    check_services
    check_pipeline_status
    check_recent_errors
    check_disk
    echo -e "${CYAN}提示: nb_log.sh <service> 查看实时日志${NC}"
    echo -e "${CYAN}      nb_monitor.sh --errors 只看错误${NC}"
    echo -e "${CYAN}      nb_monitor.sh --watch 实时刷新${NC}"
}

# 只看错误
show_errors() {
    echo -e "${BOLD}━━━ 所有错误汇总 ━━━${NC}"
    check_recent_errors

    echo -e "${BOLD}━━━ 失败的 Pipeline 记录 ━━━${NC}"
    for f in "$STATUS_DIR"/book-*.json; do
        [ -f "$f" ] || continue
        local status
        status=$(python3 -c "import json;print(json.load(open('$f')).get('status',''))" 2>/dev/null)
        if [ "$status" = "FAILED" ]; then
            local bid stage msg ts
            bid=$(python3 -c "import json;print(json.load(open('$f')).get('book_id','?'))" 2>/dev/null)
            stage=$(python3 -c "import json;print(json.load(open('$f')).get('stage','?'))" 2>/dev/null)
            msg=$(python3 -c "import json;print(json.load(open('$f')).get('message',''))" 2>/dev/null)
            ts=$(python3 -c "import json;print(json.load(open('$f')).get('timestamp',''))" 2>/dev/null)
            echo -e " ${RED}✗ Book #$bid | Stage: $stage | $msg${NC}"
            echo -e "   $ts"
        fi
    done
}

# 主入口
main() {
    local mode="${1:-}"

    case "$mode" in
        --watch|-w)
            while true; do
                dashboard
                sleep 10
            done
            ;;
        --errors|-e)
            show_errors
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  (无)       显示完整仪表盘"
            echo "  --watch    每 10 秒刷新"
            echo "  --errors   只显示错误"
            echo "  --help     帮助"
            ;;
        *)
            dashboard
            ;;
    esac
}

main "$@"
