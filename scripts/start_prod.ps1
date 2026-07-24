# AI Calorie Assistant — Production Start Script
# Run from the project root or dist/ directory.
# Usage: .\scripts\start_prod.ps1
#
# The script loads .env.production (or .env in dist/), then starts:
#   - FastAPI backend (no reload)
#   - Static file server for frontend SPA

param(
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5173",
    [string]$EnvFile = ""
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

# Determine env file
if (-not $EnvFile) {
    if (Test-Path "backend\.env.production") {
        $EnvFile = "backend\.env.production"
    } elseif (Test-Path "backend\.env") {
        $EnvFile = "backend\.env"
    } else {
        Write-Host "[ERROR] No env file found! Create backend\.env.production or backend\.env" -ForegroundColor Red
        exit 1
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AI Calorie Assistant — Production Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Env file : $EnvFile" -ForegroundColor Gray
Write-Host "  API Port  : $BackendPort" -ForegroundColor Gray
Write-Host "  UI Port   : $FrontendPort" -ForegroundColor Gray
Write-Host ""

# ── Step 1: Start Backend (FastAPI, no reload) ──
Write-Host "[1/2] Starting FastAPI backend on port $BackendPort..." -ForegroundColor Yellow

$env:BACKEND_PORT = $BackendPort

# Start uvicorn as a background job
$backendJob = Start-Job -Name "CalorieBackend" -ScriptBlock {
    param($port, $envFile)
    Set-Location $using:ProjectRoot

    # Load env vars from .env.production
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.+)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value)
        }
    }

    # Start uvicorn
    $logFile = Join-Path $using:ProjectRoot "storage\prod_server.log"
    uvicorn app.main:app --host 0.0.0.0 --port $port --no-reload --log-level info *>&1 | Out-File -FilePath $logFile -Append
} -ArgumentList $BackendPort, $EnvFile

Start-Sleep -Seconds 3

# Check if backend started
$backendRunning = Get-Job -Name "CalorieBackend" -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Running' }
if (-not $backendRunning) {
    Write-Host "  ✗ Backend failed to start. Check storage\prod_server.log" -ForegroundColor Red
    $jobInfo = Receive-Job -Name "CalorieBackend" -Keep
    Write-Host $jobInfo
    exit 1
}
Write-Host "  ✓ Backend running (PID: $($backendRunning.Id))" -ForegroundColor Green

# ── Step 2: Determine frontend build path ──
Write-Host "[2/2] Starting frontend static server on port $FrontendPort..." -ForegroundColor Yellow

$frontendDir = ""
if (Test-Path "webapp\dist") {
    $frontendDir = (Resolve-Path "webapp\dist").Path
}
elseif (Test-Path "dist\webapp") {
    $frontendDir = (Resolve-Path "dist\webapp").Path
}
else {
    Write-Host "  [WARN] No frontend build found. Build first with: npm run build (in webapp/)" -ForegroundColor Yellow
    Write-Host "  Starting backend only. Frontend will not be served." -ForegroundColor Yellow
}

if ($frontendDir) {
    Write-Host "  Frontend path: $frontendDir" -ForegroundColor Gray

    # Start a simple Python HTTP server for the frontend SPA
    $frontendJob = Start-Job -Name "CalorieFrontend" -ScriptBlock {
        param($dir, $port)
        Set-Location $dir
        # Use Python's built-in http.server
        python -m http.server $port --bind 0.0.0.0
    } -ArgumentList $frontendDir, $FrontendPort

    Start-Sleep -Seconds 2
    Write-Host "  ✓ Frontend static server started" -ForegroundColor Green
}

# ── Summary ──
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Production services running:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Backend API : http://localhost:$BackendPort" -ForegroundColor White
Write-Host "  Health Check: http://localhost:$BackendPort/health" -ForegroundColor Gray
if ($frontendDir) {
    Write-Host "  Frontend UI : http://localhost:$FrontendPort" -ForegroundColor White
}
Write-Host ""
Write-Host "  Logs (backend): storage\prod_server.log" -ForegroundColor Gray
Write-Host ""
Write-Host "  Stop with: Stop-Job CalorieBackend; Stop-Job CalorieFrontend" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
