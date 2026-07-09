#!/usr/bin/env bash

# common.sh - Shared utilities and configurations for Chikooza scripts

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." &>/dev/null && pwd)"
BACKEND_DIR="$PROJECT_ROOT"
FRONTEND_DIR="$PROJECT_ROOT/chikooza-ui"

# Define Virtual Environment paths
VENV_DIR=""
if [ -d "$PROJECT_ROOT/venv" ]; then
    VENV_DIR="$PROJECT_ROOT/venv"
elif [ -d "$PROJECT_ROOT/chikooza_env" ]; then
    VENV_DIR="$PROJECT_ROOT/chikooza_env"
else
    VENV_DIR="$PROJECT_ROOT/venv"
fi

get_timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo -e "$(get_timestamp) [${BLUE}INFO${NC}] $1"
}

log_success() {
    echo -e "$(get_timestamp) [${GREEN}SUCCESS${NC}] $1"
}

log_warning() {
    echo -e "$(get_timestamp) [${YELLOW}WARNING${NC}] $1"
}

log_error() {
    echo -e "$(get_timestamp) [${RED}ERROR${NC}] $1" >&2
}

# Function to read and export variables from a .env file
load_env() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        log_info "Loading environment variables from $env_file..."
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
                continue
            fi
            if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local val="${BASH_REMATCH[2]}"
                key=$(echo "$key" | xargs)
                val=$(echo "$val" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                if [ -z "${!key}" ]; then
                    export "$key"="$val"
                fi
            fi
        done < "$env_file"
    else
        log_warning "Environment file not found: $env_file"
    fi
}

export RED GREEN YELLOW BLUE NC SCRIPT_DIR PROJECT_ROOT BACKEND_DIR FRONTEND_DIR VENV_DIR
