# NovelBridge 一键本地开发启动脚本（conda activate svm）
# 本地只做数据处理和中转，不跑模型和服务。
# 远端负责：MySQL / Neo4j / Qdrant / llama-server / embedding
#
# 1. 开 SSH tunnel 到远端（后台）
# 2. 启动本地 rag-agent
#
# 用法: .\scripts\local\start_dev.ps1
#       .\scripts\local\start_dev.ps1 -Port 18081
#       .\scripts\local\start_dev.ps1 -NoAgent (只开 tunnel，不启动 rag-agent)

param(
    [int]$Port = 18081,
    [string]$RemoteHost = "192.168.3.50",
    [string]$RemoteUser = "wk",
    [switch]$NoAgent
)

# 确保在 svm conda 环境（当前 python 应指向 C:\Anaconda\envs\svm\python.exe）
$envPy = (Get-Command python).Source
if ($envPy -notmatch 'svm') {
    Write-Host "⚠ 当前 Python 不在 svm 环境: $envPy" -ForegroundColor Yellow
    Write-Host "  运行: conda activate svm" -ForegroundColor Yellow
}

$repoRoot = Resolve-Path -LiteralPath "$PSScriptRoot\..\.."
$ragRoot = Join-Path $repoRoot "apps\rag-agent"

# 端口定义
$MYSQL_PORT = 13306
$NEO4J_HTTP_PORT = 17474
$NEO4J_BOLT_PORT = 17687
$QDRANT_PORT = 16333
$LLAMA_PORT = 18080
$EMBEDDING_PORT = 18082

# 检查远端连通性
Write-Host "[1/4] 检查远端连通性 ${RemoteUser}@${RemoteHost}..." -ForegroundColor Cyan
try {
    $null = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${RemoteUser}@${RemoteHost} "echo OK" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "SSH 连接失败" }
    Write-Host "  ✅ SSH 连接成功" -ForegroundColor Green
} catch {
    Write-Host "  ❌ SSH 连接失败: $_" -ForegroundColor Red
    Write-Host "  请确认远端服务器 ${RemoteHost} 已开机并可通过 SSH 访问" -ForegroundColor Yellow
    exit 1
}

# 启动 SSH tunnel（后台）
Write-Host "[2/4] 启动 SSH tunnel（后台）..." -ForegroundColor Cyan

# 先杀旧 tunnel
$oldTunnel = Get-Process -Name ssh -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "13306.*${RemoteHost}" }
if ($oldTunnel) {
    Write-Host "  ⚠ 发现旧 tunnel 进程 PID=$($oldTunnel.Id)，正在关闭..." -ForegroundColor Yellow
    $oldTunnel | Stop-Process -Force
    Start-Sleep -Seconds 2
}

$tunnelArgs = @(
    "-N"
    "-o", "ExitOnForwardFailure=yes"
    "-o", "ServerAliveInterval=60"
    "-L", "127.0.0.1:${MYSQL_PORT}:127.0.0.1:${MYSQL_PORT}"
    "-L", "127.0.0.1:${NEO4J_HTTP_PORT}:127.0.0.1:${NEO4J_HTTP_PORT}"
    "-L", "127.0.0.1:${NEO4J_BOLT_PORT}:127.0.0.1:${NEO4J_BOLT_PORT}"
    "-L", "127.0.0.1:${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT}"
    "-L", "127.0.0.1:${LLAMA_PORT}:127.0.0.1:${LLAMA_PORT}"
    "-L", "127.0.0.1:${EMBEDDING_PORT}:127.0.0.1:${EMBEDDING_PORT}"
    "${RemoteUser}@${RemoteHost}"
)

$tunnel = Start-Process -WindowStyle Hidden -FilePath "ssh" -ArgumentList $tunnelArgs -PassThru
Start-Sleep -Seconds 3

# 验证 tunnel
Write-Host "  Tunnel PID: $($tunnel.Id)" -ForegroundColor Gray
try {
    $test = ssh -o ConnectTimeout=3 -p $MYSQL_PORT -o "ProxyJump=none" 127.0.0.1 -l test "exit" 2>&1
    # 换个方式验证：检查端口是否在监听
    $portCheck = netstat -ano | Select-String "127.0.0.1:${MYSQL_PORT}"
    if ($portCheck) {
        Write-Host "  ✅ Tunnel 已就绪（端口转发正常）" -ForegroundColor Green
    } else {
        throw "端口未监听"
    }
} catch {
    Write-Host "  ⚠ Tunnel 验证异常: $_" -ForegroundColor Yellow
    Write-Host "  尝试继续..." -ForegroundColor Gray
}

# 在前台启动 rag-agent
Write-Host "[3/4] 启动本地 rag-agent (127.0.0.1:${Port})..." -ForegroundColor Cyan
Write-Host ""
Write-Host "========== 服务映射 ==========" -ForegroundColor Cyan
Write-Host "  MySQL:       127.0.0.1:${MYSQL_PORT}  → 远端"
Write-Host "  Neo4j HTTP:  127.0.0.1:${NEO4J_HTTP_PORT}  → 远端"
Write-Host "  Neo4j Bolt:  127.0.0.1:${NEO4J_BOLT_PORT}  → 远端"
Write-Host "  Qdrant:      127.0.0.1:${QDRANT_PORT}  → 远端"
Write-Host "  llama:       127.0.0.1:${LLAMA_PORT}  → 远端"
Write-Host "  embedding:   127.0.0.1:${EMBEDDING_PORT}  → 远端"
Write-Host "  rag-agent:   127.0.0.1:${Port}          ← 本地"
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止 rag-agent（tunnel 会继续在后台运行）" -ForegroundColor Yellow
Write-Host "如需同时停止 tunnel: Stop-Process -Id $($tunnel.Id)" -ForegroundColor Gray
Write-Host ""

if (-not $NoAgent) {
    Push-Location $ragRoot
    try {
        python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
    } finally {
        Pop-Location
    }
} else {
    Write-Host "Tunnel 已在后台运行 (PID: $($tunnel.Id))" -ForegroundColor Green
    Write-Host "在新终端启动 rag-agent:" -ForegroundColor Cyan
    Write-Host "  cd ${ragRoot}" -ForegroundColor White
    Write-Host "  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port ${Port}" -ForegroundColor White
}
