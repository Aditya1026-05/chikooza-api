# common.ps1 - Shared utilities and configurations for Chikooza PowerShell scripts

$Script:MyDirPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script:ProjectRoot = (Get-Item "$MyDirPath\..").FullName
$Script:BackendDir = $Script:ProjectRoot
$Script:FrontendDir = "$Script:ProjectRoot\chikooza-ui"

# Define Virtual Environment paths
if (Test-Path "$Script:ProjectRoot\venv") {
    $Script:VenvDir = "$Script:ProjectRoot\venv"
} elseif (Test-Path "$Script:ProjectRoot\chikooza_env") {
    $Script:VenvDir = "$Script:ProjectRoot\chikooza_env"
} else {
    $Script:VenvDir = "$Script:ProjectRoot\venv"
}

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

# Function to read and set variables from a .env file
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
    } else {
        Log-Warning "Environment file not found: $EnvFilePath"
    }
}

Export-ModuleMember -Function Get-Timestamp, Log-Info, Log-Success, Log-Warning, Log-Error, Load-Env -Variable MyDirPath, ProjectRoot, BackendDir, FrontendDir, VenvDir
