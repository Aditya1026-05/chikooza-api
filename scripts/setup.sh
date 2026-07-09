#!/usr/bin/env bash

# setup.sh - Initial setup, dependency installation, and validation

set -e

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Starting environment setup..."

# 1. Detect OS
OS_NAME="$(uname -s)"
log_info "Detected Operating System: $OS_NAME"

# 2. Check Git
if ! command -v git &> /dev/null; then
    log_error "Git is not installed. Please install Git and try again."
    exit 1
fi
log_success "Git is available: $(git --version)"

# 3. Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.11+ and try again."
        exit 1
    else
        PYTHON_EXEC="python"
    fi
else
    PYTHON_EXEC="python3"
fi

PYTHON_VERSION="$($PYTHON_EXEC -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_MAJOR="$($PYTHON_EXEC -c 'import sys; print(sys.version_info.major)')"
PYTHON_MINOR="$($PYTHON_EXEC -c 'import sys; print(sys.version_info.minor)')"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    log_error "Python version must be 3.11 or higher. Detected: $PYTHON_VERSION"
    exit 1
fi
log_success "Python is available (version $PYTHON_VERSION): $(which $PYTHON_EXEC)"

# 4. Check Node.js
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
log_success "Node.js is available (version $NODE_VERSION): $(which node)"

# 5. Check NPM
if ! command -v npm &> /dev/null; then
    log_error "NPM is not installed. Please install NPM and try again."
    exit 1
fi
log_success "NPM is available: $(npm -v)"

# 6. Virtual Environment Setup
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating Python virtual environment in $VENV_DIR..."
    $PYTHON_EXEC -m venv "$VENV_DIR"
fi
log_success "Python virtual environment verified at: $VENV_DIR"

log_info "Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip

log_info "Installing Python dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
log_success "Backend dependencies installed successfully."

# 7. Install Frontend Dependencies
log_info "Installing Frontend dependencies in $FRONTEND_DIR..."
if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    npm install
    cd "$PROJECT_ROOT"
    log_success "Frontend dependencies installed successfully."
else
    log_error "Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

# 8. Setup Environment Files
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_info "Root .env not found. Creating from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    log_success "Root .env file created."
else
    log_info "Root .env file already exists."
fi

if [ ! -f "$FRONTEND_DIR/.env" ]; then
    log_info "Frontend .env not found. Creating from .env.example..."
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
    log_success "Frontend .env file created."
else
    log_info "Frontend .env file already exists."
fi

load_env "$PROJECT_ROOT/.env"

if [ -z "$GROQ_API_KEY" ]; then
    log_warning "GROQ_API_KEY is not configured in your .env file. AI/RAG features will run with fallback retrieve-only answers."
fi

# 9. Verify Database Connectivity & Apply Migrations
log_info "Checking database connectivity..."
DB_CHECK_CMD="import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"

if "$VENV_DIR/bin/python" -c "$DB_CHECK_CMD" &> /dev/null; then
    log_success "Database connectivity verified."
    log_info "Applying database migrations..."
    "$VENV_DIR/bin/python" "$PROJECT_ROOT/manage.py" migrate
    log_success "Database migrations successfully applied."
else
    log_error "Failed to connect to the database. Please check your DATABASE_URL or write access to the SQLite file."
    exit 1
fi

log_success "Setup workflow completed successfully!"
