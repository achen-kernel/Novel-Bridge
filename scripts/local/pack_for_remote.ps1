$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "."
$OutputFile = Join-Path $ProjectRoot "novelbridge.tar.gz"

Write-Host "=== NovelBridge Remote Deployment Package ===" -ForegroundColor Cyan
Write-Host "Project root : $ProjectRoot"
Write-Host "Output file : $OutputFile"
Write-Host ""

$includePaths = @(
    "apps/rag-agent",
    "deploy/remote",
    "scripts/remote",
    "docs",
    "schema.sql"
)

Write-Host "Including:" -ForegroundColor Yellow
foreach ($p in $includePaths) {
    if (Test-Path $p) {
        Write-Host "  [OK] $p" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $p" -ForegroundColor Red
    }
}

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

Write-Host ""
Write-Host "Creating archive..." -ForegroundColor Cyan

tar -czf $OutputFile `
    --exclude=".git" --exclude=".idea" --exclude=".opencode" --exclude=".vtl" `
    --exclude="node_modules" --exclude="__pycache__" --exclude=".venv" `
    --exclude="*.pyc" --exclude="target" --exclude="data" --exclude="book-test" `
    --exclude="AI Reader*" `
    apps/rag-agent deploy/remote scripts/remote docs schema.sql

if ($LASTEXITCODE -eq 0) {
    $fileSize = (Get-Item $OutputFile).Length
    if ($fileSize -gt 1MB) {
        $human = "{0:N1} MB" -f ($fileSize / 1MB)
    } else {
        $human = "{0:N0} KB" -f ($fileSize / 1KB)
    }
    Write-Host ""
    Write-Host "DONE: $OutputFile ($human)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Upload to remote and run:" -ForegroundColor Cyan
    Write-Host "  cd /home/wk/novelbridge"
    Write-Host "  tar xzf novelbridge.tar.gz"
    Write-Host "  cp deploy/remote/.env.example deploy/remote/.env"
    Write-Host "  nano deploy/remote/.env"
    Write-Host "  bash deploy/remote/nb_up.sh"
} else {
    Write-Error "Packaging failed (exit code: $LASTEXITCODE)"
}
