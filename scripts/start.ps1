<#
  Starts the ToyBox backend (FastAPI/uvicorn) and frontend (Vite) as background
  processes on Windows. Run from anywhere:

      .\scripts\start.ps1

  Logs go to scripts\logs\, PIDs are tracked in scripts\.pids\ so stop.ps1 can
  find and kill the right processes.
#>

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$PidDir = Join-Path $PSScriptRoot ".pids"
$LogDir = Join-Path $PSScriptRoot "logs"
$BackendPidFile = Join-Path $PidDir "backend.pid"
$FrontendPidFile = Join-Path $PidDir "frontend.pid"

New-Item -ItemType Directory -Force -Path $PidDir, $LogDir | Out-Null

function Test-ProcessAlive($ProcId) {
    if (-not $ProcId) { return $false }
    return $null -ne (Get-Process -Id $ProcId -ErrorAction SilentlyContinue)
}

function Test-AlreadyRunning($PidFile, $Label) {
    if (Test-Path $PidFile) {
        $existingId = Get-Content $PidFile -ErrorAction SilentlyContinue
        if (Test-ProcessAlive $existingId) {
            Write-Host "$Label is already running (PID $existingId). Run stop.ps1 first if you want to restart it." -ForegroundColor Yellow
            return $true
        }
        Remove-Item $PidFile -ErrorAction SilentlyContinue
    }
    return $false
}

# --- Preflight checks -------------------------------------------------------

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "frontend\node_modules not found. Run 'npm install' inside frontend\ first, then re-run this script." -ForegroundColor Red
    exit 1
}

try {
    python -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "missing" }
} catch {
    Write-Host "Backend Python dependencies not found. Run 'pip install -r backend\requirements.txt' first, then re-run this script." -ForegroundColor Red
    exit 1
}

# --- Backend -----------------------------------------------------------------

if (-not (Test-AlreadyRunning $BackendPidFile "Backend")) {
    Write-Host "Starting backend (uvicorn) on http://localhost:8000 ..."
    $backendProc = Start-Process -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput (Join-Path $LogDir "backend.log") `
        -RedirectStandardError (Join-Path $LogDir "backend.err.log") `
        -WindowStyle Hidden -PassThru
    $backendProc.Id | Out-File -FilePath $BackendPidFile -Encoding ascii
}

# --- Frontend ------------------------------------------------------------------

if (-not (Test-AlreadyRunning $FrontendPidFile "Frontend")) {
    Write-Host "Starting frontend (vite) on http://localhost:5173 ..."
    $frontendProc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "npm run dev" `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput (Join-Path $LogDir "frontend.log") `
        -RedirectStandardError (Join-Path $LogDir "frontend.err.log") `
        -WindowStyle Hidden -PassThru
    $frontendProc.Id | Out-File -FilePath $FrontendPidFile -Encoding ascii
}

# --- Wait for backend health ---------------------------------------------------

Write-Host "Waiting for backend to become healthy..."
$healthy = $false
for ($i = 0; $i -lt 150; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 1
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 300
}

if ($healthy) {
    Write-Host "Backend is healthy." -ForegroundColor Green
} else {
    Write-Host "Backend did not report healthy within 45s. Check scripts\logs\backend.err.log" -ForegroundColor Yellow
}

# --- Cloudflare tunnel (docker) -------------------------------------------------
# Token is read from CLOUDFLARE_TUNNEL_TOKEN in backend\.env (gitignored), so it never lives in this file.
# Passed via -e TUNNEL_TOKEN so it does not show in the process list either.

$TunnelContainer = "toybox-tunnel"

function Get-EnvFileValue($Path, $Key) {
    if (-not (Test-Path $Path)) { return $null }
    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) { return $null }
    $value = ($line -replace "^\s*$Key\s*=\s*", "") -replace "\s+#.*$", ""
    return $value.Trim().Trim('"').Trim("'")
}

$TunnelToken = Get-EnvFileValue (Join-Path $BackendDir ".env") "CLOUDFLARE_TUNNEL_TOKEN"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "docker not found - skipping Cloudflare tunnel." -ForegroundColor Yellow
} elseif (-not $TunnelToken) {
    Write-Host "CLOUDFLARE_TUNNEL_TOKEN not set in backend\.env - skipping Cloudflare tunnel." -ForegroundColor Yellow
} else {
    docker rm -f $TunnelContainer 2>$null | Out-Null
    $env:TUNNEL_TOKEN = $TunnelToken
    Write-Host "Starting Cloudflare tunnel container ($TunnelContainer) ..."
    docker run -d --name $TunnelContainer --restart unless-stopped -e TUNNEL_TOKEN cloudflare/cloudflared:latest tunnel --no-autoupdate run | Out-Null
    Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tunnel started: https://toybox.demoaiprojects.com" -ForegroundColor Green
    } else {
        Write-Host "Tunnel container failed to start. Is Docker Desktop running?" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "ToyBox is starting up:" -ForegroundColor Cyan
Write-Host "  Backend  : http://localhost:8000  (API docs at /docs)"
Write-Host "  Frontend : http://localhost:5173"
Write-Host ""
Write-Host "Logs: scripts\logs\backend.log / frontend.log"
Write-Host "To stop everything, run: .\scripts\stop.ps1"
