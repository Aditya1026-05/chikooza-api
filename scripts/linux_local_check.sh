#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is required."
command -v npm >/dev/null 2>&1 || fail "npm is required for the frontend build."

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

log "Creating Python virtual environment"
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip

log "Installing backend dependencies"
venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  log "Creating local backend .env from .env.example"
  cp .env.example .env
fi

log "Running Django checks"
venv/bin/python manage.py check

if [ "${RUN_TESTS:-true}" != "false" ]; then
  log "Running backend tests"
  venv/bin/python manage.py test
fi

log "Installing frontend dependencies and building React app"
cd chikooza-ui
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi
npm run build

log "Linux local check completed"
