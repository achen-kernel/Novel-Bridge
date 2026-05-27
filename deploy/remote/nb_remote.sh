#!/usr/bin/env bash
# ============================================================
# NovelBridge 远端服务管理（本地 → SSH → 远端）
# 从本地开发机通过 SSH 控制远端服务器的全部基础设施服务。
#
# 用法:
#   ./nb_remote.sh start           # 启动远端全部服务
#   ./nb_remote.sh stop            # 停止全部
#   ./nb_remote.sh status          # 查看状态
#   ./nb_remote.sh logs            # 查看最近日志
#   ./nb_remote.sh restart         # 重启全部
#   ./nb_remote.sh ssh             # 打开 SSH 连到远端
# ============================================================
set -euo pipefail

# ---- 配置（从 .env 加载）----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
PORTS_FILE="$SCRIPT_DIR/ports.env"

# .env 必须在本地有（含远端 IP/User）——删掉 MYSQL_PASSWORD 等远端密文也可以
if [ ! -f "$ENV_FILE" ]; then
    echo "[ERROR] 本地 $ENV_FILE 不存在，请从 .env.example 复制并填写"
    echo "        必需字段: NB_REMOTE_HOST, NB_REMOTE_USER"
    exit 1
fi
set -a; source "$ENV_FILE"; set +a
[ -f "$PORTS_FILE" ] && { set -a; source "$PORTS_FILE"; set +a; }

# 远端路径
REMOTE_HOST="${NB_REMOTE_HOST:-}"       # 远端 IP
REMOTE_USER="${NB_REMOTE_USER:-wk}"     # SSH 用户
REMOTE_DIR="${NB_REMOTE_DEPLOY_DIR:-/home/wk/novelbridge}"  # 远端项目根

# 端口
MYSQL_PORT="${MYSQL_PORT:-13306}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-17474}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-17687}"
QDRANT_PORT="${QDRANT_PORT:-16333}"
LLAMA_PORT="${LLAMA_PORT:-18080}"
EMBEDDING_PORT="${EMBEDDING_PORT:-18082}"

# SSH 基础命令
SSH_CMD="ssh ${REMOTE_USER}@${REMOTE_HOST}"

# ---- 颜色 ----
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn()  { echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $1"; }
err()   { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; }

# ---- 帮助 ----
usage() {
    echo "用法: $(basename "$0") {start|stop|status|logs|restart|ssh}"
    echo ""
    echo "  start    启动远端全部服务（Docker + llama-server）"
    echo "  stop     停止全部服务"
    echo "  status   查看各服务状态"
    echo "  logs     查看最近 2 分钟日志"
    echo "  restart  重启全部服务"
    echo "  ssh      打开 SSH 连接到远端"
    echo ""
    echo "必需配置 (.env): NB_REMOTE_HOST, NB_REMOTE_USER"
}

# ---- SSH helper：在远端执行命令 ----
remote_exec() {
    $SSH_CMD -o ConnectTimeout=10 -o StrictHostKeyChecking=no "cd $REMOTE_DIR/deploy/remote && $*"
}

# ---- 启动 Docker 容器 ----
start_docker() {
    info "远端启动 Docker 容器..."
    remote_exec "
        for c in novelbridge-mysql novelbridge-neo4j novelbridge-qdrant; do
            docker ps -a --format '{{.Names}}' | grep -q \"^\$c$\" && docker rm -f \"\$c\" 2>/dev/null || true
        done
        docker compose up -d mysql neo4j qdrant
    "

    # 等待就绪
    for name in novelbridge-mysql novelbridge-neo4j novelbridge-qdrant; do
        local max_wait=60
        [ "$name" = "novelbridge-qdrant" ] && max_wait=15
        local waited=0
        while [ $waited -lt $max_wait ]; do
            if remote_exec "docker ps --format '{{.Names}}' | grep -q '^$name$'"; then
                break
            fi
            sleep 2
            waited=$((waited + 2))
        done
        if remote_exec "docker ps --format '{{.Names}}' | grep -q '^$name$'"; then
            local status
            status=$(remote_exec "docker ps --filter 'name=$name' --format '{{.Status}}' | cut -d' ' -f1-2")
            info "  ✅ $name 已启动 (${status})"
        else
            err "  ❌ $name 启动失败（等待 ${waited}s 后仍未就绪）"
        fi
    done
}

# ---- 启动 llama-server（远端 cuda:1）----
start_models() {
    info "远端启动 llama-server 9B + embedding (cuda:1)..."
    remote_exec "./start_llama_9b.sh"
    remote_exec "./start_embedding.sh"
}

# ---- 停止全部 ----
stop_all() {
    warn "停止远端全部服务..."
    remote_exec "
        ./stop_llama.sh 2>/dev/null || true
        cd ${REMOTE_DIR}/deploy/remote
        docker compose stop mysql neo4j qdrant 2>/dev/null || true
        for c in novelbridge-mysql novelbridge-neo4j novelbridge-qdrant; do
            docker rm -f \"\$c\" 2>/dev/null || true
        done
    "
    info "远端全部服务已停止"
}

# ---- 状态 ----
check_status() {
    echo ""
    echo -e "${CYAN}━━━ 远端服务状态（${REMOTE_HOST}）━━━${NC}"
    echo ""

    # Docker
    for name in novelbridge-mysql novelbridge-neo4j novelbridge-qdrant; do
        local port status
        case "$name" in
            novelbridge-mysql)  port="$MYSQL_PORT" ;;
            novelbridge-neo4j)  port="$NEO4J_HTTP_PORT/$NEO4J_BOLT_PORT" ;;
            novelbridge-qdrant) port="$QDRANT_PORT" ;;
        esac
        if remote_exec "docker ps --format '{{.Names}}' | grep -q '^$name$'"; then
            status=$(remote_exec "docker ps --filter 'name=$name' --format '{{.Status}}' | cut -d' ' -f1-2")
            echo -e " ${GREEN}✅${NC} $name (:${port})  ${status}"
        else
            echo -e " ${RED}❌${NC} $name (:${port})  — 已停止"
        fi
    done

    # llama-server
    local pid
    pid=$(remote_exec "pgrep -f 'llama-server.*port ${LLAMA_PORT}'" 2>/dev/null || echo "")
    if [ -n "$pid" ]; then
        local mem
        mem=$(remote_exec "ps -o rss= -p $pid 2>/dev/null | awk '{printf \"%.0fMB\", \$1/1024}'" 2>/dev/null || echo "?")
        echo -e " ${GREEN}✅${NC} llama-server (:${LLAMA_PORT})  PID ${pid}, ${mem}"
    else
        echo -e " ${RED}❌${NC} llama-server (:${LLAMA_PORT})  — 未启动"
    fi

    pid=$(remote_exec "pgrep -f 'llama-server.*port ${EMBEDDING_PORT}'" 2>/dev/null || echo "")
    if [ -n "$pid" ]; then
        local mem
        mem=$(remote_exec "ps -o rss= -p $pid 2>/dev/null | awk '{printf \"%.0fMB\", \$1/1024}'" 2>/dev/null || echo "?")
        echo -e " ${GREEN}✅${NC} Qwen3-Embedding (:${EMBEDDING_PORT})  PID ${pid}, ${mem}"
    else
        echo -e " ${RED}❌${NC} Qwen3-Embedding (:${EMBEDDING_PORT})  — 未启动"
    fi

    echo ""
    echo "连接信息（本地开 SSH tunnel）："
    echo "  ssh -N -L ${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT} \\"
    echo "         -L ${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT} \\"
    echo "         -L ${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT} \\"
    echo "         -L ${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT} \\"
    echo "         -L ${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT} \\"
    echo "         -L ${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT} \\"
    echo "         ${REMOTE_USER}@${REMOTE_HOST}"
}

# ---- 日志 ----
show_logs() {
    echo ""
    echo -e "${CYAN}━━━ 远端服务日志（${REMOTE_HOST}，最近 2 分钟）━━━${NC}"
    echo ""
    echo "--- llama-server 9B ---"
    remote_exec "tail -20 ${REMOTE_DIR}/logs/llama-9b/llama-server.log 2>/dev/null || echo '(空)'"
    echo ""
    echo "--- embedding ---"
    remote_exec "tail -20 ${REMOTE_DIR}/logs/embedding/embedding-server.log 2>/dev/null || echo '(空)'"
    echo ""
    echo "--- MySQL ---"
    remote_exec "docker logs --since 120s --tail 10 novelbridge-mysql 2>/dev/null || echo '(容器未运行)'"
    echo ""
    echo "--- Neo4j ---"
    remote_exec "docker logs --since 120s --tail 10 novelbridge-neo4j 2>/dev/null || echo '(容器未运行)'"
    echo ""
    echo "--- Qdrant ---"
    remote_exec "docker logs --since 120s --tail 10 novelbridge-qdrant 2>/dev/null || echo '(容器未运行)'"
}

# ---- SSH 连接 ----
ssh_connect() {
    echo -e "${CYAN}连接到 ${REMOTE_USER}@${REMOTE_HOST} ...${NC}"
    $SSH_CMD
}

# ============================================================
# 主入口
# ============================================================
main() {
    local cmd="${1:-start}"
    cmd="${cmd#--}"

    case "$cmd" in
        start)
            info "验证 SSH 连接 ${REMOTE_USER}@${REMOTE_HOST}..."
            remote_exec "echo OK" || {
                err "SSH 连接失败，检查 NB_REMOTE_HOST/NB_REMOTE_USER"
                exit 1
            }
            start_docker
            start_models
            echo ""
            check_status
            echo ""
            info "全部远端服务启动完成！"
            info "本地开 tunnel:"
            echo "  ssh -N -L ${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT} \\"
            echo "         -L ${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT} \\"
            echo "         -L ${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT} \\"
            echo "         -L ${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT} \\"
            echo "         -L ${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT} \\"
            echo "         -L ${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT} \\"
            echo "         ${REMOTE_USER}@${REMOTE_HOST}"
            echo ""
            info "然后在本地跑 rag-agent:"
            echo "  cd novelbridge/apps/rag-agent"
            echo "  python -m uvicorn app.main:app --host 127.0.0.1 --port 18081"
            ;;
        stop)
            stop_all
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        restart)
            stop_all
            sleep 2
            main start
            ;;
        ssh)
            ssh_connect
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
