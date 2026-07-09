# deploy.ps1 - Windows PowerShell deployment script
# Executes a complete, production-quality local deployment workflow for Windows.

$ErrorActionPreference = "Stop"

# Define project root and subdirectories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName
$BackendDir = $ProjectRoot
$FrontendDir = "$ProjectRoot\chikooza-ui"

# Define Virtual Environment paths
if (Test-Path "$ProjectRoot\venv") {
    $VenvDir = "$ProjectRoot\venv"
} elseif (Test-Path "$ProjectRoot\chikooza_env") {
    $VenvDir = "$ProjectRoot\chikooza_env"
} else {
    $VenvDir = "$ProjectRoot\venv"
}
$PythonVenvExec = "$VenvDir\Scripts\python.exe"

function Get-Timestamp {
    return (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
}

function Log-Info ($Message) {
    Write-Host "$((Get-Timestamp)) [INFO] $Message" -ForegroundColor Cyan
}

function Log-Success ($Message) {
    Write-Host "$((Get-Timestamp)) [SUCCESS] $Message" -ForegroundColor Green
}

function Log-Warning ($Message) {
    Write-Host "$((Get-Timestamp)) [WARNING] $Message" -ForegroundColor Yellow
}

function Log-Error ($Message) {
    Write-Error "$((Get-Timestamp)) [ERROR] $Message" -ErrorAction Continue
}

# Function to read and set variables from a .env file if it exists, without overwriting existing environment vars
function Load-Env ($EnvFilePath) {
    if (Test-Path $EnvFilePath) {
        Log-Info "Loading environment variables from $EnvFilePath..."
        Get-Content $EnvFilePath | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                if ($line -match "^([^=]+)=(.*)$") {
                    $key = $Matches[1].Trim()
                    $val = $Matches[2].Trim()
                    if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
                        $val = $val.Substring(1, $val.Length - 2)
                    }
                    if (-not [System.Environment]::GetEnvironmentVariable($key)) {
                        [System.Environment]::SetEnvironmentVariable($key, $val, [System.EnvironmentVariableTarget]::Process)
                    }
                }
            }
        }
    }
}

# 1. SETUP & VALIDATE SYSTEM
Log-Info "=== PHASE 1: SETUP & VALIDATE SYSTEM ==="

# Check OS suitability (verify we are running on Windows)
if ($OS -notmatch "Windows") {
    Log-Warning "Detected OS is not Windows, but attempting execution since this is deploy.ps1."
}
Log-Success "Operating system validated: Windows"

# Check Git
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Log-Error "Git is not installed or not in system PATH. Please install Git and try again."
    exit 1
}
Log-Success "Git verified."

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Log-Error "Python is not installed. Please install Python 3.11+ and try again."
    exit 1
}
$pythonVersion = & $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonMajor = & $pythonCmd.Source -c "import sys; print(sys.version_info.major)"
$pythonMinor = & $pythonCmd.Source -c "import sys; print(sys.version_info.minor)"
if ([int]$pythonMajor -lt 3 -or ([int]$pythonMajor -eq 3 -and [int]$pythonMinor -lt 11)) {
    Log-Error "Python version must be 3.11 or higher. Detected: $pythonVersion"
    exit 1
}
Log-Success "Python version verified: $pythonVersion"

# Check Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Log-Error "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
}
$nodeVersionStr = & node -v
$nodeVersion = $nodeVersionStr.Trim().TrimStart('v')
$nodeMajor = $nodeVersion.Split('.')[0]
if ([int]$nodeMajor -lt 18) {
    Log-Error "Node.js version must be 18 or higher. Detected: $nodeVersion"
    exit 1
}
Log-Success "Node.js version verified: $nodeVersion"

# Load Env Configs
Load-Env "$ProjectRoot\.env"
Load-Env "$FrontendDir\.env"

# 2. PULL LATEST CODE
Log-Info "=== PHASE 2: PULLING LATEST CODE ==="
$currentBranch = (git branch --show-current).Trim()
Log-Info "Syncing repository branch: $currentBranch"
git fetch origin $currentBranch
git pull origin $currentBranch
$commitHash = (git rev-parse --short HEAD).Trim()
Log-Success "Code updated to commit: $commitHash"

# 3. INSTALL DEPENDENCIES
Log-Info "=== PHASE 3: INSTALLING DEPENDENCIES ==="
if (-not (Test-Path $VenvDir)) {
    Log-Info "Creating missing virtual environment at $VenvDir..."
    & $pythonCmd.Source -m venv $VenvDir
}

Log-Info "Updating backend packages..."
& $PythonVenvExec -m pip install --upgrade pip
& $PythonVenvExec -m pip install -r "$ProjectRoot\requirements.txt"
Log-Success "Backend packages installed."

Log-Info "Updating frontend packages..."
Push-Location $FrontendDir
& npm ci
Pop-Location
Log-Success "Frontend packages installed."

# 4. RUN DATABASE MIGRATIONS
Log-Info "=== PHASE 4: RUNNING DATABASE MIGRATIONS ==="
Log-Info "Checking database connectivity..."
$dbCheckCmd = "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"
$dbCheckSuccess = $true
try {
    $null = & $PythonVenvExec -c $dbCheckCmd 2>&1
} catch {
    $dbCheckSuccess = $false
}

if ($dbCheckSuccess) {
    Log-Success "Database connectivity established."
    Log-Info "Applying migrations..."
    & $PythonVenvExec "$ProjectRoot\manage.py" migrate --no-input
    Log-Success "Database migrations completed."
} else {
    Log-Error "Failed to connect to the database. Verify DATABASE_URL in .env or SQLite file permissions."
    exit 1
}

# 5. BUILD ASSETS
Log-Info "=== PHASE 5: BUILDING STATIC ASSETS ==="
Log-Info "Collecting Django static files..."
& $PythonVenvExec "$ProjectRoot\manage.py" collectstatic --no-input
Log-Success "Django static files collected."

Log-Info "Compiling frontend assets via Vite..."
Push-Location $FrontendDir
& npm run build
Pop-Location
Log-Success "Frontend compilation complete."

# 6. RESTART SERVICES (Windows Background Processes)
Log-Info "=== PHASE 6: RESTARTING SERVICES ==="

# Helper to find and stop processes listening on specific ports on Windows
function Stop-PortProcess ($Port) {
    $nets = netstat -ano | Select-String ":$Port "
    if ($nets) {
        $pids = @()
        foreach ($net in $nets) {
            $parts = $net.Line.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
            if ($parts.Length -ge 5) {
                $pidVal = $parts[4]
                if ($pidVal -match '^\d+$') {
                    $pids += [int]$pidVal
                }
            }
        }
        $uniquePids = $pids | Select-Object -Unique
        foreach ($p in $uniquePids) {
            if ($p -gt 0) {
                Log-Info "Stopping active process listening on port $Port (PID: $p)..."
                Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Stop old processes running on 8002 and 5173
Stop-PortProcess 8002
Stop-PortProcess 5173

# Start Gunicorn-equivalent (waitress or django runserver in background on Windows)
Log-Info "Starting backend process in background..."
# Check if waitress is available, otherwise use runserver
$hasWaitress = $false
try {
    & $PythonVenvExec -c "import waitress" 2>&1 | Out-Null
    $hasWaitress = $true
} catch {}

$backendArgs = @()
if ($hasWaitress) {
    $backendArgs = @("-c", "import waitress; from chikooza.wsgi import application; waitress.serve(application, host='127.0.0.1', port=8002)")
} else {
    $backendArgs = @("$ProjectRoot\manage.py", "runserver", "127.0.0.1:8002", "--noreload")
}

$gunicornLog = "$ProjectRoot\logs_gunicorn.log"
New-Item -ItemType File -Path $gunicornLog -Force | Out-Null
$backendProc = Start-Process -FilePath $PythonVenvExec -ArgumentList $backendArgs -RedirectStandardOutput $gunicornLog -RedirectStandardError $gunicornLog -WindowStyle Hidden -PassThru
$backendProc.Id | Out-File -FilePath "$ScriptDir\.django_prod.pid" -Encoding ascii

# Start Frontend preview server in background
Log-Info "Starting frontend preview in background..."
$viteLog = "$ProjectRoot\logs_vite_prod.log"
New-Item -ItemType File -Path $viteLog -Force | Out-Null
$previewArgs = @("run", "preview", "--", "--port", "5173", "--host", "127.0.0.1")
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList $previewArgs -WorkingDirectory $FrontendDir -RedirectStandardOutput $viteLog -RedirectStandardError $viteLog -WindowStyle Hidden -PassThru
$frontendProc.Id | Out-File -FilePath "$ScriptDir\.vite_prod.pid" -Encoding ascii

# Wait a moment for processes to bind
Start-Sleep -Seconds 4
Log-Success "Services restarted."

# 7. VERIFY DEPLOYMENT
Log-Info "=== PHASE 7: VERIFYING HEALTH STATUS ==="
$healthStatus = 0

# Verify Backend
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8002/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($resp.StatusCode -match "200|404|301|302") {
        Log-Success "Backend service verified at http://127.0.0.1:8002/"
    } else {
        Log-Warning "Backend returned status code: $($resp.StatusCode)"
        $healthStatus = 1
    }
} catch {
    Log-Warning "Backend service is not responding. Error: $_"
    $healthStatus = 1
}

# Verify Frontend
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Log-Success "Frontend service verified at http://127.0.0.1:5173/"
    } else {
        Log-Warning "Frontend returned status code: $($resp.StatusCode)"
        $healthStatus = 1
    }
} catch {
    Log-Warning "Frontend service is not responding. Error: $_"
    $healthStatus = 1
}

# 8. SUCCESS SUMMARY
Log-Info "=== PHASE 8: DEPLOYMENT SUMMARY ==="
if ($healthStatus -eq 0) {
    Log-Success "Windows Deployment successful! App version/commit: $commitHash"
    Log-Info "Backend URL: http://127.0.0.1:8002/"
    Log-Info "Frontend URL: http://127.0.0.1:5173/"
    
    # Auto-tail logs if interactive
    if ($Host.UI -and $Host.Name -notmatch "ServerRemoteHost") {
        Write-Host ""
        Write-Host "--------------------------------------------------" -ForegroundColor Yellow
        Log-Info "Streaming logs in real-time (press [Ctrl+C] to exit log stream; servers will keep running)..."
        Write-Host "--------------------------------------------------" -ForegroundColor Yellow
        Write-Host ""
        
        $bReader = $null
        $fReader = $null
        try {
            $bStream = New-Object System.IO.FileStream($gunicornLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $fStream = New-Object System.IO.FileStream($viteLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            
            $bReader = New-Object System.IO.StreamReader($bStream)
            $fReader = New-Object System.IO.StreamReader($fStream)
            
            # Seek to end
            [void]$bReader.ReadToEnd()
            [void]$fReader.ReadToEnd()
            
            while ($true) {
                $bLine = $bReader.ReadLine()
                if ($bLine) {
                    Write-Host "[BACKEND] $bLine" -ForegroundColor Cyan
                }
                $fLine = $fReader.ReadLine()
                if ($fLine) {
                    Write-Host "[FRONTEND] $fLine" -ForegroundColor Green
                }
                Start-Sleep -Milliseconds 150
            }
        }
        catch [System.Management.Automation.PipelineStoppedException] {
            # User pressed Ctrl+C to stop streaming
            Log-Info "Detached from log stream. Background services remain running."
        }
        catch {
            Log-Warning "Detached from log stream: $_"
        }
        finally {
            if ($bReader) { $bReader.Close() }
            if ($fReader) { $fReader.Close() }
        }
    }
} else {
    Log-Warning "Deployment completed, but health checks failed. Check running background processes for details."
    exit 1
}
