<#
.SYNOPSIS
  NovelBridge — 远程停止服务（Windows → SSH → nb_down.sh）
#>

$ErrorActionPreference = "Stop"

$remoteHost = if ($env:NB_REMOTE_HOST) { $env:NB_REMOTE_HOST } else { "192.168.3.50" }
$remotePort = if ($env:NB_REMOTE_PORT) { $env:NB_REMOTE_PORT } else { "22" }
$remoteUser = if ($env:NB_REMOTE_USER) { $env:NB_REMOTE_USER } else { "wk" }
$sshKey = $env:NB_SSH_KEY
$deployDir = if ($env:NB_REMOTE_DEPLOY_DIR) { $env:NB_REMOTE_DEPLOY_DIR } else { "~/novelbridge-deploy" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NovelBridge — 远程停止服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$sshArgs = @("-p", $remotePort, "-o", "ConnectTimeout=10")
if ($sshKey) { $sshArgs += "-i", $sshKey }
$sshDest = "$remoteUser@$remoteHost"

ssh @sshArgs $sshDest "cd $deployDir/deploy/remote && bash nb_down.sh" 2>&1

if ($LASTEXITCODE -eq 0) {
  Write-Host "远程服务已停止" -ForegroundColor Green
} else {
  Write-Host "远程服务停止完成（可能部分服务未运行）" -ForegroundColor Yellow
}
