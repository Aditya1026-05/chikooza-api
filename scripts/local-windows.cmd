@echo off
setlocal EnableExtensions

set "GIT_BASH="
set "PROJECT_DIR=%~dp0.."

if exist "%ProgramFiles%\Git\bin\bash.exe" set "GIT_BASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined GIT_BASH if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "GIT_BASH=%LocalAppData%\Programs\Git\bin\bash.exe"
if not defined GIT_BASH if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "GIT_BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"

if not defined GIT_BASH (
    where winget.exe >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Git Bash is required and WinGet is unavailable.
        echo Install Git for Windows, then run this command again.
        exit /b 1
    )

    echo [INFO] Git Bash is missing. Installing Git for Windows for the current user.
    winget.exe install --id Git.Git --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [ERROR] Git for Windows could not be installed without elevation.
        echo Install Git for Windows manually, then run this command again.
        exit /b 1
    )

    if exist "%ProgramFiles%\Git\bin\bash.exe" set "GIT_BASH=%ProgramFiles%\Git\bin\bash.exe"
    if not defined GIT_BASH if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "GIT_BASH=%LocalAppData%\Programs\Git\bin\bash.exe"
)

if not defined GIT_BASH (
    echo [ERROR] Git was installed, but Git Bash is not visible yet.
    echo Open a new Command Prompt and run this command again.
    exit /b 1
)

pushd "%PROJECT_DIR%" >nul
"%GIT_BASH%" "./scripts/local.sh" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%
