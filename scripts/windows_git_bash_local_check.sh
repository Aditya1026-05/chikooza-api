#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

command -v npm >/dev/null 2>&1 || fail "npm is required. Install Node.js first."

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

log "Creating Python virtual environment"
if command -v py >/dev/null 2>&1; then
  py -3 -m venv venv
elif command -v python >/dev/null 2>&1; then
  python -m venv venv
else
  fail "Python is required. Install Python 3 and add it to PATH."
fi

PYTHON_EXE="venv/Scripts/python.exe"
PIP_EXE="venv/Scripts/pip.exe"

if [ ! -x "$PYTHON_EXE" ]; then
  fail "Could not find $PYTHON_EXE. Use PowerShell script on native Windows, or run this inside Git Bash/WSL."
fi

"$PYTHON_EXE" -m pip install --upgrade pip

log "Installing backend dependencies"
"$PIP_EXE" install -r requirements.txt

if [ ! -f .env ]; then
  log "Creating local backend .env from .env.example"
  cp .env.example .env
fi

log "Running Django checks"
"$PYTHON_EXE" manage.py check

if [ "${RUN_TESTS:-true}" != "false" ]; then
  log "Running backend tests"
  "$PYTHON_EXE" manage.py test
fi

log "Installing frontend dependencies and building React app"
cd chikooza-ui
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi
npm run build

log "Windows Git Bash local check completed"
