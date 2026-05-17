<#
.SYNOPSIS
  Sync rag-agent files from remote server (extract + copy + cleanup)
.DESCRIPTION
  After downloading sync.tar.gz from remote Linux via scp, run this script to:
  1. Extract sync.tar.gz
  2. Copy apps/rag-agent/ -> rag-agent/ (merge remote Python code)
  3. Keep _remote suffixed dirs (docs/learn_remote/, .opencode/..._remote/)
  4. Keep AGENTS_remote.md
  5. Remove temp dirs (apps/, sync.tar.gz)
#>

$ErrorActionPreference = "Stop"
$SCRIPT_DIR = Split-Path -Parent $PSCommandPath
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR\..\.."

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NovelBridge -- Sync from Remote" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ---- Find sync tar ----
$tarFile = "$PROJECT_ROOT\sync.tar.gz"
if (-not (Test-Path $tarFile)) {
    Write-Host "ERROR: sync.tar.gz not found at $tarFile" -ForegroundColor Red
    Write-Host "Download it first: scp wk@<remote-ip>:/home/wk/novelbridge/sync.tar.gz ." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found sync.tar.gz" -ForegroundColor Green

# ---- Extract ----
Write-Host "Extracting..." -ForegroundColor Yellow
Push-Location $PROJECT_ROOT
tar xzf $tarFile
Pop-Location
Write-Host "Extract done" -ForegroundColor Green

# ---- Merge apps/rag-agent/ -> rag-agent/ ----
if (Test-Path "$PROJECT_ROOT\apps\rag-agent") {
    Write-Host "Merging apps/rag-agent/ -> rag-agent/ ..." -ForegroundColor Yellow
    Copy-Item -Path "$PROJECT_ROOT\apps\rag-agent\*" -Destination "$PROJECT_ROOT\rag-agent\" -Recurse -Force
    Write-Host "rag-agent/ merged" -ForegroundColor Green
} else {
    Write-Host "No apps/rag-agent/ found, skipping" -ForegroundColor Yellow
}

# ---- Cleanup ----
if (Test-Path "$PROJECT_ROOT\apps") {
    Write-Host "Removing apps/ ..." -ForegroundColor Yellow
    Remove-Item -Path "$PROJECT_ROOT\apps" -Recurse -Force
}

if (Test-Path $tarFile) {
    Write-Host "Removing sync.tar.gz ..." -ForegroundColor Yellow
    Remove-Item -Path $tarFile -Force
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sync complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kept in project:"
Write-Host "  .opencode/skills/vibe-learn_remote/"
Write-Host "  docs/learn_remote/"
Write-Host "  AGENTS_remote.md"
Write-Host ""
Write-Host "Run git status to see all changes:" -ForegroundColor Yellow
Write-Host "  git status" -ForegroundColor Yellow
