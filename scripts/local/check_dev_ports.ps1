# Check local tunnel ports used by NovelBridge local development.
#
# Usage:
#   .\scripts\local\check_dev_ports.ps1

param(
    [string]$HostName = "127.0.0.1",
    [int[]]$Ports = @(13306, 16333, 17474, 17687, 18080, 18082)
)

function Test-TcpPort {
    param([string]$HostName, [int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        if (-not $task.Wait(1500)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

foreach ($port in $Ports) {
    $ok = Test-TcpPort -HostName $HostName -Port $port
    $status = if ($ok) { "open" } else { "closed" }
    Write-Host ("{0}:{1} {2}" -f $HostName, $port, $status)
}
