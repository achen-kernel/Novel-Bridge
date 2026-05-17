<#
.SYNOPSIS
  NovelBridge -- SSH tunnel to remote internal services
.DESCRIPTION
  Forward remote Linux internal ports to localhost via SSH.
  Use this for local dev access to MySQL / Neo4j / llama-server.

  Then run Spring Boot with profile=dev:
    $env:SPRING_PROFILES_ACTIVE="dev"
    cd Novel-Bridge && mvn spring-boot:run

  Mappings:
    local:13306  -> remote:13306  (MySQL)
    local:17474  -> remote:17474  (Neo4j HTTP)
    local:17687  -> remote:17687  (Neo4j Bolt)
    local:18080  -> remote:18080  (llama-server)
#>

$ErrorActionPreference = "Stop"

$remoteHost = if ($env:NB_REMOTE_HOST) { $env:NB_REMOTE_HOST } else { "192.168.3.50" }
$remotePort = if ($env:NB_REMOTE_PORT) { $env:NB_REMOTE_PORT } else { "22" }
$remoteUser = if ($env:NB_REMOTE_USER) { $env:NB_REMOTE_USER } else { "wk" }
$sshKey = $env:NB_SSH_KEY

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NovelBridge -- SSH Tunnel (start)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Target: $remoteUser@$remoteHost`:$remotePort"
Write-Host ""

# ---- Check existing tunnel ----
$existingTunnel = Get-Process -Name "ssh" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "$remoteHost.*13306" }

if ($existingTunnel) {
  Write-Host "SSH tunnel already running (PID: $($existingTunnel.Id))" -ForegroundColor Yellow
  Write-Host "Restart: run nb_tunnel_down.ps1 first" -ForegroundColor Yellow
  exit 0
}

# ---- Build SSH tunnel command ----
$sshArgs = @(
  "-p", $remotePort
  "-o", "StrictHostKeyChecking=accept-new"
  "-o", "ConnectTimeout=10"
  "-o", "ExitOnForwardFailure=yes"
  "-N"
  "-L", "13306:127.0.0.1:13306"
  "-L", "17474:127.0.0.1:17474"
  "-L", "17687:127.0.0.1:17687"
  "-L", "18080:127.0.0.1:18080"
  "-L", "18081:127.0.0.1:18081"
)
if ($sshKey) { $sshArgs += "-i", $sshKey }
$sshArgs += "$remoteUser@$remoteHost"

Write-Host "Establishing SSH tunnel (background)..." -ForegroundColor Yellow

$process = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2

if ($process.HasExited) {
  if ($process.ExitCode -ne 0) {
    Write-Host "ERROR: SSH tunnel failed (exit code: $($process.ExitCode))" -ForegroundColor Red
    Write-Host "Check:" -ForegroundColor Red
    Write-Host "  1. Remote SSH service is running"
    Write-Host "  2. SSH key is set up (or use password)"
    Write-Host "  3. Remote ports are listening"
    exit 1
  }
}

Write-Host "SSH tunnel established" -ForegroundColor Green
Write-Host ""
Write-Host "Local mappings:"
Write-Host "  localhost:13306  ->  remote MySQL"
Write-Host "  localhost:17474  ->  remote Neo4j HTTP"
Write-Host "  localhost:17687  ->  remote Neo4j Bolt"
Write-Host "  localhost:18080  ->  remote llama-server"
Write-Host "  localhost:18081  ->  remote rag-agent"
Write-Host ""
Write-Host "To stop: .\scripts\remote\nb_tunnel_down.ps1" -ForegroundColor Yellow
Write-Host "To use: `$env:SPRING_PROFILES_ACTIVE=`"dev`"" -ForegroundColor Yellow
