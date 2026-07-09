#!/usr/bin/env bash

# build.sh - Prepares the application for production deployment

set -e

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Preparing application for production build..."

# 1. Verify venv
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtual environment not found. Please run scripts/setup.sh first."
    exit 1
fi

# 2. Django Production Preparation
log_info "=== Backend Production Verification & Preparation ==="

# Check Django deployment settings
log_info "Running Django deployment checks..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/manage.py" check --deploy || log_warning "Django deployment check flagged recommendations (please review)."

# Collect static assets
log_info "Collecting Django static files..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/manage.py" collectstatic --no-input
log_success "Static files successfully collected into root 'static' directory."

# 3. Frontend Production Build
log_info "=== Frontend Production Compilation ==="
if [ -d "$FRONTEND_DIR" ]; then
    log_info "Compiling frontend assets via Vite..."
    cd "$FRONTEND_DIR"
    npm run build
    cd "$PROJECT_ROOT"
    log_success "Frontend compiled successfully (output directory: $FRONTEND_DIR/build/)."
else
    log_error "Frontend directory not found at $FRONTEND_DIR"
    exit 1
fi

log_success "Build workflow successfully completed! Assets are ready for production."
