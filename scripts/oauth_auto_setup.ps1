<#
.SYNOPSIS
  OAuth Configuration Helper for AI Calorie Assistant.
  Checks .env values, opens developer consoles, and provides setup guidance.
#>

$ErrorActionPreference = "Stop"

# --- Paths ---
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BACKEND_ENV  = Join-Path $PROJECT_ROOT "backend\.env"
$WEBAPP_ENV   = Join-Path $PROJECT_ROOT "webapp\.env"

# --- Helpers ---
function Read-EnvValue($envFile, $key) {
    if (-not (Test-Path $envFile)) { return $null }
    $line = (Get-Content $envFile) -match "^$key="
    if (-not $line) { return $null }
    return ($line -replace "^$key=", "").Trim('"').Trim("'")
}

function Ok($v) { return (-not [string]::IsNullOrEmpty($v)) }

function Print-Section($title) {
    Write-Host "`n--- $title ---" -ForegroundColor Cyan
}

# ════════════════════════════════════════════════════
#  1. Scan .env
# ════════════════════════════════════════════════════

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   AI OAuth Configuration Helper" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Backend
Print-Section "backend/.env"
$bGoogleId  = Read-EnvValue $BACKEND_ENV "GOOGLE_CLIENT_ID"
$bAppleId   = Read-EnvValue $BACKEND_ENV "APPLE_CLIENT_ID"
$bFbId      = Read-EnvValue $BACKEND_ENV "FACEBOOK_APP_ID"
$bFbSecret  = Read-EnvValue $BACKEND_ENV "FACEBOOK_APP_SECRET"
$bJwtSecret = Read-EnvValue $BACKEND_ENV "JWT_SECRET"

$items = @(
    @("GOOGLE_CLIENT_ID", $bGoogleId),
    @("APPLE_CLIENT_ID", $bAppleId),
    @("FACEBOOK_APP_ID", $bFbId),
    @("FACEBOOK_APP_SECRET", $bFbSecret),
    @("JWT_SECRET", $bJwtSecret)
)
foreach ($item in $items) {
    $key = $item[0]; $val = $item[1]
    $ok = Ok $val
    $icon = if ($ok) { "[OK]" } else { "[--]" }
    $color = if ($ok) { "Green" } else { "Red" }
    $display = if ($ok -and $val.Length -gt 40) { $val.Substring(0, 40) + "..." } else { $val }
    Write-Host "  $icon $key = $display" -ForegroundColor $color
}

# Frontend
Print-Section "webapp/.env"
$wGoogleId = Read-EnvValue $WEBAPP_ENV "VITE_GOOGLE_CLIENT_ID"
$wFbId     = Read-EnvValue $WEBAPP_ENV "VITE_FACEBOOK_APP_ID"

$items2 = @(
    @("VITE_GOOGLE_CLIENT_ID", $wGoogleId),
    @("VITE_FACEBOOK_APP_ID", $wFbId)
)
foreach ($item in $items2) {
    $key = $item[0]; $val = $item[1]
    $ok = Ok $val
    $icon = if ($ok) { "[OK]" } else { "[--]" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host "  $icon $key = $val" -ForegroundColor $color
}

# ════════════════════════════════════════════════════
#  2. Action menu
# ════════════════════════════════════════════════════

Print-Section "Quick Actions"
Write-Host "  [1] Google    - Open Google Cloud Console"
Write-Host "  [2] Apple     - Open Apple Developer"
Write-Host "  [3] Facebook  - Open Facebook Developer"
Write-Host "  [4] Open ALL three consoles"
Write-Host "  [5] Check only (no browser)"
Write-Host "  [0] Exit"

$choice = Read-Host "`nSelect (0-5)"

switch ($choice) {
    "1" {
        Write-Host "Opening Google Cloud Console..." -ForegroundColor Yellow
        Start-Process "https://console.cloud.google.com/apis/credentials"
    }
    "2" {
        Write-Host "Opening Apple Developer..." -ForegroundColor Yellow
        Start-Process "https://developer.apple.com/account/resources/authkeys/list"
    }
    "3" {
        Write-Host "Opening Facebook Developer..." -ForegroundColor Yellow
        Start-Process "https://developers.facebook.com/apps/"
    }
    "4" {
        Write-Host "Opening all consoles..." -ForegroundColor Yellow
        Start-Process "https://console.cloud.google.com/apis/credentials"
        Start-Process "https://developer.apple.com/account/resources/authkeys/list"
        Start-Process "https://developers.facebook.com/apps/"
    }
    "5" { Write-Host "Skip browser." -ForegroundColor Gray }
    "0" { Write-Host "Exit."; exit }
    default { Write-Host "Invalid choice." -ForegroundColor Red }
}

# ════════════════════════════════════════════════════
#  3. Diagnosis
# ════════════════════════════════════════════════════

Print-Section "Diagnosis"

$allGreen = $true

# Google
if ((Ok $bGoogleId) -and (Ok $wGoogleId)) {
    if ($bGoogleId -eq $wGoogleId) {
        Write-Host "  [OK] Google: frontend & backend Client ID match" -ForegroundColor Green
    } else {
        Write-Host "  [!!] Google: Client ID mismatch!" -ForegroundColor Yellow
        Write-Host "        backend:  $bGoogleId"
        Write-Host "        frontend: $wGoogleId"
        $allGreen = $false
    }
} else {
    $allGreen = $false
    if (-not (Ok $bGoogleId)) { Write-Host "  [--] Google: backend GOOGLE_CLIENT_ID missing" -ForegroundColor Red }
    if (-not (Ok $wGoogleId)) { Write-Host "  [--] Google: frontend VITE_GOOGLE_CLIENT_ID missing" -ForegroundColor Red }
    Write-Host "        -> Create OAuth 2.0 Web Client ID in Google Cloud Console"
    Write-Host "           Authorized JS origins: http://localhost:5173"
}

# Apple
if (Ok $bAppleId) {
    Write-Host "  [OK] Apple: APPLE_CLIENT_ID configured" -ForegroundColor Green
} else {
    $allGreen = $false
    Write-Host "  [--] Apple: APPLE_CLIENT_ID missing" -ForegroundColor Red
    Write-Host "        -> Create Services ID with Sign in with Apple enabled in Apple Developer"
    Write-Host "           Return URL: https://localhost:8001/api/v1/user/oauth/apple"
}

# Facebook
if ((Ok $bFbId) -and (Ok $bFbSecret) -and (Ok $wFbId)) {
    Write-Host "  [OK] Facebook: fully configured" -ForegroundColor Green
} else {
    $allGreen = $false
    if (-not (Ok $bFbId))     { Write-Host "  [--] Facebook: backend FACEBOOK_APP_ID missing" -ForegroundColor Red }
    if (-not (Ok $bFbSecret)) { Write-Host "  [--] Facebook: backend FACEBOOK_APP_SECRET missing" -ForegroundColor Red }
    if (-not (Ok $wFbId))     { Write-Host "  [--] Facebook: frontend VITE_FACEBOOK_APP_ID missing" -ForegroundColor Red }
    Write-Host "        -> Create Consumer App in Facebook Developers"
    Write-Host "           Enable Facebook Login"
    Write-Host "           Valid OAuth Redirect URIs: http://localhost:5173/"
}

# JWT
if ((Ok $bJwtSecret) -and ($bJwtSecret -ne "change-this-to-a-random-secret-in-production")) {
    Write-Host "  [OK] JWT: custom secret configured" -ForegroundColor Green
} else {
    Write-Host "  [!!] JWT: using default secret -- change before production" -ForegroundColor Yellow
}

# ════════════════════════════════════════════════════
#  4. Summary
# ════════════════════════════════════════════════════

Write-Host "`n============================================" -ForegroundColor Cyan
if ($allGreen) {
    Write-Host "  All OAuth providers configured!" -ForegroundColor Green
    Write-Host "  Restart both services to apply:" -ForegroundColor White
} else {
    Write-Host "  Some configs are missing - see above." -ForegroundColor Yellow
    Write-Host "  After updating, restart services:" -ForegroundColor White
}
Write-Host "    backend: uvicorn app.main:app --port 8001 --reload"
Write-Host "    webapp:  npm run dev"
Write-Host "============================================`n" -ForegroundColor Cyan
