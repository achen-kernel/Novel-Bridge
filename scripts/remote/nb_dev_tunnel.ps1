# NovelBridge local-dev SSH tunnel.
# Runs Python rag-agent locally while MySQL/Qdrant/Neo4j/llama-server stay on the remote Linux host.
#
# Usage:
#   .\scripts\remote\nb_dev_tunnel.ps1
#   .\scripts\remote\nb_dev_tunnel.ps1 -User wk -RemoteHost 192.168.3.50 -IncludeRagAgent

param(
    [string]$User = "wk",
    [string]$RemoteHost = "192.168.3.50",
    [string]$PortFile = "$PSScriptRoot\..\..\deploy\remote\ports.env",
    [switch]$IncludeRagAgent,
    [string]$PidFile = "$PSScriptRoot\.nb_dev_tunnel.pid"
)

function Read-PortFile {
    param([string]$Path)
    $ports = @{}
    if (Test-Path -LiteralPath $Path) {
        Get-Content -LiteralPath $Path | ForEach-Object {
            if ($_ -match '^([A-Z0-9_]+)=(\d+)$') {
                $ports[$matches[1]] = $matches[2]
            }
        }
    }
    return $ports
}

function Port-OrDefault {
    param($Ports, [string]$Name, [string]$Default)
    if ($Ports.ContainsKey($Name)) { return $Ports[$Name] }
    return $Default
}

$ports = Read-PortFile -Path $PortFile
$MYSQL_PORT = Port-OrDefault $ports "MYSQL_PORT" "13306"
$NEO4J_HTTP_PORT = Port-OrDefault $ports "NEO4J_HTTP_PORT" "17474"
$NEO4J_BOLT_PORT = Port-OrDefault $ports "NEO4J_BOLT_PORT" "17687"
$LLAMA_PORT = Port-OrDefault $ports "LLAMA_PORT" "18080"
$EMBEDDING_PORT = Port-OrDefault $ports "EMBEDDING_PORT" "18082"
$QDRANT_PORT = Port-OrDefault $ports "QDRANT_PORT" "16333"
$RAG_AGENT_PORT = Port-OrDefault $ports "RAG_AGENT_PORT" "18081"

$forwardings = @(
    "-L", "127.0.0.1:${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT}",
    "-L", "127.0.0.1:${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT}",
    "-L", "127.0.0.1:${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT}",
    "-L", "127.0.0.1:${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT}",
    "-L", "127.0.0.1:${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT}",
    "-L", "127.0.0.1:${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT}"
)

if ($IncludeRagAgent) {
    $forwardings += @("-L", "127.0.0.1:${RAG_AGENT_PORT}:127.0.0.1:${RAG_AGENT_PORT}")
}

$sshArgs = @(
    "-N",
    "-T",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3"
) + $forwardings + @("${User}@${RemoteHost}")

Write-Host "[INFO] Starting NovelBridge local-dev tunnel to ${User}@${RemoteHost}"
Write-Host "[INFO] Forwarded services:"
Write-Host "  MySQL      localhost:${MYSQL_PORT} -> remote:${MYSQL_PORT}"
Write-Host "  Qdrant     localhost:${QDRANT_PORT} -> remote:${QDRANT_PORT}"
Write-Host "  Neo4j HTTP localhost:${NEO4J_HTTP_PORT} -> remote:${NEO4J_HTTP_PORT}"
Write-Host "  Neo4j Bolt localhost:${NEO4J_BOLT_PORT} -> remote:${NEO4J_BOLT_PORT}"
Write-Host "  llama      localhost:${LLAMA_PORT} -> remote:${LLAMA_PORT}"
Write-Host "  embedding  localhost:${EMBEDDING_PORT} -> remote:${EMBEDDING_PORT}"
if ($IncludeRagAgent) {
    Write-Host "  rag-agent  localhost:${RAG_AGENT_PORT} -> remote:${RAG_AGENT_PORT}"
}

$proc = Start-Process -WindowStyle Hidden -FilePath "ssh" -ArgumentList $sshArgs -PassThru
$proc.Id | Set-Content -LiteralPath $PidFile -Encoding ascii

Write-Host "[INFO] Tunnel started. PID=$($proc.Id)"
Write-Host "[INFO] PID file: $PidFile"
Write-Host "[INFO] Stop it with: Stop-Process -Id $($proc.Id)"
