# test-all.ps1 - Orchestrates and tests the entire automated flow sequentially on Windows

$ErrorActionPreference = "Stop"

# Resolve scripts directory and import common utilities
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\common.ps1"

Log-Info "=== STARTING FULL WORKFLOW AUTOMATION HARNESS ==="

# 1. SETUP
Log-Info "PHASE 1: Setting up virtual environments and dependencies..."
& "$ScriptDir\setup.ps1"
Log-Success "Setup phase complete."

# 2. HEALTH CHECK
Log-Info "PHASE 2: Auditing system health status..."
& "$ScriptDir\health.ps1"
Log-Success "Health audit phase complete."

# 3. UNIT TESTS
Log-Info "PHASE 3: Running lint checks and test suite..."
& "$ScriptDir\test.ps1"
Log-Success "Unit testing phase complete."

# 4. CLEAN
Log-Info "PHASE 4: Cleaning temporary cache files..."
& "$ScriptDir\clean.ps1"
Log-Success "Cleanup phase complete."

# 5. BUILD
Log-Info "PHASE 5: Compiling assets and static resources..."
& "$ScriptDir\build.ps1"
Log-Success "Build compilation phase complete."

# 6. START DEVELOPMENT SERVERS (INTERACTIVE LOGS)
Log-Info "PHASE 6: Starting development servers in interactive log streaming mode..."
& "$ScriptDir\dev.ps1"

