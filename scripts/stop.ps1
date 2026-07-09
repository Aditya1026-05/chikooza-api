# stop.ps1 - Gracefully stops development servers by PID and port check on Windows

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Log-Info "Stopping all running development services..."

# Function to stop process by PID file
function Stop-PidFile ($PidFile, $ProcessName) {
    if (Test-Path $PidFile) {
        $pidStr = (Get-Content $PidFile -ErrorAction SilentlyContinue)
        if ($pidStr -and $pidStr -match '^\d+$') {
            $pidVal = [int]$pidStr
            $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue
            if ($proc) {
                Log-Info "Stopping $ProcessName (PID: $pidVal)..."
                Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
                Log-Success "$ProcessName stopped."
            } else {
                Log-Info "$ProcessName (PID: $pidVal) is not running."
            }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# Function to stop process by Port
function Stop-PortProcess ($Port, $ProcessName) {
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
        if ($uniquePids) {
            Log-Info "Found active process(es) on port $Port ($ProcessName): $uniquePids"
            foreach ($p in $uniquePids) {
                if ($p -gt 0) {
                    $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
                    if ($proc) {
                        Log-Info "Killing process $p..."
                        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
                    }
                }
            }
            Log-Success "Processes on port $Port terminated."
        }
    }
}

# 1. Stop by PID files
Stop-PidFile "$ScriptDir\.django.pid" "Backend API"
Stop-PidFile "$ScriptDir\.vite.pid" "Frontend App"
Stop-PidFile "$ScriptDir\.django_prod.pid" "Production Backend"
Stop-PidFile "$ScriptDir\.vite_prod.pid" "Production Frontend"

# 2. Stop by Ports (safety fallback)
Stop-PortProcess 8002 "Backend"
Stop-PortProcess 5173 "Frontend"

Log-Success "Clean stop completed."
