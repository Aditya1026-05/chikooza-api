# clean.ps1 - Safely cleans up build artifacts, cache directories, logs, and temporary files on Windows

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Log-Info "Starting project cleanup..."

$deepClean = $false
if ($args[0] -eq "--deep") {
    $deepClean = $true
    Log-Warning "Deep clean requested. This will remove virtual environments, local database files, and environment files."
}

# Helper to safely remove item
function Remove-Safe ($Path) {
    if (Test-Path $Path) {
        Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 1. Clean Python Caches and Temp Files
Log-Info "Removing Python cache files (__pycache__, .pyc, .pyo, .pyd)..."
Get-ChildItem -Path $Script:ProjectRoot -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Safe $_.FullName
}
Get-ChildItem -Path $Script:ProjectRoot -Include "*.pyc", "*.pyo", "*.pyd" -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Safe $_.FullName
}
Log-Success "Python caches cleaned."

# 2. Clean Test and Coverage Artifacts
Log-Info "Removing testing cache directories..."
Remove-Safe "$Script:ProjectRoot\.pytest_cache"
Remove-Safe "$Script:ProjectRoot\.coverage"
Remove-Safe "$Script:ProjectRoot\htmlcov"
Log-Success "Testing caches cleaned."

# 3. Clean Build Artifacts
Log-Info "Removing Frontend build outputs, Vite caches, and backend static files..."
Remove-Safe "$Script:FrontendDir\build"
Remove-Safe "$Script:FrontendDir\dist"
Remove-Safe "$Script:FrontendDir\.vite"
Remove-Safe "$Script:ProjectRoot\static"
Log-Success "Build artifacts cleaned."

# 4. Clean Log Directories
Log-Info "Cleaning log directories..."
if (Test-Path "$Script:ProjectRoot\logs") {
    Get-ChildItem -Path "$Script:ProjectRoot\logs" -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Safe $_.FullName
    }
}
if (Test-Path "$Script:ProjectRoot\chatbot_logs") {
    Get-ChildItem -Path "$Script:ProjectRoot\chatbot_logs" -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Safe $_.FullName
    }
}
if (Test-Path "$Script:ProjectRoot\aibot_logs") {
    Get-ChildItem -Path "$Script:ProjectRoot\aibot_logs" -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Safe $_.FullName
    }
}
Remove-Safe "$Script:ProjectRoot\logs_gunicorn.log"
Remove-Safe "$Script:ProjectRoot\logs_vite_prod.log"
Log-Success "Logs cleaned."

# 5. Deep Clean Actions
if ($deepClean -eq $true) {
    $title = "Confirm Deep Clean"
    $message = "Are you absolutely sure you want to delete databases, env files, node_modules, and virtual environment?"
    $yes = New-Object System.Management.Automation.Host.ChoiceDescription "&Yes", "Confirm deletion"
    $no = New-Object System.Management.Automation.Host.ChoiceDescription "&No", "Cancel deletion"
    $options = [System.Management.Automation.Host.ChoiceDescription[]]($yes, $no)
    $result = $host.ui.PromptForChoice($title, $message, $options, 1) # Default to No
    
    if ($result -eq 0) {
        Log-Info "Removing environment configuration files..."
        Remove-Safe "$Script:ProjectRoot\.env"
        Remove-Safe "$Script:FrontendDir\.env"
        
        Log-Info "Removing local SQLite database files..."
        Remove-Safe "$Script:ProjectRoot\db1.sqlite3"
        Remove-Safe "$Script:ProjectRoot\db1_backup.sqlite3"
        
        Log-Info "Removing virtual environment directory..."
        Remove-Safe $Script:VenvDir
        
        Log-Info "Removing frontend node_modules..."
        Remove-Safe "$Script:FrontendDir\node_modules"
        
        Log-Success "Deep clean completed."
    } else {
        Log-Info "Deep clean aborted."
    }
}

Log-Success "Project cleanup completed successfully."
