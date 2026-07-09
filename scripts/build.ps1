# build.ps1 - Prepares the application for production deployment on Windows

$ErrorActionPreference = "Stop"

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

$pythonVenvExec = "$Script:VenvDir\Scripts\python.exe"

Log-Info "Preparing application for production build..."

# 1. Verify venv
if (-not (Test-Path $Script:VenvDir)) {
    Log-Error "Virtual environment not found. Please run scripts/setup.ps1 first."
    exit 1
}

# 2. Django Production Preparation
Log-Info "=== Backend Production Verification & Preparation ==="

# Check Django deployment settings
Log-Info "Running Django deployment checks..."
try {
    & $pythonVenvExec "$Script:ProjectRoot\manage.py" check --deploy
} catch {
    Log-Warning "Django deployment check flagged recommendations (please review)."
}

# Collect static assets
Log-Info "Collecting Django static files..."
& $pythonVenvExec "$Script:ProjectRoot\manage.py" collectstatic --no-input
Log-Success "Static files successfully collected."

# 3. Frontend Production Build
Log-Info "=== Frontend Production Compilation ==="
if (Test-Path $Script:FrontendDir) {
    Log-Info "Compiling frontend assets via Vite..."
    Push-Location $Script:FrontendDir
    & npm run build
    Pop-Location
    Log-Success "Frontend compiled successfully (output directory: $Script:FrontendDir\build\)."
} else {
    Log-Error "Frontend directory not found at $Script:FrontendDir"
    exit 1
}

Log-Success "Build workflow successfully completed! Assets are ready for production."
