# dev.ps1 - Starts backend & frontend development servers in the background and streams logs on Windows

$ErrorActionPreference = "Stop"

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Log-Info "Validating environment before startup..."

# Verify venv and node_modules exist
$venvPath = $Script:VenvDir
$frontendNodeModules = "$Script:FrontendDir\node_modules"

if (-not (Test-Path $venvPath) -or -not (Test-Path $frontendNodeModules)) {
    Log-Warning "Dependencies appear to be missing. Running setup.ps1 first..."
    & "$ScriptDir\setup.ps1"
}

# Ensure logs directory exists
$logDir = "$Script:ProjectRoot\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Ensure no stale processes are running
& "$ScriptDir\stop.ps1"

Log-Info "Starting development servers..."

# 1. Start Backend Django API (port 8002)
Log-Info "Launching Backend API (Django) on port 8002..."
$backendLog = "$logDir\backend.log"
# Create file if not exists
New-Item -ItemType File -Path $backendLog -Force | Out-Null

$backendArgs = @("$Script:ProjectRoot\manage.py", "runserver", "127.0.0.1:8002")
$backendProc = Start-Process -FilePath "$venvPath\Scripts\python.exe" -ArgumentList $backendArgs -WorkingDirectory $Script:ProjectRoot -RedirectStandardOutput $backendLog -RedirectStandardError $backendLog -WindowStyle Hidden -PassThru
$backendProc.Id | Out-File -FilePath "$ScriptDir\.django.pid" -Encoding ascii
Log-Success "Backend started in background (PID: $($backendProc.Id), logs: logs\backend.log)"

# 2. Start Frontend Vite Application (port 5173)
Log-Info "Launching Frontend App (Vite) on port 5173..."
$frontendLog = "$logDir\frontend.log"
# Create file if not exists
New-Item -ItemType File -Path $frontendLog -Force | Out-Null

$frontendArgs = @("run", "dev")
$frontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList $frontendArgs -WorkingDirectory $Script:FrontendDir -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog -WindowStyle Hidden -PassThru
$frontendProc.Id | Out-File -FilePath "$ScriptDir\.vite.pid" -Encoding ascii
Log-Success "Frontend started in background (PID: $($frontendProc.Id), logs: logs\frontend.log)"

# Print summary
Write-Host ""
Write-Host "--------------------------------------------------"
Log-Success "Chikooza Development Environment is RUNNING!"
Log-Info "Backend API base URL  : http://127.0.0.1:8002/"
Log-Info "Backend Admin Panel   : http://127.0.0.1:8002/admin/"
Log-Info "Frontend Application  : http://localhost:5173/ (or default Vite port)"
Log-Info "To stop all servers, press [Ctrl+C] or run: .\scripts\stop.ps1"
Write-Host "--------------------------------------------------"
Write-Host ""

# Simple log multiplexer loop
Log-Info "Streaming logs (press Ctrl+C to stop)..."

$bReader = $null
$fReader = $null

try {
    # Open streams in shared read-write mode so the background process can still write
    $bStream = New-Object System.IO.FileStream($backendLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $fStream = New-Object System.IO.FileStream($frontendLog, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    
    $bReader = New-Object System.IO.StreamReader($bStream)
    $fReader = New-Object System.IO.StreamReader($fStream)
    
    # Seek to end
    [void]$bReader.ReadToEnd()
    [void]$fReader.ReadToEnd()
    
    # Wait loop
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
    # Occurs when CTRL+C is pressed
    Log-Warning "Interruption detected. Stopping development servers..."
    & "$ScriptDir\stop.ps1"
}
catch {
    Log-Warning "Error while streaming logs: $_"
    Log-Warning "Stopping development servers..."
    & "$ScriptDir\stop.ps1"
}
finally {
    if ($bReader) { $bReader.Close() }
    if ($fReader) { $fReader.Close() }
}
