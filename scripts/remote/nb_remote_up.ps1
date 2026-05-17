<#
.SYNOPSIS
  NovelBridge — 远程启动服务（Windows → SSH → nb_up.sh）
.DESCRIPTION
  通过 SSH 在远程 Linux 服务器上执行 nb_up.sh。
  环境变量:
    NB_REMOTE_HOST  (默认: 192.168.3.50)
    NB_REMOTE_PORT  (默认: 22)
    NB_REMOTE_USER  (默认: wk)
    NB_SSH_KEY      (可选，私钥路径)
    NB_REMOTE_DEPLOY_DIR (默认: ~/novelbridge-deploy)
.NOTES
  密码不要写在环境变量或脚本中。
  推荐使用 SSH key 认证。
  如使用密码，PowerShell 会弹出凭据提示。
#>

$ErrorActionPreference = "Stop"

# ---- 配置 ----
$remoteHost = $env:NB_REMOTE_HOST
$remotePort = $env:NB_REMOTE_PORT
$remoteUser = $env:NB_REMOTE_USER
$sshKey = $env:NB_SSH_KEY
$deployDir = $env:NB_REMOTE_DEPLOY_DIR

if (-not $remoteHost) { $remoteHost = "192.168.3.50" }
if (-not $remotePort) { $remotePort = "22" }
if (-not $remoteUser) { $remoteUser = "wk" }
if (-not $deployDir) { $deployDir = "~/novelbridge-deploy" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NovelBridge — 远程启动服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  目标: $remoteUser@$remoteHost`:$remotePort"
Write-Host "  目录: $deployDir"
Write-Host ""

# ---- SSH 参数 ----
$sshArgs = @(
  "-p", $remotePort,
  "-o", "StrictHostKeyChecking=accept-new",
  "-o", "ConnectTimeout=10"
)
if ($sshKey) {
  $sshArgs += "-i", $sshKey
}

$sshDest = "$remoteUser@$remoteHost"

# ---- 检查连接 ----
Write-Host "正在检查 SSH 连接..." -ForegroundColor Yellow
$checkCmd = "ssh @sshArgs -q $sshDest exit 2>&1"
$checkResult = ssh @sshArgs -q $sshDest exit 2>&1

if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: SSH 连接失败，请检查:" -ForegroundColor Red
  Write-Host "  1. 目标主机是否可达: ping $remoteHost"
  Write-Host "  2. SSH 端口是否正确: $remotePort"
  Write-Host "  3. 用户名/密钥是否正确"
  Write-Host "  4. 主机密钥是否已接受"
  exit 1
}

Write-Host "SSH 连接成功" -ForegroundColor Green
Write-Host ""

# ---- 确保远程目录存在 ----
Write-Host "确保远程部署目录存在..." -ForegroundColor Yellow
ssh @sshArgs $sshDest "mkdir -p $deployDir/deploy/remote $deployDir/logs" 2>&1

# ---- 同步部署脚本到远程 ----
Write-Host "同步 deploy/remote 脚本到远程..." -ForegroundColor Yellow
$localDeployPath = Join-Path (Get-Location) "deploy/remote"
if (Test-Path $localDeployPath) {
  scp -P $remotePort @(if($sshKey){@("-i",$sshKey)}else{@()}) `
    -r "$localDeployPath/*" `
    "$remoteUser@$remoteHost`:$deployDir/deploy/remote/" 2>&1 | Out-Null
  Write-Host "同步完成" -ForegroundColor Green
} else {
  Write-Host "WARNING: 本地 deploy/remote 目录不存在，跳过同步" -ForegroundColor Yellow
}

# ---- 执行远程脚本 ----
Write-Host "在远程服务器上执行 nb_up.sh ..." -ForegroundColor Yellow
Write-Host "（这可能需要几分钟）" -ForegroundColor Gray
Write-Host ""

ssh @sshArgs $sshDest "cd $deployDir/deploy/remote && bash nb_up.sh" 2>&1

if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "远程服务启动完成" -ForegroundColor Green
  Write-Host "rag-agent 端点: http://$remoteHost`:18081"
} else {
  Write-Host ""
  Write-Host "远程服务启动失败（退出码: $LASTEXITCODE）" -ForegroundColor Red
  Write-Host "请检查远程服务器日志: $deployDir/logs/"
  exit 1
}
