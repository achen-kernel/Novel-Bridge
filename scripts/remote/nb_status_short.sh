#!/usr/bin/env bash
# ============================================================
# NovelBridge — 快速状态检查：agent_run / chapters / candidates
# ============================================================
MYSQL_CMD="docker exec novelbridge-mysql mysql -u root -p12345678 novel_bridge"

echo "=== agent_run ==="
$MYSQL_CMD -e "SELECT id,run_type,status,started_at,error_message FROM novel_agent_run ORDER BY id DESC LIMIT 5;" 2>/dev/null

echo "=== chapters ==="
$MYSQL_CMD -e "SELECT COUNT(*) as cnt FROM novel_chapter;" 2>/dev/null

echo "=== chunks ==="
$MYSQL_CMD -e "SELECT COUNT(*) as cnt FROM novel_chunk;" 2>/dev/null

echo "=== model_run (last 5) ==="
$MYSQL_CMD -e "SELECT id,status,duration_ms,parse_status,error_message FROM novel_model_run ORDER BY id DESC LIMIT 5;" 2>/dev/null

echo "=== candidates ==="
$MYSQL_CMD -e "SELECT COUNT(*) as cnt,status FROM novel_entity_candidate GROUP BY status;" 2>/dev/null

echo "=== llama-server ==="
curl -s --max-time 3 http://127.0.0.1:18080/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Model: {d[\"data\"][0][\"id\"][:50]}')" 2>/dev/null || echo "llama-server: DOWN"
