#!/usr/bin/env bash

# clean.sh - Safely cleans up build artifacts, cache directories, logs, and temporary files

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Starting project cleanup..."

DEEP_CLEAN=false
if [ "$1" == "--deep" ]; then
    DEEP_CLEAN=true
    log_warning "Deep clean requested. This will remove virtual environments, local database files, and environment files."
fi

# 1. Clean Python Caches and Temp Files
log_info "Removing Python cache files (__pycache__, .pyc, .pyo, .pyd)..."
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyd" -delete 2>/dev/null || true
log_success "Python caches cleaned."

# 2. Clean Test and Coverage Artifacts
log_info "Removing testing cache directories..."
rm -rf "$PROJECT_ROOT/.pytest_cache" "$PROJECT_ROOT/.coverage" "$PROJECT_ROOT/htmlcov" 2>/dev/null || true
log_success "Testing caches cleaned."

# 3. Clean Build Artifacts
log_info "Removing Frontend build outputs, Vite caches, and backend static files..."
rm -rf "$FRONTEND_DIR/build" "$FRONTEND_DIR/dist" "$FRONTEND_DIR/.vite" "$PROJECT_ROOT/static" 2>/dev/null || true
log_success "Build artifacts cleaned."

# 4. Clean Log Directories
log_info "Cleaning log directories..."
rm -rf "$PROJECT_ROOT/logs"/*.log "$PROJECT_ROOT/chatbot_logs"/*.log "$PROJECT_ROOT/aibot_logs"/*.log 2>/dev/null || true
rm -rf "$PROJECT_ROOT"/logs_gunicorn.log "$PROJECT_ROOT"/logs_vite_prod.log 2>/dev/null || true
log_success "Logs cleaned."

# 5. Deep Clean Actions
if [ "$DEEP_CLEAN" = true ]; then
    read -p "Are you absolutely sure you want to delete database and environment files? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing environment configuration files..."
        rm -f "$PROJECT_ROOT/.env" "$FRONTEND_DIR/.env" 2>/dev/null || true
        
        log_info "Removing local SQLite database files..."
        rm -f "$PROJECT_ROOT/db1.sqlite3" "$PROJECT_ROOT/db1_backup.sqlite3" 2>/dev/null || true
        
        log_info "Removing virtual environment directory..."
        rm -rf "$VENV_DIR" 2>/dev/null || true
        
        log_info "Removing frontend node_modules..."
        rm -rf "$FRONTEND_DIR/node_modules" 2>/dev/null || true
        
        log_success "Deep clean completed."
    else
        log_info "Deep clean aborted."
    fi
fi

log_success "Project cleanup completed successfully."
