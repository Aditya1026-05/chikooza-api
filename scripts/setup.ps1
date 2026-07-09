# setup.ps1 - Initial setup, dependency installation, and validation for Windows

$ErrorActionPreference = "Stop"

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Log-Info "Starting environment setup..."

# 1. Check Git
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Log-Error "Git is not installed or not in system PATH. Please install Git and try again."
    exit 1
}
Log-Success "Git is available: $((git --version).Trim())"

# 2. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Log-Error "Python is not installed or not in system PATH. Please install Python 3.11+ and try again."
    exit 1
}

$pythonVersion = & $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonMajor = & $pythonCmd.Source -c "import sys; print(sys.version_info.major)"
$pythonMinor = & $pythonCmd.Source -c "import sys; print(sys.version_info.minor)"

if ([int]$pythonMajor -lt 3 -or ([int]$pythonMajor -eq 3 -and [int]$pythonMinor -lt 11)) {
    Log-Error "Python version must be 3.11 or higher. Detected: $pythonVersion"
    exit 1
}
Log-Success "Python is available (version $pythonVersion): $($pythonCmd.Source)"

# 3. Check Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Log-Error "Node.js is not installed or not in system PATH. Please install Node.js 18+ and try again."
    exit 1
}

$nodeVersionStr = & node -v
$nodeVersion = $nodeVersionStr.Trim().TrimStart('v')
$nodeMajor = $nodeVersion.Split('.')[0]

if ([int]$nodeMajor -lt 18) {
    Log-Error "Node.js version must be 18 or higher. Detected: $nodeVersion"
    exit 1
}
Log-Success "Node.js is available (version $nodeVersion): $($nodeCmd.Source)"

# 4. Check NPM
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Log-Error "NPM is not installed or not in system PATH. Please install NPM and try again."
    exit 1
}
Log-Success "NPM is available: $(npm -v)"

# 5. Virtual Environment Setup
$venvPath = $Script:VenvDir
$pythonVenvExec = "$venvPath\Scripts\python.exe"

if (-not (Test-Path $venvPath)) {
    Log-Info "Creating Python virtual environment in $venvPath..."
    & $pythonCmd.Source -m venv $venvPath
}
Log-Success "Python virtual environment verified at: $venvPath"

# Upgrade pip and install backend requirements
Log-Info "Upgrading pip..."
& $pythonVenvExec -m pip install --upgrade pip

Log-Info "Installing Python dependencies from requirements.txt..."
& $pythonVenvExec -m pip install -r "$Script:ProjectRoot\requirements.txt"
Log-Success "Backend dependencies installed successfully."

# 6. Install Frontend Dependencies
Log-Info "Installing Frontend dependencies in $Script:FrontendDir..."
if (Test-Path $Script:FrontendDir) {
    Push-Location $Script:FrontendDir
    & npm install
    Pop-Location
    Log-Success "Frontend dependencies installed successfully."
} else {
    Log-Error "Frontend directory not found at $Script:FrontendDir"
    exit 1
}

# 7. Setup Environment Files
# Root .env
$rootEnv = "$Script:ProjectRoot\.env"
$rootEnvEx = "$Script:ProjectRoot\.env.example"
if (-not (Test-Path $rootEnv)) {
    Log-Info "Root .env not found. Creating from .env.example..."
    Copy-Item $rootEnvEx $rootEnv
    Log-Success "Root .env file created."
} else {
    Log-Info "Root .env file already exists."
}

# Frontend .env
$frontEnv = "$Script:FrontendDir\.env"
$frontEnvEx = "$Script:FrontendDir\.env.example"
if (-not (Test-Path $frontEnv)) {
    Log-Info "Frontend .env not found. Creating from .env.example..."
    Copy-Item $frontEnvEx $frontEnv
    Log-Success "Frontend .env file created."
} else {
    Log-Info "Frontend .env file already exists."
}

# Validate env vars
Load-Env $rootEnv

$groqKey = [System.Environment]::GetEnvironmentVariable("GROQ_API_KEY")
if (-not $groqKey) {
    Log-Warning "GROQ_API_KEY is not configured in your .env file. The AI/RAG features will run with fallback retrieve-only answers."
}

# 8. Verify Database Connectivity & Apply Migrations
Log-Info "Checking database connectivity..."
$dbCheckCmd = "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"

$dbCheckSuccess = $true
try {
    $null = & $pythonVenvExec -c $dbCheckCmd 2>&1
} catch {
    $dbCheckSuccess = $false
}

if ($dbCheckSuccess) {
    Log-Success "Database connectivity verified."
    
    Log-Info "Applying database migrations..."
    & $pythonVenvExec "$Script:ProjectRoot\manage.py" migrate
    Log-Success "Database migrations successfully applied."
} else {
    Log-Error "Failed to connect to the database. Please check your DATABASE_URL or write access to the SQLite file."
    exit 1
}

Log-Success "Setup workflow completed successfully!"
