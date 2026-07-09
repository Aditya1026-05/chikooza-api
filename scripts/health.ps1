# health.ps1 - Checks the health and status of the entire development ecosystem on Windows

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Load-Env "$Script:ProjectRoot\.env"

Log-Info "Running system health checks..."
Write-Host "=============================================="

# Helper to format status rows
function Print-Status ($Label, $Status, $Detail) {
    if ($Status -eq "OK") {
        Write-Host "[OK]   $Label - $Detail" -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "[WARN] $Label - $Detail" -ForegroundColor Yellow
    } else {
        Write-Host "[FAIL] $Label - $Detail" -ForegroundColor Red
    }
}

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if ($pythonCmd) {
    $pythonVersion = & $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    Print-Status "Python Environment" "OK" "Python $pythonVersion detected"
} else {
    Print-Status "Python Environment" "FAIL" "Python is not installed or not in PATH"
}

# 2. Check Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeVersion = & node -v
    Print-Status "Node.js Environment" "OK" "Node $($nodeVersion.Trim()) detected"
} else {
    Print-Status "Node.js Environment" "FAIL" "Node.js is not installed or not in PATH"
}

# 3. Check virtualenv
$venvPath = $Script:VenvDir
$pythonVenvExec = "$venvPath\Scripts\python.exe"

if (Test-Path $venvPath) {
    if (Test-Path $pythonVenvExec) {
        Print-Status "Virtual Environment" "OK" "Active at $venvPath"
    } else {
        Print-Status "Virtual Environment" "FAIL" "Directory exists but python executable is missing at $pythonVenvExec"
    }
} else {
    Print-Status "Virtual Environment" "FAIL" "No virtualenv found at $venvPath"
}

# 4. Check Frontend node_modules
$frontendNodeModules = "$Script:FrontendDir\node_modules"
if (Test-Path $frontendNodeModules) {
    Print-Status "Frontend Node Modules" "OK" "node_modules installed in $Script:FrontendDir"
} else {
    Print-Status "Frontend Node Modules" "WARN" "node_modules missing in $Script:FrontendDir"
}

# 5. Check configuration files
$rootEnv = "$Script:ProjectRoot\.env"
if (Test-Path $rootEnv) {
    Print-Status "Backend Config (.env)" "OK" "Loaded successfully"
} else {
    Print-Status "Backend Config (.env)" "FAIL" "Missing in $Script:ProjectRoot"
}

$frontEnv = "$Script:FrontendDir\.env"
if (Test-Path $frontEnv) {
    Print-Status "Frontend Config (.env)" "OK" "Loaded successfully"
} else {
    Print-Status "Frontend Config (.env)" "WARN" "Missing in $Script:FrontendDir"
}

# 6. Check Database Connectivity
$dbCheckCmd = "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"
$dbConnected = $false
$dbEngine = "Unknown"

if (Test-Path $pythonVenvExec) {
    try {
        $null = & $pythonVenvExec -c $dbCheckCmd 2>&1
        $dbConnected = $true
        $dbEngine = & $pythonVenvExec -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.conf import settings; print(settings.DATABASES['default']['ENGINE'].split('.')[-1])"
        $dbEngine = $dbEngine.Trim()
    } catch {}
}

if ($dbConnected) {
    Print-Status "Database Connection" "OK" "Connected ($dbEngine)"
} else {
    Print-Status "Database Connection" "FAIL" "Cannot connect to database"
}

# 7. Check Ports & Endpoints
# Check Backend port 8002
$backendActive = $false
$nets8002 = netstat -ano | Select-String ":8002 "
if ($nets8002) {
    $backendActive = $true
}

if ($backendActive) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8002/admin/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -match "200|404|301|302") {
            Print-Status "Backend Port 8002" "OK" "Listening and responsive"
        } else {
            Print-Status "Backend Port 8002" "WARN" "Listening, but returned code: $($resp.StatusCode)"
        }
    } catch {
        Print-Status "Backend Port 8002" "WARN" "Listening, but failed HTTP ping: $_"
    }
} else {
    Print-Status "Backend Port 8002" "FAIL" "Backend is NOT running"
}

# Check Frontend port 5173
$frontendActive = $false
$nets5173 = netstat -ano | Select-String ":5173 "
if ($nets5173) {
    $frontendActive = $true
}

if ($frontendActive) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Print-Status "Frontend Port 5173" "OK" "Listening and responsive (Vite)"
        } else {
            Print-Status "Frontend Port 5173" "WARN" "Listening, but returned status: $($resp.StatusCode)"
        }
    } catch {
        Print-Status "Frontend Port 5173" "WARN" "Listening, but failed HTTP ping: $_"
    }
} else {
    Print-Status "Frontend Port 5173" "FAIL" "Frontend is NOT running"
}

# 8. Check Groq API
$groqKey = [System.Environment]::GetEnvironmentVariable("GROQ_API_KEY")
if ($groqKey) {
    Print-Status "AI / Groq API Key" "OK" "Configured (value length: $($groqKey.Length) chars)"
} else {
    Print-Status "AI / Groq API Key" "WARN" "Not configured (RAG will run in fallback retrieval-only mode)"
}

Write-Host "=============================================="
Log-Info "Health check execution finished."
