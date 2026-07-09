#!/usr/bin/env bash

# dev.sh - Starts backend & frontend development servers in the background and streams logs

set -e

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Validating environment before startup..."

# Verify venv and node_modules exist
if [ ! -d "$VENV_DIR" ] || [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log_warning "Dependencies appear to be missing. Running setup.sh first..."
    bash "$SCRIPT_DIR/setup.sh"
fi

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Ensure no stale processes are running
bash "$SCRIPT_DIR/stop.sh"

log_info "Starting development servers..."

# 1. Start Backend Django API (port 8002)
log_info "Launching Backend API (Django) on port 8002..."
cd "$PROJECT_ROOT"
nohup "$VENV_DIR/bin/python" -u manage.py runserver 8002 > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/.django.pid"
log_success "Backend started in background (PID: $BACKEND_PID, logs: logs/backend.log)"

# 2. Start Frontend Vite Application (port 5173)
log_info "Launching Frontend App (Vite) on port 5173..."
cd "$FRONTEND_DIR"
# Vite defaults to 5173 or port from npm script
nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$SCRIPT_DIR/.vite.pid"
cd "$PROJECT_ROOT"
log_success "Frontend started in background (PID: $FRONTEND_PID, logs: logs/frontend.log)"

# Print summary
echo -e "\n--------------------------------------------------"
log_success "Chikooza Development Environment is RUNNING!"
log_info "Backend API base URL  : http://127.0.0.1:8002/"
log_info "Backend Admin Panel   : http://127.0.0.1:8002/admin/"
log_info "Frontend Application  : http://localhost:5173/ (or default Vite port)"
log_info "To stop all servers, press [Ctrl+C] or run: ./scripts/stop.sh"
echo -e "--------------------------------------------------\n"

# Setup trap to stop services on script termination (e.g. CTRL+C)
cleanup() {
    echo -e "\n"
    log_warning "Interruption detected. Stopping development servers..."
    bash "$SCRIPT_DIR/stop.sh"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Tail both logs simultaneously
log_info "Streaming logs (press Ctrl+C to stop)..."
tail -n 20 -f "$PROJECT_ROOT/logs/backend.log" "$PROJECT_ROOT/logs/frontend.log" 2>/dev/null || true

# Wait for background jobs
wait
