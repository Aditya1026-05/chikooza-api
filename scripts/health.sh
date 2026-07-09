#!/usr/bin/env bash

# health.sh - Checks the health and status of the entire development ecosystem

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

load_env "$PROJECT_ROOT/.env"

log_info "Running system health checks..."
echo "=============================================="

# Helper to format status rows
print_status() {
    local label="$1"
    local status="$2"
    local detail="$3"
    
    if [ "$status" == "OK" ]; then
        echo -e "[${GREEN}OK${NC}]   $label - $detail"
    elif [ "$status" == "WARN" ]; then
        echo -e "[${YELLOW}WARN${NC}] $label - $detail"
    else
        echo -e "[${RED}FAIL${NC}] $label - $detail"
    fi
}

# 1. Check Python
if command -v python3 &>/dev/null; then
    PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
    print_status "Python Environment" "OK" "Python $PYTHON_VERSION detected"
else
    print_status "Python Environment" "FAIL" "Python 3 is not installed or not in PATH"
fi

# 2. Check Node.js
if command -v node &>/dev/null; then
    NODE_VERSION="$(node -v)"
    print_status "Node.js Environment" "OK" "Node $NODE_VERSION detected"
else
    print_status "Node.js Environment" "FAIL" "Node.js is not installed or not in PATH"
fi

# 3. Check virtualenv
if [ -d "$VENV_DIR" ]; then
    if [ -f "$VENV_DIR/bin/python" ]; then
        print_status "Virtual Environment" "OK" "Active at $VENV_DIR"
    else
        print_status "Virtual Environment" "FAIL" "Directory exists but python executable is missing"
    fi
else
    print_status "Virtual Environment" "FAIL" "No virtualenv found at $VENV_DIR"
fi

# 4. Check Frontend node_modules
if [ -d "$FRONTEND_DIR/node_modules" ]; then
    print_status "Frontend Node Modules" "OK" "node_modules installed in $FRONTEND_DIR"
else
    print_status "Frontend Node Modules" "WARN" "node_modules missing in $FRONTEND_DIR"
fi

# 5. Check configuration files
if [ -f "$PROJECT_ROOT/.env" ]; then
    print_status "Backend Config (.env)" "OK" "Loaded successfully"
else
    print_status "Backend Config (.env)" "FAIL" "Missing in $PROJECT_ROOT"
fi

if [ -f "$FRONTEND_DIR/.env" ]; then
    print_status "Frontend Config (.env)" "OK" "Loaded successfully"
else
    print_status "Frontend Config (.env)" "WARN" "Missing in $FRONTEND_DIR"
fi

# 6. Check Database Connectivity
DB_CHECK_CMD="import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.db import connections; connections['default'].cursor()"
if [ -f "$VENV_DIR/bin/python" ] && "$VENV_DIR/bin/python" -c "$DB_CHECK_CMD" &> /dev/null; then
    # Get DB details
    DB_ENGINE="$("$VENV_DIR/bin/python" -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chikooza.settings'); django.setup(); from django.conf import settings; print(settings.DATABASES['default']['ENGINE'].split('.')[-1])")"
    print_status "Database Connection" "OK" "Connected ($DB_ENGINE)"
else
    print_status "Database Connection" "FAIL" "Cannot connect to database"
fi

# 7. Check Ports & Endpoints
# Check Backend port 8002
BACKEND_ACTIVE=false
if command -v lsof &>/dev/null && lsof -i :8002 -sTCP:LISTEN >/dev/null; then
    BACKEND_ACTIVE=true
elif command -v netstat &>/dev/null && netstat -an | grep 8002 | grep LISTEN >/dev/null; then
    BACKEND_ACTIVE=true
fi

if [ "$BACKEND_ACTIVE" == "true" ]; then
    # Test endpoint
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8002/admin/ | grep -q "200\|404\|301\|302"; then
        print_status "Backend Port 8002" "OK" "Listening and responsive"
    else
        print_status "Backend Port 8002" "WARN" "Listening, but returned connection/HTTP error"
    fi
else
    print_status "Backend Port 8002" "FAIL" "Backend is NOT running"
fi

# Check Frontend port 5173 (Vite default)
FRONTEND_ACTIVE=false
if command -v lsof &>/dev/null && lsof -i :5173 -sTCP:LISTEN >/dev/null; then
    FRONTEND_ACTIVE=true
elif command -v netstat &>/dev/null && netstat -an | grep 5173 | grep LISTEN >/dev/null; then
    FRONTEND_ACTIVE=true
fi

if [ "$FRONTEND_ACTIVE" == "true" ]; then
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173/ | grep -q "200"; then
        print_status "Frontend Port 5173" "OK" "Listening and responsive (Vite)"
    else
        print_status "Frontend Port 5173" "WARN" "Listening, but returned HTTP error"
    fi
else
    print_status "Frontend Port 5173" "FAIL" "Frontend is NOT running"
fi

# 8. Check Groq API
if [ -n "$GROQ_API_KEY" ]; then
    print_status "AI / Groq API Key" "OK" "Configured (value length: ${#GROQ_API_KEY} chars)"
else
    print_status "AI / Groq API Key" "WARN" "Not configured (RAG will run in fallback retrieval-only mode)"
fi

echo "=============================================="
log_info "Health check execution finished."
