# Start NovelBridge SSH tunnel on Windows.
#
# Usage:
#   .\scripts\remote\nb_tunnel_up.ps1
#   .\scripts\remote\nb_tunnel_up.ps1 -User wk -RemoteHost 192.168.3.50

param(
    [string]$User = "wk",
    [string]$RemoteHost = "192.168.3.50",
    [string]$PortFile = "$PSScriptRoot\..\..\deploy\remote\ports.env"
)

$ports = @{}
if (Test-Path -LiteralPath $PortFile) {
    Get-Content -LiteralPath $PortFile | ForEach-Object {
        if ($_ -match '^([A-Z0-9_]+)=(\d+)$') {
            $ports[$matches[1]] = $matches[2]
        }
    }
}

$MYSQL_PORT = if ($ports.ContainsKey('MYSQL_PORT')) { $ports['MYSQL_PORT'] } else { '13306' }
$NEO4J_HTTP_PORT = if ($ports.ContainsKey('NEO4J_HTTP_PORT')) { $ports['NEO4J_HTTP_PORT'] } else { '17474' }
$NEO4J_BOLT_PORT = if ($ports.ContainsKey('NEO4J_BOLT_PORT')) { $ports['NEO4J_BOLT_PORT'] } else { '17687' }
$QDRANT_PORT = if ($ports.ContainsKey('QDRANT_PORT')) { $ports['QDRANT_PORT'] } else { '16333' }
$LLAMA_PORT = if ($ports.ContainsKey('LLAMA_PORT')) { $ports['LLAMA_PORT'] } else { '18080' }
$EMBEDDING_PORT = if ($ports.ContainsKey('EMBEDDING_PORT')) { $ports['EMBEDDING_PORT'] } else { '18082' }
$RAG_AGENT_PORT = if ($ports.ContainsKey('RAG_AGENT_PORT')) { $ports['RAG_AGENT_PORT'] } else { '18081' }

$forwardings = @(
    "-L", "127.0.0.1:${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT}",
    "-L", "127.0.0.1:${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT}",
    "-L", "127.0.0.1:${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT}",
    "-L", "127.0.0.1:${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT}",
    "-L", "127.0.0.1:${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT}",
    "-L", "127.0.0.1:${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT}",
    "-L", "127.0.0.1:${RAG_AGENT_PORT}:127.0.0.1:${RAG_AGENT_PORT}"
)

$sshArgs = @(
    "-N",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=60"
) + $forwardings + @("${User}@${RemoteHost}")

Write-Host "[INFO] Starting SSH tunnel to ${User}@${RemoteHost}"
Write-Host "[INFO] Port mappings:"
Write-Host "  localhost:${MYSQL_PORT}      -> remote:${MYSQL_PORT}     (MySQL)"
Write-Host "  localhost:${NEO4J_HTTP_PORT}  -> remote:${NEO4J_HTTP_PORT} (Neo4j HTTP)"
Write-Host "  localhost:${NEO4J_BOLT_PORT}  -> remote:${NEO4J_BOLT_PORT} (Neo4j Bolt)"
Write-Host "  localhost:${QDRANT_PORT}      -> remote:${QDRANT_PORT}     (Qdrant)"
Write-Host "  localhost:${LLAMA_PORT}       -> remote:${LLAMA_PORT}      (llama-server)"
Write-Host "  localhost:${EMBEDDING_PORT}   -> remote:${EMBEDDING_PORT}  (embedding llama-server)"
Write-Host "  localhost:${RAG_AGENT_PORT}   -> remote:${RAG_AGENT_PORT}  (rag-agent)"

$proc = Start-Process -WindowStyle Hidden -FilePath "ssh" -ArgumentList $sshArgs -PassThru
Write-Host "[INFO] SSH tunnel started in background. PID=$($proc.Id)"
