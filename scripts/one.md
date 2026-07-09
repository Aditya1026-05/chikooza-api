# Chikooza Automation Scripts Cheatsheet

This cheatsheet provides a simple, direct reference for running all developer automation and deployment scripts.

## 💡 Purpose: Development vs. Deployment

Before running any script, choose the mode that fits your current task:

*   **Deploy Scripts (`deploy-mac.sh`, `deploy-linux.sh`, `deploy.ps1`)**: Use these when you want to **launch the app to run permanently** (e.g., testing production-ready builds or deploying on a live host). The servers run in the background (as daemons), and pressing `Ctrl+C` only detaches you from the log stream (the app stays online).
*   **Harness Scripts (`test-all.sh`, `test-all.ps1`)**: Use these when you are doing **local coding, testing, and developer validation**. It runs setup, styles check, unit tests, asset builds, and starts the development servers interactively. Pressing `Ctrl+C` immediately stops the servers to free up port resources.

---

## 🚀 The Single-Command Deployment Workflows (Start here)

For local production checks or live hosting, you only need to run a single command depending on your operating system.

> [!IMPORTANT]
> **Managing the Live App & Logs during Deployment:**
> *   **How to stop watching logs**: Press **`Ctrl+C`**. This exits the log viewer back to your command line, but **leaves the application running** in the background.
> *   **How to completely stop the app**: Run the stop script: `./scripts/stop.sh` (or `.\scripts\stop.ps1` on Windows).


### 🍎 macOS Local Deployment
Executes code updates, dependency setups, database migrations, asset builds, starts production servers in the background, and streams logs:
```bash
./scripts/deploy-mac.sh
```
*   **Detaching Logs**: Press **`Ctrl+C`** to exit the log viewer. The application **keeps running in the background**.
*   **Stopping Servers**: Run `./scripts/stop.sh` to turn off background servers completely.

### 🐧 Debian/Linux Server Deployment
Pulls latest changes, runs migrations, builds resources, and restarts production services (`gunicorn` and `nginx` systemd services, with background daemon fallback):
```bash
./scripts/deploy-linux.sh
```
*   **Detaching Logs**: Press **`Ctrl+C`** to exit the log viewer. The application **keeps running in the background**.
*   **Stopping Servers**: Run `./scripts/stop.sh` to turn off background servers completely.

### 🪟 Windows Local Deployment
Executes updates, updates virtualenvs, applies migrations, builds Vite templates, starts backend and frontend preview servers in the background, and streams logs:
```powershell
.\scripts\deploy.ps1
```
*   **Detaching Logs**: Press **`Ctrl+C`** to exit the log viewer. The application **keeps running in the background**.
*   **Stopping Servers**: Run `.\scripts\stop.ps1` to turn off background servers completely.

---

## 🛠️ Individual Script Reference (Alphabetical)

Each script is designed to run the same logical workflow on macOS/Linux (using Bash `.sh` files) and Windows (using PowerShell `.ps1` files). Run all commands from the project root directory.

### 1. `build.sh` & `build.ps1` (Compile Production Assets)
Validates Django configuration settings for deploy readiness, compiles static Django files, and bundles frontend files for production.
*   **macOS / Linux**: `./scripts/build.sh`
*   **Windows**: `.\scripts\build.ps1`

### 2. `clean.sh` & `clean.ps1` (Purge Caches & Temp Files)
Safely deletes python compilation files (`__pycache__`), build directories, logs, and testing caches.
*   **macOS / Linux**: `./scripts/clean.sh`
*   **Windows**: `.\scripts\clean.ps1`
*   **Deep Clean** (Also deletes virtualenv directories, `.env` files, and local SQLite databases):
    *   macOS / Linux: `./scripts/clean.sh --deep`
    *   Windows: `.\scripts\clean.ps1 --deep`

### 3. `common.sh` & `common.ps1` (Shared Configuration Helper)
Stores common environment loaders, directory paths, and logging utilities. It is imported by the other scripts and is **not** run directly.

### 4. `dev.sh` & `dev.ps1` (Interactive Development Servers)
Clears stale process ports and launches Django API (port `8002`) and Vite dev server (port `5173`) in background logs-streaming mode.
*   **macOS / Linux**: `./scripts/dev.sh`
*   **Windows**: `.\scripts\dev.ps1`
*   **Interruption Trap**: Pressing **`Ctrl+C`** in this mode **will stop and clean up all servers** automatically.

### 5. `health.sh` & `health.ps1` (Ecosystem Health Check)
Audits Python and Node versions, database connection paths, port availability, and AI key configurations, printing a status report list.
*   **macOS / Linux**: `./scripts/health.sh`
*   **Windows**: `.\scripts\health.ps1`

### 6. `setup.sh` & `setup.ps1` (Environment Bootstrap)
Validates system prerequisites, initializes virtualenvs (`venv` or `chikooza_env`), installs python modules and frontend packages, configures `.env` copies, and runs migrations.
*   **macOS / Linux**: `./scripts/setup.sh`
*   **Windows**: `.\scripts\setup.ps1`

### 7. `stop.sh` & `stop.ps1` (Graceful Process Termination)
Gracefully terminates Gunicorn, Vite, Waitress, or Django dev servers using tracking process PIDs and scanning port bindings (8002, 5173) to ensure a clean exit.
*   **macOS / Linux**: `./scripts/stop.sh`
*   **Windows**: `.\scripts\stop.ps1`

### 8. `test.sh` & `test.ps1` (Style Checker & Unit Tests)
Runs import sorting (`isort`), code formatting checks (`black`), style checkers (`flake8`), and the backend Django unit testing suite (70 tests).
*   **macOS / Linux**: `./scripts/test.sh`
*   **Windows**: `.\scripts\test.ps1`

### 9. `test-all.sh` & `test-all.ps1` (Complete Development Harness)
Runs the entire dev workflow in one go (Setup → Health → Test → Clean → Build → Interactive Dev Startup).
*   **macOS / Linux**: `./scripts/test-all.sh`
*   **Windows**: `.\scripts\test-all.ps1`
*   **Interruption Trap**: Pressing **`Ctrl+C`** in this mode **will stop and clean up all servers** automatically.
