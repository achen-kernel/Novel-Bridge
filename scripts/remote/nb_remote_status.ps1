<#
.SYNOPSIS
  NovelBridge — 远程服务状态（Windows → SSH → nb_status.sh）
#>

$ErrorActionPreference = "Stop"

$remoteHost = if ($env:NB_REMOTE_HOST) { $env:NB_REMOTE_HOST } else { "192.168.3.50" }
$remotePort = if ($env:NB_REMOTE_PORT) { $env:NB_REMOTE_PORT } else { "22" }
$remoteUser = if ($env:NB_REMOTE_USER) { $env:NB_REMOTE_USER } else { "wk" }
$sshKey = $env:NB_SSH_KEY
$deployDir = if ($env:NB_REMOTE_DEPLOY_DIR) { $env:NB_REMOTE_DEPLOY_DIR } else { "~/novelbridge-deploy" }

$sshArgs = @("-p", $remotePort, "-o", "ConnectTimeout=10")
if ($sshKey) { $sshArgs += "-i", $sshKey }
$sshDest = "$remoteUser@$remoteHost"

ssh @sshArgs $sshDest "cd $deployDir/deploy/remote && bash nb_status.sh" 2>&1

if ($LASTEXITCODE -ne 0) {
  Write-Host "（远程状态查询完成）" -ForegroundColor Gray
}
