#!/usr/bin/env bash

# test.sh - Runs backend unit tests and code quality/lint checks

set -e

# Resolve scripts directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/common.sh"

log_info "Preparing to run test suite..."

# 1. Run Python Linting/Formatting checks (isort, black, flake8)
log_info "=== PHASE 1: CODE LINTING & STYLE CHECKS ==="

LINT_FAILED=0

# Isort Check
if "$VENV_DIR/bin/pip" show isort &>/dev/null; then
    log_info "Running isort import order check..."
    if ! "$VENV_DIR/bin/isort" "$PROJECT_ROOT" --check-only; then
        log_warning "isort found import ordering issues. Run: isort ."
        LINT_FAILED=1
    else
        log_success "Import sorting is correct."
    fi
else
    log_info "isort is not installed. Skipping..."
fi

# Black Check
if "$VENV_DIR/bin/pip" show black &>/dev/null; then
    log_info "Running black formatting check..."
    if ! "$VENV_DIR/bin/black" "$PROJECT_ROOT" --check; then
        log_warning "black found formatting issues. Run: black ."
        LINT_FAILED=1
    else
        log_success "Code formatting is correct."
    fi
else
    log_info "black is not installed. Skipping..."
fi

# Flake8 Check
if "$VENV_DIR/bin/pip" show flake8 &>/dev/null; then
    log_info "Running flake8 code quality audits..."
    # We ignore standard migrations and virtual environment directories
    if ! "$VENV_DIR/bin/flake8" "$PROJECT_ROOT" --exclude=venv,chikooza_env,migrations; then
        log_warning "flake8 identified syntax or formatting issues."
        LINT_FAILED=1
    else
        log_success "Flake8 style audits passed."
    fi
else
    log_info "flake8 is not installed. Skipping..."
fi

if [ $LINT_FAILED -eq 0 ]; then
    log_success "All linting audits passed successfully."
else
    log_warning "Linting checks reported issues. These do not block unit tests."
fi

# 2. Run Backend Tests
log_info "=== PHASE 2: RUNNING BACKEND UNIT TESTS ==="
cd "$PROJECT_ROOT"
if "$VENV_DIR/bin/python" manage.py test; then
    log_success "Backend unit test suite passed successfully!"
else
    log_error "Backend unit test suite failed."
    exit 1
fi

# 3. Check Frontend Tests
log_info "=== PHASE 3: FRONTEND TESTS ==="
log_info "Frontend tests are not yet configured in this project (no test script found in package.json)."
log_success "Test workflow complete."
