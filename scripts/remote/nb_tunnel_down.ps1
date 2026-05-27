# Stop NovelBridge SSH tunnels on Windows.
#
# Usage:
#   .\scripts\remote\nb_tunnel_down.ps1
#   .\scripts\remote\nb_tunnel_down.ps1 -RemoteHost 192.168.3.50

param(
    [string]$RemoteHost = "192.168.3.50"
)

$processes = Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" | Where-Object {
    $_.CommandLine -match [regex]::Escape($RemoteHost)
}

if (-not $processes) {
    Write-Host "[INFO] No running SSH tunnel to ${RemoteHost}"
    return
}

foreach ($proc in $processes) {
    Write-Host "[INFO] Stopping SSH tunnel (PID: $($proc.ProcessId)) -> ${RemoteHost}"
    Stop-Process -Id $proc.ProcessId -Force
}

Write-Host "[INFO] Stopped all SSH tunnels to ${RemoteHost}"
