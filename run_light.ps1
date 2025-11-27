param(
    [int]$Port = 8000,
    [string]$DbPath = "D:\Sanctum\tmp\rsn-light.db"
)

Push-Location $PSScriptRoot

# Minimal env for light/demo
$env:ALLOW_PLACEHOLDER_PIPELINE = "1"
$env:RSN_JWKS_URL = "local"
$env:RSN_SECRET_KEY = "demo-secret"
$env:JWT_SECRET_KEY = "demo-jwt"
$env:DATABASE_URL = "sqlite:///$DbPath"
$env:DB_URL = $env:DATABASE_URL

# Ensure DB folder exists
$dbDir = Split-Path $DbPath
if (-not (Test-Path $dbDir)) { New-Item -ItemType Directory -Path $dbDir | Out-Null }

# Choose Python (prefer active venv)
$python = "python"
if ($env:VIRTUAL_ENV) {
    $candidate = Join-Path $env:VIRTUAL_ENV "Scripts/python.exe"
    if (Test-Path $candidate) { $python = $candidate }
}

# Run API
Push-Location backend
& $python -m uvicorn app.main:app --port $Port
Pop-Location

Pop-Location
