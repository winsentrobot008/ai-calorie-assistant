# AI Calorie Assistant — Production Build Script
# Run from the project root directory.
# Usage: .\scripts\build_prod.ps1

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AI Calorie Assistant — Production Build" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Clean previous builds
Write-Host "`n[1/4] Cleaning previous builds..." -ForegroundColor Yellow
$pathsToClean = @(
    "webapp\dist",
    "dist",
    "__pycache__"
)
foreach ($p in $pathsToClean) {
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p
        Write-Host "  ✓ Removed $p" -ForegroundColor Green
    }
}

# 2. Install frontend dependencies & build
Write-Host "`n[2/4] Building frontend..." -ForegroundColor Yellow
Set-Location webapp
if (-not (Test-Path "node_modules")) {
    Write-Host "  Installing npm dependencies..." -ForegroundColor Gray
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ npm install failed" -ForegroundColor Red
        exit 1
    }
}
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Frontend build failed" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Frontend built to webapp/dist/" -ForegroundColor Green
Set-Location $ProjectRoot

# 3. Check backend dependencies
Write-Host "`n[3/4] Checking backend dependencies..." -ForegroundColor Yellow
Set-Location backend
$missingDeps = $false
$required = @("fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "httpx", "python-multipart", "python-dotenv")
foreach ($pkg in $required) {
    $check = pip show $pkg 2>$null
    if (-not $check) {
        Write-Host "  ✗ Missing: $pkg" -ForegroundColor Red
        $missingDeps = $true
    }
}
if ($missingDeps) {
    Write-Host "  Installing missing dependencies..." -ForegroundColor Gray
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ pip install failed" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✓ Backend dependencies OK" -ForegroundColor Green
Set-Location $ProjectRoot

# 4. Create dist/ directory with production artifacts
Write-Host "`n[4/4] Assembling dist/ directory..." -ForegroundColor Yellow
if (-not (Test-Path "dist")) {
    New-Item -ItemType Directory -Path "dist" -Force | Out-Null
}
New-Item -ItemType Directory -Path "dist\webapp" -Force | Out-Null
New-Item -ItemType Directory -Path "dist\backend" -Force | Out-Null

# Copy frontend build
Copy-Item -Recurse "webapp\dist\*" "dist\webapp\" -Force
Write-Host "  ✓ Frontend assets copied" -ForegroundColor Green

# Copy backend source
Copy-Item -Recurse "backend\app" "dist\backend\" -Force
Copy-Item "backend\requirements.txt" "dist\backend\" -Force
Copy-Item "backend\.env.production" "dist\backend\.env" -Force
Write-Host "  ✓ Backend source copied" -ForegroundColor Green

# Copy start scripts
Copy-Item "scripts\start_prod.ps1" "dist\" -Force
Write-Host "  ✓ Start script copied" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Build Complete! Output: dist/" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To deploy:" -ForegroundColor White
Write-Host "  1. cd dist" -ForegroundColor Gray
Write-Host "  2. Edit backend\.env with your API key" -ForegroundColor Gray
Write-Host "  3. .\start_prod.ps1" -ForegroundColor Gray
