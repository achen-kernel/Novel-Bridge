# Poll remote Linux service logs for local NovelBridge development.
# This is for services that still run remotely while rag-agent runs locally.
#
# Usage:
#   .\scripts\remote\nb_remote_logs_watch.ps1
#   .\scripts\remote\nb_remote_logs_watch.ps1 -User wk -RemoteHost 192.168.3.50 -IntervalSec 120 -Lines 80

param(
    [string]$User = "wk",
    [string]$RemoteHost = "192.168.3.50",
    [int]$IntervalSec = 90,
    [int]$Lines = 80,
    [string]$RemoteRoot = "/home/wk/novelbridge"
)

if ($IntervalSec -lt 15) {
    throw "IntervalSec should be >= 15 to avoid noisy SSH polling."
}

$remoteScript = @'
set -u
ROOT="__REMOTE_ROOT__"
LINES="__LINES__"
SINCE="__SINCE__s"
LOG_DIR="$ROOT/logs"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') remote service logs ====="

echo
echo "----- llama-server file log -----"
if [ -f "$LOG_DIR/llama-server.log" ]; then
  tail -n "$LINES" "$LOG_DIR/llama-server.log"
else
  echo "missing: $LOG_DIR/llama-server.log"
  if command -v journalctl >/dev/null 2>&1; then
    journalctl --user -u llama-server.service -n "$LINES" --no-pager 2>/dev/null || true
  fi
fi

echo
echo "----- MySQL docker logs -----"
docker logs --since "$SINCE" --tail "$LINES" novelbridge-mysql 2>&1 || echo "cannot read novelbridge-mysql logs"

echo
echo "----- Neo4j docker logs -----"
docker logs --since "$SINCE" --tail "$LINES" novelbridge-neo4j 2>&1 || echo "cannot read novelbridge-neo4j logs"

echo
echo "----- Qdrant docker logs -----"
docker logs --since "$SINCE" --tail "$LINES" novelbridge-qdrant 2>&1 || echo "cannot read novelbridge-qdrant logs"
'@

$remoteScript = $remoteScript.Replace("__REMOTE_ROOT__", $RemoteRoot)
$remoteScript = $remoteScript.Replace("__LINES__", [string]$Lines)
$remoteScript = $remoteScript.Replace("__SINCE__", [string]($IntervalSec + 15))

Write-Host "[INFO] Polling remote logs from ${User}@${RemoteHost} every ${IntervalSec}s"
Write-Host "[INFO] Remote root: $RemoteRoot"
Write-Host "[INFO] Press Ctrl+C to stop."

while ($true) {
    Clear-Host
    $remoteScript | ssh "${User}@${RemoteHost}" "bash -s"
    Start-Sleep -Seconds $IntervalSec
}
