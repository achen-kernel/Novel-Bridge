<#
.SYNOPSIS
  NovelBridge — 关闭 SSH tunnel
.DESCRIPTION
  终止之前由 nb_tunnel_up.ps1 启动的 SSH tunnel 进程。
#>

$ErrorActionPreference = "Stop"

$remoteHost = if ($env:NB_REMOTE_HOST) { $env:NB_REMOTE_HOST } else { "192.168.3.50" }

Write-Host "正在查找 SSH tunnel 进程..." -ForegroundColor Yellow

$tunnelProcesses = Get-Process -Name "ssh" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "$remoteHost" -and $_.CommandLine -match "-L" }

if (-not $tunnelProcesses) {
  Write-Host "未找到活跃的 SSH tunnel 进程" -ForegroundColor Yellow
  exit 0
}

foreach ($proc in $tunnelProcesses) {
  Write-Host "终止 SSH tunnel PID: $($proc.Id)" -ForegroundColor Yellow
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "SSH tunnel 已关闭" -ForegroundColor Green
