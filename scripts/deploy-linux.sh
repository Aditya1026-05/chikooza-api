#!/usr/bin/env bash

# deploy-linux.sh - Debian/Linux deployment script
# Executes a complete, production-quality deployment workflow for Linux.

set -e

# ANSI escape codes for coloring
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine project root and subdirectories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." &>/dev/null && pwd)"
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$PROJECT_ROOT/chikooza-ui"

# Define Virtual Environment paths
VENV_DIR=""
if [ -d "$PROJECT_ROOT/venv" ]; then
    VENV_DIR="$PROJECT_ROOT/venv"
elif [ -d "$PROJECT_ROOT/chikooza_env" ]; then
    VENV_DIR="$PROJECT_ROOT/chikooza_env"
else
    VENV_DIR="$PROJECT_ROOT/venv"
fi

get_timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo -e "$(get_timestamp) [${BLUE}INFO${NC}] $1"
}

log_success() {
    echo -e "$(get_timestamp) [${GREEN}SUCCESS${NC}] $1"
}

log_warning() {
    echo -e "$(get_timestamp) [${YELLOW}WARNING${NC}] $1"
}

log_error() {
    echo -e "$(get_timestamp) [${RED}ERROR${NC}] $1" >&2
}

# Function to read and export variables from .env
load_env() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        log_info "Loading environment variables from $env_file..."
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
                continue
            fi
            if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local val="${BASH_REMATCH[2]}"
                key=$(echo "$key" | xargs)
                val=$(echo "$val" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                if [ -z "${!key}" ]; then
                    export "$key"="$val"
                fi
            fi
        done < "$env_file"
    fi
}

# 1. SETUP & VALIDATE SYSTEM
log_info "=== PHASE 1: SETUP & VALIDATE SYSTEM ==="

# Check OS suitability
OS_NAME="$(uname -s)"
if [ "$OS_NAME" != "Linux" ]; then
    log_error "This script is designed for Linux. Detected OS: $OS_NAME. Please run deploy-mac.sh instead."
    exit 1
fi
log_success "Operating system validated: Linux ($OS_NAME)"

# Check Git
if ! command -v git &> /dev/null; then
    log_error "Git is not installed. Please install Git and try again."
    exit 1
fi
log_success "Git verified."

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed. Please install Python 3.11+ and try again."
    exit 1
fi
PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PYTHON_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    log_error "Python version must be 3.11 or higher. Detected: $PYTHON_VERSION"
    exit 1
fi
log_success "Python version verified: $PYTHON_VERSION"

# Check Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi
NODE_VERSION="$(node -v | tr -d 'v')"
NODE_MAJOR="$(echo "$NODE_VERSION" | cut -d. -f1)"
if [ "$NODE_MAJOR" -lt 18 ]; then
    log_error "Node.js version must be 18 or higher. Detected: $NODE_VERSION"
    exit 1
fi
log_success "Node.js version verified: $NODE_VERSION"

# Load Env Configs
load_env "$PROJECT_ROOT/.env"
load_env "$FRONTEND_DIR/.env"

# 2. PULL LATEST CODE
log_info "=== PHASE 2: PULLING LATEST CODE ==="
CURRENT_BRANCH="$(git branch --show-current)"
log_info "Syncing repository branch: $CURRENT_BRANCH"
git fetch origin "$CURRENT_BRANCH"
git pull origin "$CURRENT_BRANCH"
COMMIT_HASH="$(git rev-parse --short HEAD)"
log_success "Code updated to commit: $COMMIT_HASH"

# 3. INSTALL DEPENDENCIES
log_info "=== PHASE 3: INSTALLING DEPENDENCIES ==="
# Ensure venv exists
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating missing virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

log_info "Updating backend packages..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
log_success "Backend packages installed."

log_info "Updating frontend packages..."
cd "$FRONTEND_DIR"
npm ci || npm install
cd "$PROJECT_ROOT"
log_success "Frontend packages installed."

# 4. RUN DATABASE MIGRATIONS
log_info "=== PHASE 4: RUNNING DATABASE MIGRATIONS ==="
log_info "Checking database connectivity..."
DB_CHECK_CMD="import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"
if "$VENV_DIR/bin/python" -c "$DB_CHECK_CMD" &> /dev/null; then
    log_success "Database connectivity established."
    log_info "Applying migrations..."
    "$VENV_DIR/bin/python" "$PROJECT_ROOT/manage.py" migrate --no-input
    log_success "Database migrations completed."
else
    log_error "Failed to connect to the database. Verify DATABASE_URL in .env or SQLite file permissions."
    exit 1
fi

# 5. BUILD ASSETS
log_info "=== PHASE 5: BUILDING STATIC ASSETS ==="
log_info "Collecting Django static files..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/manage.py" collectstatic --no-input
log_success "Django static files collected."

log_info "Compiling frontend assets via Vite..."
cd "$FRONTEND_DIR"
npm run build
cd "$PROJECT_ROOT"
log_success "Frontend compilation complete."

# 6. RESTART SERVICES (Linux Systemd or background fallback)
log_info "=== PHASE 6: RESTARTING SERVICES ==="

# We check if systemctl is available and systemd is pid 1
USE_SYSTEMD=false
if command -v systemctl &>/dev/null && [ "$(ps -p 1 -o comm=)" = "systemd" ]; then
    USE_SYSTEMD=true
fi

# Determine service name from env (default to 'gunicorn' and 'nginx')
BACKEND_SERVICE="${BACKEND_SERVICE_NAME:-gunicorn}"
FRONTEND_SERVICE="${FRONTEND_SERVICE_NAME:-nginx}"

if [ "$USE_SYSTEMD" = true ]; then
    log_info "Systemd detected. Attempting to restart services via systemctl..."
    
    # Restart Gunicorn service
    if systemctl list-units --state=active | grep -q "$BACKEND_SERVICE"; then
        log_info "Restarting backend systemd service ($BACKEND_SERVICE)..."
        sudo systemctl restart "$BACKEND_SERVICE"
        log_success "Backend service restarted."
    else
        log_warning "Systemd backend service '$BACKEND_SERVICE' not active or not found."
    fi
    
    # Reload or restart Nginx service
    if systemctl list-units --state=active | grep -q "$FRONTEND_SERVICE"; then
        log_info "Reloading frontend systemd service ($FRONTEND_SERVICE)..."
        sudo systemctl reload "$FRONTEND_SERVICE" || sudo systemctl restart "$FRONTEND_SERVICE"
        log_success "Frontend service reloaded/restarted."
    else
        log_warning "Systemd frontend service '$FRONTEND_SERVICE' not active or not found."
    fi
else
    log_info "Systemd not detected. Falling back to background process manager..."
    
    BACKEND_PID=$(lsof -t -i :8002 || true)
    FRONTEND_PID=$(lsof -t -i :5173 || true)

    if [ -n "$BACKEND_PID" ]; then
        log_info "Stopping active backend process (PID: $BACKEND_PID)..."
        kill -15 $BACKEND_PID || kill -9 $BACKEND_PID
    fi

    if [ -n "$FRONTEND_PID" ]; then
        log_info "Stopping active frontend process (PID: $FRONTEND_PID)..."
        kill -15 $FRONTEND_PID || kill -9 $FRONTEND_PID
    fi

    log_info "Starting services in background..."
    # Start Backend in detached subshell ignoring SIGINT/SIGTERM
    (
        trap '' SIGINT SIGTERM
        exec "$VENV_DIR/bin/gunicorn" chikooza.wsgi --bind 127.0.0.1:8002 --workers 3 > "$PROJECT_ROOT/logs_gunicorn.log" 2>&1 </dev/null
    ) &
    echo $! > "$SCRIPT_DIR/.django_prod.pid"

    # Start Frontend preview in detached subshell ignoring SIGINT/SIGTERM
    (
        trap '' SIGINT SIGTERM
        cd "$FRONTEND_DIR"
        exec npm run preview -- --port 5173 --host 127.0.0.1 > "$PROJECT_ROOT/logs_vite_prod.log" 2>&1 </dev/null
    ) &
    echo $! > "$SCRIPT_DIR/.vite_prod.pid"
    cd "$PROJECT_ROOT"
    
    
    sleep 3
    log_success "Services restarted."
fi

# 7. VERIFY DEPLOYMENT
log_info "=== PHASE 7: VERIFYING HEALTH STATUS ==="
HEALTH_STATUS=0

# Verify Backend
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/ | grep -q "200\|404\|301\|302"; then
    log_success "Backend service verified at http://127.0.0.1:8002/"
else
    log_warning "Backend service is not responding or returned error code."
    HEALTH_STATUS=1
fi

# Verify Frontend
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/ | grep -q "200"; then
    log_success "Frontend service verified at http://127.0.0.1:5173/"
else
    log_warning "Frontend service is not responding."
    HEALTH_STATUS=1
fi

# 8. SUCCESS SUMMARY
log_info "=== PHASE 8: DEPLOYMENT SUMMARY ==="
if [ $HEALTH_STATUS -eq 0 ]; then
    log_success "Linux Deployment successful! App version/commit: $COMMIT_HASH"
    log_info "Backend URL: http://127.0.0.1:8002/"
    log_info "Frontend URL: http://127.0.0.1:5173/"
    
    # Auto-tail logs if running in an interactive terminal
    if [ -t 1 ]; then
        echo -e "\n--------------------------------------------------"
        log_info "Streaming logs in real-time (press [Ctrl+C] to exit log stream; servers will keep running)..."
        echo -e "--------------------------------------------------\n"
        if [ "$USE_SYSTEMD" = true ]; then
            sudo journalctl -u "$BACKEND_SERVICE" -f -n 20 || true
        else
            tail -f "$PROJECT_ROOT/logs_gunicorn.log" "$PROJECT_ROOT/logs_vite_prod.log" || true
        fi
    fi
else
    log_warning "Deployment completed, but health checks failed. Check Gunicorn/Nginx system logs or local logs."
    exit 1
fi

