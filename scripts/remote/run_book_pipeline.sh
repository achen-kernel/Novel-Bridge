#!/usr/bin/env bash
# ============================================================
# NovelBridge 全流程 Pipeline 脚本 (远端)
# 从 Stage 2 → Stage 7，依次处理一本书
# 用法:
#   ./run_book_pipeline.sh <book_id> [book_id2 ...]
#   ./run_book_pipeline.sh 1
#   ./run_book_pipeline.sh 1 2 3
#   ./run_book_pipeline.sh 1 --from index
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
STATUS_DIR="${STATUS_DIR:-$LOG_DIR/status}"
API_BASE="http://127.0.0.1:18081"
PID_FILE="$LOG_DIR/.pipeline.pid"

mkdir -p "$LOG_DIR" "$STATUS_DIR"

# 时间戳
now() { date '+%Y-%m-%d %H:%M:%S'; }
ts()  { date '+%Y%m%d_%H%M%S'; }

# 彩色输出
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[$(now)]${NC} $1"; }
warn()  { echo -e "${YELLOW}[$(now)]${NC} $1"; }
err()   { echo -e "${RED}[$(now)] ERROR:${NC} $1"; }
step()  { echo -e "${CYAN}━━━ $1 ━━━${NC}"; }

# 写状态文件 (供监控脚本读取)
write_status() {
    local book_id=$1 stage=$2 status=$3 message=$4
    local status_file="$STATUS_DIR/book-${book_id}.json"
    cat > "$status_file" <<EOF
{
  "book_id": $book_id,
  "stage": "$stage",
  "status": "$status",
  "message": "$message",
  "timestamp": "$(now)"
}
EOF
}

# 调用 API 的通用函数
call_api() {
    local method=$1 url=$2 data=$3 desc=$4
    local stage_label=$5
    local book_id=$6
    info "→ $desc ..."

    local start_ts end_ts duration
    start_ts=$(date +%s)

    local http_code response
    response=$(curl -s -w "\n%{http_code}" -X "$method" \
        "$API_BASE$url" \
        -H "Content-Type: application/json" \
        -d "$data" 2>&1) || true

    local http_code_exit=$?
    end_ts=$(date +%s)
    duration=$((end_ts - start_ts))

    local body code
    body=$(echo "$response" | head -n -1)
    code=$(echo "$response" | tail -n1)

    if [ "$http_code_exit" -ne 0 ] || [ -z "$code" ] || [ "$code" -ge 500 ]; then
        err "$desc 失败 (HTTP $code, ${duration}s)"
        echo "$body"
        write_status "$book_id" "$stage_label" "FAILED" "HTTP $code, ${duration}s"
        return 1
    fi

    # 检查返回的 status 字段
    local status
    status=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [ "$status" = "error" ]; then
        local err_msg
        err_msg=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error','unknown'))" 2>/dev/null || echo "unknown")
        err "$desc 返回 error (${duration}s): $err_msg"
        write_status "$book_id" "$stage_label" "FAILED" "$err_msg (${duration}s)"
        return 1
    fi

    info "✓ $desc 完成 (${duration}s)"
    echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d,ensure_ascii=False,indent=2))" 2>/dev/null || echo "$body"

    # 提取关键数字用于日志
    local detail
    detail=$(echo "$body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
keys = ['chapters','chunks','success_count','mentions','profiles','decisions',
        'chunks_indexed','facts_indexed','relation_mentions','event_mentions',
        'stages','entities','relations','events','total','passed','failed']
parts = []
for k in keys:
    if k in d:
        parts.append(f'{k}={d[k]}')
print(', '.join(parts))
" 2>/dev/null || echo "")
    if [ -n "$detail" ]; then
        info "  ├ $detail"
    fi

    write_status "$book_id" "$stage_label" "OK" "completed in ${duration}s"
    return 0
}

# ============================================================
# 单本书 Pipeline
# ============================================================
run_book_pipeline() {
    local book_id=$1
    local start_stage="${2:-process}"
    local log_file="$LOG_DIR/book-${book_id}-pipeline.log"
    local pipeline_start pipeline_end total_duration

    pipeline_start=$(date +%s)
    write_status "$book_id" "init" "RUNNING" "Pipeline started"

    # 输出到终端 + 日志文件
    exec 3>&1
    {
        info "=========================================="
        info "开始处理 Book ID: $book_id"
        info "Pipeline 日志: $log_file"
        info "=========================================="

        echo "===== Pipeline Start: book_id=$book_id at $(now) ====="

        # 标记跳过的阶段
        skip_before=true

        # ---- Stage 1: Prior Hint (DeepSeek 梗概) ----
        # 默认总是先跑 prior-hint，除非从 extract 及之后开始
        # （extract、govern、index、narrative、plot-stages、graph、eval、export）
        local skip_prior=false
        case "$start_stage" in
            extract|govern|index|narrative|plot-stages|graph|eval|export)
                skip_prior=true ;;
        esac

        if ! $skip_prior; then
            skip_before=false
            step "[Stage 1/10] DeepSeek 小说梗概 (Prior Hint)"
            call_api POST "/api/books/${book_id}/prior-hint" '{}' \
                "获取 Prior Hint" "prior-hint" "$book_id" || return 1
        else
            warn "→ 跳过 prior-hint (start_stage=$start_stage)"
        fi

        # ---- Stage 2: 拆章 + Chunking ----
        if [[ "$start_stage" == "process" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 2/10] 拆章 + Chunking"
            call_api POST "/api/books/${book_id}/process" '{}' \
                "拆章并构建 Chunks" "process" "$book_id" || { write_status "$book_id" "process" "FAILED" "pipeline aborted"; return 1; }
        elif [[ "$start_stage" == "process" ]]; then
            skip_before=false
            step "[Stage 2/10] 拆章 + Chunking"
            call_api POST "/api/books/${book_id}/process" '{}' \
                "拆章并构建 Chunks" "process" "$book_id" || { write_status "$book_id" "process" "FAILED" "pipeline aborted"; return 1; }
        else
            warn "→ 跳过 process (start_stage=$start_stage)"
        fi

        # ---- Stage 3: ChapterFact 提取 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "extract" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 3/10] ChapterFact 提取"
            call_api POST "/api/books/${book_id}/extract" '{"use_model": true}' \
                "提取 ChapterFact" "extract" "$book_id" || return 1
        elif [[ "$start_stage" == "extract" ]]; then
            skip_before=false
            step "[Stage 3/10] ChapterFact 提取"
            call_api POST "/api/books/${book_id}/extract" '{"use_model": true}' \
                "提取 ChapterFact" "extract" "$book_id" || return 1
        else
            warn "→ 跳过 extract (start_stage=$start_stage)"
        fi

        # ---- Stage 4: 实体治理 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "govern" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 4/10] 实体治理"
            call_api POST "/api/books/${book_id}/govern" '{}' \
                "实体治理" "govern" "$book_id" || return 1
        elif [[ "$start_stage" == "govern" ]]; then
            skip_before=false
            step "[Stage 4/10] 实体治理"
            call_api POST "/api/books/${book_id}/govern" '{}' \
                "实体治理" "govern" "$book_id" || return 1
        else
            warn "→ 跳过 govern (start_stage=$start_stage)"
        fi

        # ---- Stage 5: 向量索引 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "index" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 5/10] 向量索引 (Qdrant)"
            call_api POST "/api/books/${book_id}/index" '{"reindex": true}' \
                "索引到 Qdrant" "index" "$book_id" || return 1
        elif [[ "$start_stage" == "index" ]]; then
            skip_before=false
            step "[Stage 5/10] 向量索引 (Qdrant)"
            call_api POST "/api/books/${book_id}/index" '{"reindex": true}' \
                "索引到 Qdrant" "index" "$book_id" || return 1
        else
            warn "→ 跳过 index (start_stage=$start_stage)"
        fi

        # ---- Stage 6: 叙事构建 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "narrative" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 6/10] 叙事构建 (关系+事件)"
            call_api POST "/api/books/${book_id}/narrative" '{}' \
                "构建叙事" "narrative" "$book_id" || return 1
        elif [[ "$start_stage" == "narrative" ]]; then
            skip_before=false
            step "[Stage 6/10] 叙事构建 (关系+事件)"
            call_api POST "/api/books/${book_id}/narrative" '{}' \
                "构建叙事" "narrative" "$book_id" || return 1
        else
            warn "→ 跳过 narrative (start_stage=$start_stage)"
        fi

        # ---- Stage 7: 情节检测 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "plot-stages" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 7/10] 情节检测"
            call_api POST "/api/books/${book_id}/plot-stages/detect" '{}' \
                "检测情节阶段" "plot-stages" "$book_id" || return 1
        elif [[ "$start_stage" == "plot-stages" ]]; then
            skip_before=false
            step "[Stage 7/10] 情节检测"
            call_api POST "/api/books/${book_id}/plot-stages/detect" '{}' \
                "检测情节阶段" "plot-stages" "$book_id" || return 1
        else
            warn "→ 跳过 plot-stages (start_stage=$start_stage)"
        fi

        # ---- Stage 8: 图投影到 Neo4j ----
        if [[ "$start_stage" == "process" || "$start_stage" == "graph" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 8/10] 图投影到 Neo4j"
            call_api POST "/api/books/${book_id}/graph/project" '{}' \
                "投影到 Neo4j" "graph" "$book_id" || return 1
        elif [[ "$start_stage" == "graph" ]]; then
            skip_before=false
            step "[Stage 8/10] 图投影到 Neo4j"
            call_api POST "/api/books/${book_id}/graph/project" '{}' \
                "投影到 Neo4j" "graph" "$book_id" || return 1
        else
            warn "→ 跳过 graph (start_stage=$start_stage)"
        fi

        # ---- Stage 9: 评估 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "eval" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 9/10] 运行评估"
            call_api POST "/api/eval/run?book_id=${book_id}" '' \
                "运行 Eval" "eval" "$book_id" || return 1
        elif [[ "$start_stage" == "eval" ]]; then
            skip_before=false
            step "[Stage 9/10] 运行评估"
            call_api POST "/api/eval/run?book_id=${book_id}" '' \
                "运行 Eval" "eval" "$book_id" || return 1
        else
            warn "→ 跳过 eval (start_stage=$start_stage)"
        fi

        # ---- Stage 10: 导出 ----
        if [[ "$start_stage" == "process" || "$start_stage" == "export" || "$start_stage" == "all" ]] && ! $skip_before; then
            step "[Stage 10/10] 导出训练数据"
            call_api POST "/api/eval/export/chapter-facts?book_id=${book_id}&min_review=ACCEPTED" '' \
                "导出 ChapterFacts" "export-facts" "$book_id" || warn "导出 chapter-facts 失败（可能无 ACCEPTED 数据）"
            call_api POST "/api/eval/export/qa-pairs?book_id=${book_id}" '' \
                "导出 QA Pairs" "export-qa" "$book_id" || warn "导出 qa-pairs 失败"
        elif [[ "$start_stage" == "export" ]]; then
            step "[Stage 10/10] 导出训练数据"
            call_api POST "/api/eval/export/chapter-facts?book_id=${book_id}&min_review=ACCEPTED" '' \
                "导出 ChapterFacts" "export-facts" "$book_id" || true
            call_api POST "/api/eval/export/qa-pairs?book_id=${book_id}" '' \
                "导出 QA Pairs" "export-qa" "$book_id" || true
        fi

        pipeline_end=$(date +%s)
        total_duration=$((pipeline_end - pipeline_start))
        local min=$((total_duration / 60))
        local sec=$((total_duration % 60))

        echo ""
        info "=========================================="
        info "✅ Book ID $book_id 全部流程完成！"
        info "   总耗时: ${min}m ${sec}s"
        info "   日志: $log_file"
        info "=========================================="
        echo "===== Pipeline Complete: book_id=$book_id at $(now), duration=${total_duration}s ====="

        write_status "$book_id" "done" "COMPLETED" "pipeline finished in ${min}m${sec}s"

    } 2>&1 | tee -a "$log_file" >&3

    return 0
}

# ============================================================
# 批量处理
# ============================================================
batch_run() {
    local book_ids=("$@")
    local start_stage="${book_ids[-1]}"
    # 如果最后一个参数是阶段名，弹出
    case "$start_stage" in
        process|prior-hint|extract|govern|index|narrative|plot-stages|graph|eval|export|all)
            unset 'book_ids[${#book_ids[@]}-1]'
            ;;
        *)
            start_stage="process"
            ;;
    esac

    # 并行处理？默认串行（书之间有顺序依赖？没有，可以并行）
    # 但为避免资源争用，串行处理
    for bid in "${book_ids[@]}"; do
        run_book_pipeline "$bid" "$start_stage"
        echo ""
    done
}

# ============================================================
# 主入口
# ============================================================
main() {
    if [ $# -lt 1 ]; then
        echo "用法: $0 <book_id> [book_id2 ...] [选项]"
        echo ""
        echo "参数:"
        echo "  book_id              书籍 ID (支持多个)"
        echo ""
        echo "选项:"
        echo "  --from <stage>       从指定阶段开始 (默认: process)"
        echo "  --parallel           并行处理多本书"
        echo "  --list-books         列出数据库中已上传的书籍"
        echo ""
        echo "阶段列表 (按顺序):"
        echo "  process      Stage 2: 拆章 + Chunking"
        echo "  prior-hint   Stage 3: DeepSeek 小说梗概"
        echo "  extract      Stage 4: ChapterFact 提取"
        echo "  govern       Stage 5: 实体治理"
        echo "  index        Stage 6: 向量索引到 Qdrant"
        echo "  narrative    Stage 7: 叙事构建"
        echo "  plot-stages  Stage 8: 情节检测"
        echo "  graph        Stage 9: 图投影到 Neo4j"
        echo "  eval         Stage 10: 运行评估"
        echo "  export       Stage 10: 导出训练数据"
        echo "  all          从当前阶段执行到 export"
        echo ""
        echo "示例:"
        echo "  $0 1                   处理书籍 1 完整流程"
        echo "  $0 1 2 3              依次处理书籍 1,2,3"
        echo "  $0 1 --from index     从索引阶段开始"
        echo "  $0 --list-books       查看已上传书籍"
        exit 1
    fi

    # 特例：列出书籍
    if [ "$1" = "--list-books" ]; then
        step "已上传到 MySQL 的书籍"
        docker exec -i novelbridge-mysql mysql -u"${MYSQL_USER:-novel_bridge}" -p"${MYSQL_PASSWORD}" -e "
            SELECT id, title, author, status, chapter_count, chunk_count, created_at
            FROM novel_bridge.novel_book ORDER BY id;
        " 2>/dev/null || err "无法查询书籍列表"
        exit 0
    fi

    local book_ids=()
    local start_stage="all"
    local parallel=false

    # 解析参数
    while [ $# -gt 0 ]; do
        case "$1" in
            --from)
                shift; start_stage="$1"; shift ;;
            --parallel)
                parallel=true; shift ;;
            *)
                book_ids+=("$1"); shift ;;
        esac
    done

    # 检查服务
    info "检查 rag-agent 服务 ($API_BASE/health)..."
    local health_check
    health_check=$(curl -sf "$API_BASE/health" 2>/dev/null || echo "")
    if [ -z "$health_check" ]; then
        err "rag-agent 不可用，请先启动服务"
        exit 1
    fi
    info "✅ rag-agent 服务就绪"

    # 记录启动到 PID 文件
    echo "$$" > "$PID_FILE"
    info "Pipeline PID: $$"

    if [ "$parallel" = true ] && [ ${#book_ids[@]} -gt 1 ]; then
        warn "并行模式: 同时处理 ${book_ids[*]}"
        local pids=()
        for bid in "${book_ids[@]}"; do
            (run_book_pipeline "$bid" "$start_stage") &
            pids+=($!)
        done
        # 等待所有完成
        for pid in "${pids[@]}"; do
            wait "$pid" || true
        done
        info "所有并行任务完成"
    else
        for bid in "${book_ids[@]}"; do
            run_book_pipeline "$bid" "$start_stage"
            echo ""
        done
    fi

    rm -f "$PID_FILE"
    info "全部处理完成！"
}

main "$@"
