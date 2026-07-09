#!/usr/bin/env bash

# test-all.sh - Orchestrates and tests the entire automated flow sequentially

set -e

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "=== STARTING FULL WORKFLOW AUTOMATION HARNESS ==="

# 1. SETUP
log_info "PHASE 1: Setting up virtual environments and dependencies..."
bash "$SCRIPT_DIR/setup.sh"
log_success "Setup phase complete."

# 2. HEALTH CHECK
log_info "PHASE 2: Auditing system health status..."
bash "$SCRIPT_DIR/health.sh"
log_success "Health audit phase complete."

# 3. UNIT TESTS
log_info "PHASE 3: Running lint checks and test suite..."
bash "$SCRIPT_DIR/test.sh"
log_success "Unit testing phase complete."

# 4. CLEAN
log_info "PHASE 4: Cleaning temporary cache files..."
bash "$SCRIPT_DIR/clean.sh"
log_success "Cleanup phase complete."

# 5. BUILD
log_info "PHASE 5: Compiling assets and static resources..."
bash "$SCRIPT_DIR/build.sh"
log_success "Build compilation phase complete."

# 6. START DEVELOPMENT SERVERS (INTERACTIVE LOGS)
log_info "PHASE 6: Starting development servers in interactive log streaming mode..."
bash "$SCRIPT_DIR/dev.sh"

