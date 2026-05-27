# Start Python rag-agent for local development.
#
# Usage:
#   .\scripts\local\start_rag_agent.ps1
#   .\scripts\local\start_rag_agent.ps1 -Port 18081

param(
    [int]$Port = 18081,
    [string]$HostName = "127.0.0.1"
)

$repoRoot = Resolve-Path -LiteralPath "$PSScriptRoot\..\.."
$ragRoot = Join-Path $repoRoot "apps\rag-agent"
$python = Join-Path $ragRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing Python venv: $python. Create it under apps\rag-agent and install requirements.txt first."
}

Push-Location $ragRoot
try {
    & $python -m uvicorn app.main:app --reload --host $HostName --port $Port
}
finally {
    Pop-Location
}
