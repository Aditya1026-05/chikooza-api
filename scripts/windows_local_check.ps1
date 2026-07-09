$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

Write-Step "Creating Python virtual environment"
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv venv
} else {
    throw "Python 3 is required. Install Python and add it to PATH."
}

$PythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
$PipExe = Join-Path $RepoRoot "venv\Scripts\pip.exe"

if (!(Test-Path $PythonExe)) {
    throw "Could not find $PythonExe"
}

& $PythonExe -m pip install --upgrade pip

Write-Step "Installing backend dependencies"
& $PipExe install -r requirements.txt

if (!(Test-Path ".env")) {
    Write-Step "Creating local backend .env from .env.example"
    Copy-Item ".env.example" ".env"
}

Write-Step "Running Django checks"
& $PythonExe manage.py check

if ($env:RUN_TESTS -ne "false") {
    Write-Step "Running backend tests"
    & $PythonExe manage.py test
}

Write-Step "Installing frontend dependencies and building React app"
Set-Location (Join-Path $RepoRoot "chikooza-ui")

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required. Install Node.js first."
}

npm install

if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

npm run build

Write-Step "Windows local check completed"
