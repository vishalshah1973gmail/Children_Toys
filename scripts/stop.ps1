<#
  Stops the ToyBox backend and frontend started by start.ps1 on Windows.
  Run from anywhere:

      .\scripts\stop.ps1

  Kills by tracked PID first (whole process tree, since npm/vite spawn child
  processes), then falls back to whatever is listening on ports 8000/5173 in
  case the PID file is stale or missing.
#>

$PidDir = Join-Path $PSScriptRoot ".pids"
$BackendPidFile = Join-Path $PidDir "backend.pid"
$FrontendPidFile = Join-Path $PidDir "frontend.pid"

function Stop-ByPidFile($PidFile, $Label) {
    if (-not (Test-Path $PidFile)) { return }
    $processId = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Write-Host "Stopping $Label (PID $processId)..."
        taskkill /PID $processId /T /F 2>$null | Out-Null
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

function Stop-ByPort($Port, $Label) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $ownerId = $conn.OwningProcess
        if ($ownerId -and (Get-Process -Id $ownerId -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping $Label on port $Port (PID $ownerId)..."
            taskkill /PID $ownerId /T /F 2>$null | Out-Null
        }
    }
}

Stop-ByPidFile $BackendPidFile "backend"
Stop-ByPidFile $FrontendPidFile "frontend"

# Fallback in case a process was started outside these scripts, or survived
# the PID-based kill as an orphan.
Stop-ByPort 8000 "backend"
Stop-ByPort 5173 "frontend"

Write-Host "ToyBox stopped." -ForegroundColor Green
