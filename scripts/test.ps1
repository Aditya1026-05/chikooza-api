# test.ps1 - Runs backend unit tests and code quality/lint checks on Windows

$ErrorActionPreference = "Stop"

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

$pythonVenvExec = "$Script:VenvDir\Scripts\python.exe"

Log-Info "Preparing to run test suite..."

# 1. Run Python Linting/Formatting checks (isort, black, flake8)
Log-Info "=== PHASE 1: CODE LINTING & STYLE CHECKS ==="

$lintFailed = $false

# Helper to check if pip package is installed
function Test-PipPackage ($PackageName) {
    $result = & $pythonVenvExec -m pip show $PackageName 2>&1
    return ($result -notmatch "WARNING: Package\(s\) not found")
}

# Isort Check
if (Test-PipPackage "isort") {
    Log-Info "Running isort import order check..."
    try {
        & "$Script:VenvDir\Scripts\isort.exe" "$Script:ProjectRoot" --check-only
        Log-Success "Import sorting is correct."
    } catch {
        Log-Warning "isort found import ordering issues. Run: isort ."
        $lintFailed = $true
    }
} else {
    Log-Info "isort is not installed. Skipping..."
}

# Black Check
if (Test-PipPackage "black") {
    Log-Info "Running black formatting check..."
    try {
        & "$Script:VenvDir\Scripts\black.exe" "$Script:ProjectRoot" --check
        Log-Success "Code formatting is correct."
    } catch {
        Log-Warning "black found formatting issues. Run: black ."
        $lintFailed = $true
    }
} else {
    Log-Info "black is not installed. Skipping..."
}

# Flake8 Check
if (Test-PipPackage "flake8") {
    Log-Info "Running flake8 code quality audits..."
    try {
        & "$Script:VenvDir\Scripts\flake8.exe" "$Script:ProjectRoot" --exclude=venv,chikooza_env,migrations
        Log-Success "Flake8 style audits passed."
    } catch {
        Log-Warning "flake8 identified syntax or formatting issues."
        $lintFailed = $true
    }
} else {
    Log-Info "flake8 is not installed. Skipping..."
}

if (-not $lintFailed) {
    Log-Success "All linting audits passed successfully."
} else {
    Log-Warning "Linting checks reported issues. These do not block unit tests."
}

# 2. Run Backend Tests
Log-Info "=== PHASE 2: RUNNING BACKEND UNIT TESTS ==="
$testSuccess = $true
try {
    & $pythonVenvExec "$Script:ProjectRoot\manage.py" test
} catch {
    $testSuccess = $false
}

if ($testSuccess) {
    Log-Success "Backend unit test suite passed successfully!"
} else {
    Log-Error "Backend unit test suite failed."
    exit 1
}

# 3. Check Frontend Tests
Log-Info "=== PHASE 3: FRONTEND TESTS ==="
Log-Info "Frontend tests are not yet configured in this project (no test script found in package.json)."
Log-Success "Test workflow complete."
