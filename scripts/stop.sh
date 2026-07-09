#!/usr/bin/env bash

# stop.sh - Gracefully stops development servers by PID and port check

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Stopping all running development services..."

# Function to stop process by PID file
stop_pid_file() {
    local pid_file="$1"
    local process_name="$2"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "Stopping $process_name (PID: $pid)..."
            kill "$pid" || kill -9 "$pid"
            log_success "$process_name stopped."
        else
            log_info "$process_name (PID: $pid) is not running."
        fi
        rm -f "$pid_file"
    fi
}

# Function to stop process by Port
stop_port() {
    local port="$1"
    local process_name="$2"
    
    # Try to find PID listening on port
    local pids=""
    if command -v lsof &>/dev/null; then
        pids=$(lsof -t -i :"$port" || true)
    elif command -v fuser &>/dev/null; then
        pids=$(fuser "$port"/tcp 2>/dev/null || true)
    fi
    
    if [ -n "$pids" ]; then
        log_info "Found active process(es) on port $port ($process_name): $pids"
        for pid in $pids; do
            if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
                log_info "Killing process $pid..."
                kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
            fi
        done
        log_success "Processes on port $port terminated."
    fi
}

# 1. Stop by PID files
stop_pid_file "$SCRIPT_DIR/.django.pid" "Backend API"
stop_pid_file "$SCRIPT_DIR/.vite.pid" "Frontend App"
stop_pid_file "$SCRIPT_DIR/.django_prod.pid" "Production Backend"
stop_pid_file "$SCRIPT_DIR/.vite_prod.pid" "Production Frontend"

# 2. Stop by Ports (as safety fallback)
stop_port 8002 "Backend"
stop_port 5173 "Frontend"

log_success "Clean stop completed."
