#!/usr/bin/env bash

# Native local launcher for Linux, macOS, and Windows Git Bash.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd -P -- "$SCRIPT_DIR/../.." >/dev/null 2>&1 && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/chikooza-ui"
SCRIPT_PATH="$SCRIPT_DIR/local.sh"
VENV_DIR="${CHIKOOZA_LOCAL_VENV:-$PROJECT_ROOT/.venv}"
BACKEND_HOST="${CHIKOOZA_LOCAL_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${CHIKOOZA_LOCAL_BACKEND_PORT:-8002}"
FRONTEND_HOST="${CHIKOOZA_LOCAL_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${CHIKOOZA_LOCAL_FRONTEND_PORT:-5173}"
ALLOW_CUSTOM_DATABASE="${CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE:-false}"
BACKEND_PUBLIC_HOST="$BACKEND_HOST"
FRONTEND_PUBLIC_HOST="$FRONTEND_HOST"
[ "$BACKEND_PUBLIC_HOST" != "0.0.0.0" ] || BACKEND_PUBLIC_HOST="127.0.0.1"
[ "$FRONTEND_PUBLIC_HOST" != "0.0.0.0" ] || FRONTEND_PUBLIC_HOST="127.0.0.1"
BACKEND_URL="http://$BACKEND_PUBLIC_HOST:$BACKEND_PORT/"
BACKEND_READY_URL="${BACKEND_URL%/}/health/ready"
FRONTEND_URL="http://$FRONTEND_PUBLIC_HOST:$FRONTEND_PORT/"
BACKEND_LOG="$PROJECT_ROOT/logs/local-backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/local-frontend.log"

case "$(uname -s 2>/dev/null || printf unknown)" in
    Darwin) LOCAL_OS="macos" ;;
    Linux) LOCAL_OS="linux" ;;
    MINGW*|MSYS*|CYGWIN*) LOCAL_OS="windows" ;;
    *) LOCAL_OS="unsupported" ;;
esac

TMP_ROOT="${TMPDIR:-/tmp}"
if [ "$LOCAL_OS" = "windows" ] && command -v cygpath >/dev/null 2>&1; then
    TMP_ROOT="$(cygpath -u "$TMP_ROOT" 2>/dev/null || printf '%s' "$TMP_ROOT")"
fi
PROJECT_ID="$(printf '%s' "$PROJECT_ROOT" | cksum | awk '{print $1}')"
USER_ID="$(id -u 2>/dev/null || printf user)"
RUNTIME_DIR="$TMP_ROOT/chikooza-local-$USER_ID-$PROJECT_ID"
BACKEND_STATE="$RUNTIME_DIR/backend.state"
FRONTEND_STATE="$RUNTIME_DIR/frontend.state"
START_TAIL_PID=0

if [ -t 1 ]; then
    BLUE='\033[0;34m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    RED='\033[0;31m'
    RESET='\033[0m'
else
    BLUE=''
    GREEN=''
    YELLOW=''
    RED=''
    RESET=''
fi

log_info() { printf '%b[INFO]%b %s\n' "$BLUE" "$RESET" "$*"; }
log_ok() { printf '%b[OK]%b %s\n' "$GREEN" "$RESET" "$*"; }
log_warn() { printf '%b[WARN]%b %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die() { printf '%b[ERROR]%b %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

prepare_runtime_directory() {
    [ ! -L "$RUNTIME_DIR" ] || die "Refusing symbolic-link runtime directory: $RUNTIME_DIR"
    [ ! -e "$RUNTIME_DIR" ] || [ -d "$RUNTIME_DIR" ] || \
        die "The runtime path exists but is not a directory: $RUNTIME_DIR"
    mkdir -p "$RUNTIME_DIR"
    [ -O "$RUNTIME_DIR" ] || die "The runtime directory is not owned by the current user: $RUNTIME_DIR"
    chmod 700 "$RUNTIME_DIR"
}

prepare_runtime_directory

usage() {
    cat <<'EOF'
Usage: ./scripts/launchers/local.sh <command>

Commands:
  bootstrap Bootstrap a fresh machine, then start the app interactively
  setup     Install/check runtimes, dependencies, env files, and local data
  start     Start Django and Vite interactively; Ctrl+C stops both
  stop      Stop only processes owned by this launcher
  restart   Stop owned processes, then start interactively
  status    Show launcher-owned process status
  logs      Follow backend and frontend logs
  health    Verify owned processes and both HTTP endpoints
  help      Show this help

This is a local workflow. It deliberately does not pull Git changes, deploy a
public server, or provide rollback. Use the Linux server deployer for those jobs.

Optional environment overrides:
  CHIKOOZA_LOCAL_VENV
  CHIKOOZA_LOCAL_BACKEND_HOST / CHIKOOZA_LOCAL_BACKEND_PORT
  CHIKOOZA_LOCAL_FRONTEND_HOST / CHIKOOZA_LOCAL_FRONTEND_PORT
  CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE
  CHIKOOZA_PYTHON / CHIKOOZA_NODE
EOF
}

ensure_project_layout() {
    [ -f "$PROJECT_ROOT/manage.py" ] || die "manage.py was not found at $PROJECT_ROOT."
    [ -f "$PROJECT_ROOT/requirements.txt" ] || die "requirements.txt was not found."
    [ -f "$FRONTEND_DIR/package.json" ] || die "Frontend package.json was not found."
    [ -f "$FRONTEND_DIR/package-lock.json" ] || die "Frontend package-lock.json is required for npm ci."
}

validate_bind_settings() {
    [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]] || die "CHIKOOZA_LOCAL_BACKEND_PORT must be a number."
    [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]] || die "CHIKOOZA_LOCAL_FRONTEND_PORT must be a number."
    [ "$BACKEND_PORT" -ge 1 ] && [ "$BACKEND_PORT" -le 65535 ] || die "Backend port must be between 1 and 65535."
    [ "$FRONTEND_PORT" -ge 1 ] && [ "$FRONTEND_PORT" -le 65535 ] || die "Frontend port must be between 1 and 65535."
    [[ "$BACKEND_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || die "Backend host must be an IPv4 address or DNS hostname."
    [[ "$FRONTEND_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || die "Frontend host must be an IPv4 address or DNS hostname."
    [[ "$ALLOW_CUSTOM_DATABASE" == true || "$ALLOW_CUSTOM_DATABASE" == false ]] || die "CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE must be true or false."
    [ "$BACKEND_PORT" != "$FRONTEND_PORT" ] || die "Backend and frontend must use different ports."
}

as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        log_info "The operating-system package manager may request your password."
        sudo "$@"
    else
        die "This package installation needs root access, but sudo is unavailable. Install the reported packages manually and rerun setup."
    fi
}

to_unix_path() {
    if [ "$LOCAL_OS" = "windows" ] && command -v cygpath >/dev/null 2>&1; then
        cygpath -u "$1" 2>/dev/null || printf '%s\n' "$1"
    else
        printf '%s\n' "$1"
    fi
}

prepend_path_if_directory() {
    if [ -d "$1" ]; then
        PATH="$1:$PATH"
        export PATH
    fi
}

activate_known_tool_paths() {
    if [ "$LOCAL_OS" = "macos" ]; then
        prepend_path_if_directory "/opt/homebrew/opt/node@22/bin"
        prepend_path_if_directory "/usr/local/opt/node@22/bin"
        prepend_path_if_directory "/opt/homebrew/opt/python@3.12/libexec/bin"
        prepend_path_if_directory "/usr/local/opt/python@3.12/libexec/bin"
        prepend_path_if_directory "/opt/homebrew/bin"
        prepend_path_if_directory "/usr/local/bin"
    elif [ "$LOCAL_OS" = "windows" ]; then
        local local_app_data="${LOCALAPPDATA:-}"
        local program_files="${PROGRAMFILES:-C:\\Program Files}"
        local directory

        if [ -n "$local_app_data" ]; then
            local_app_data="$(to_unix_path "$local_app_data")"
            prepend_path_if_directory "$local_app_data/Microsoft/WinGet/Links"
            prepend_path_if_directory "$local_app_data/Programs/nodejs"
            for directory in "$local_app_data"/Programs/Python/Python3*; do
                if [ -d "$directory" ]; then
                    prepend_path_if_directory "$directory/Scripts"
                    prepend_path_if_directory "$directory"
                fi
            done
        fi

        program_files="$(to_unix_path "$program_files")"
        prepend_path_if_directory "$program_files/nodejs"
    fi
    hash -r 2>/dev/null || true
}

python_version_supported() {
    local version="$1"
    local major minor
    major="${version%%.*}"
    minor="${version#*.}"
    minor="${minor%%.*}"
    [[ "$major" =~ ^[0-9]+$ ]] || return 1
    [[ "$minor" =~ ^[0-9]+$ ]] || return 1
    [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }
}

PYTHON_EXEC=""
PYTHON_MODE=""
PYTHON_VERSION=""

select_python() {
    local candidate resolved version
    local candidates="python3.12 python3.11 python3.13 python3.14 python3 python"

    if [ -n "${CHIKOOZA_PYTHON:-}" ]; then
        candidate="$CHIKOOZA_PYTHON"
        if [[ "$candidate" == */* ]]; then
            [ -x "$candidate" ] && resolved="$candidate" || resolved=""
        else
            resolved="$(command -v "$candidate" 2>/dev/null || true)"
        fi
        if [ -n "$resolved" ]; then
            version="$("$resolved" -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))' 2>/dev/null || true)"
            if python_version_supported "$version"; then
                PYTHON_EXEC="$resolved"
                PYTHON_MODE="direct"
                PYTHON_VERSION="$version"
                return 0
            fi
        fi
    fi

    for candidate in $candidates; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        version="$("$candidate" -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))' 2>/dev/null || true)"
        if python_version_supported "$version"; then
            PYTHON_EXEC="$(command -v "$candidate")"
            PYTHON_MODE="direct"
            PYTHON_VERSION="$version"
            return 0
        fi
    done

    if command -v py >/dev/null 2>&1; then
        version="$(py -3 -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))' 2>/dev/null || true)"
        if python_version_supported "$version"; then
            PYTHON_EXEC="$(command -v py)"
            PYTHON_MODE="launcher"
            PYTHON_VERSION="$version"
            return 0
        fi
    fi
    return 1
}

system_python() {
    if [ "$PYTHON_MODE" = "launcher" ]; then
        "$PYTHON_EXEC" -3 "$@"
    else
        "$PYTHON_EXEC" "$@"
    fi
}

node_version_supported() {
    local version="${1#v}"
    local major minor
    major="${version%%.*}"
    minor="${version#*.}"
    minor="${minor%%.*}"
    [[ "$major" =~ ^[0-9]+$ ]] || return 1
    [[ "$minor" =~ ^[0-9]+$ ]] || return 1

    if [ "$major" -eq 20 ]; then
        [ "$minor" -ge 19 ]
    elif [ "$major" -eq 22 ]; then
        [ "$minor" -ge 12 ]
    else
        [ "$major" -gt 22 ]
    fi
}

NODE_EXEC=""
NODE_VERSION=""
NPM_EXEC=""

select_node() {
    local candidate resolved version
    local candidates="node"

    if [ -n "${CHIKOOZA_NODE:-}" ]; then
        candidate="$CHIKOOZA_NODE"
        if [[ "$candidate" == */* ]]; then
            [ -x "$candidate" ] && resolved="$candidate" || resolved=""
        else
            resolved="$(command -v "$candidate" 2>/dev/null || true)"
        fi
        if [ -n "$resolved" ]; then
            version="$("$resolved" --version 2>/dev/null || true)"
            if node_version_supported "$version"; then
                NODE_EXEC="$resolved"
                NODE_VERSION="${version#v}"
                prepend_path_if_directory "$(dirname "$NODE_EXEC")"
                hash -r 2>/dev/null || true
                return 0
            fi
        fi
    fi
    if [ "$LOCAL_OS" = "macos" ]; then
        candidates="/opt/homebrew/opt/node@22/bin/node /usr/local/opt/node@22/bin/node $candidates"
    elif [ "$LOCAL_OS" = "linux" ]; then
        candidates="/usr/local/bin/node /usr/bin/node $candidates"
    fi

    for candidate in $candidates; do
        if [[ "$candidate" == */* ]]; then
            [ -x "$candidate" ] || continue
            resolved="$candidate"
        else
            command -v "$candidate" >/dev/null 2>&1 || continue
            resolved="$(command -v "$candidate")"
        fi
        version="$("$resolved" --version 2>/dev/null || true)"
        if node_version_supported "$version"; then
            NODE_EXEC="$resolved"
            NODE_VERSION="${version#v}"
            prepend_path_if_directory "$(dirname "$NODE_EXEC")"
            hash -r 2>/dev/null || true
            return 0
        fi
    done
    return 1
}

select_npm() {
    local candidate
    for candidate in npm npm.cmd; do
        if command -v "$candidate" >/dev/null 2>&1; then
            NPM_EXEC="$(command -v "$candidate")"
            "$NPM_EXEC" --version >/dev/null 2>&1 && return 0
        fi
    done
    return 1
}

git_is_available() {
    command -v git >/dev/null 2>&1 && git --version >/dev/null 2>&1
}

curl_is_available() {
    command -v curl >/dev/null 2>&1 && curl --version >/dev/null 2>&1
}

python_can_create_venv() {
    local probe status=0
    [ -n "$PYTHON_EXEC" ] || return 1
    mkdir -p "$RUNTIME_DIR"
    probe="$RUNTIME_DIR/venv-probe.$$"
    [ ! -e "$probe" ] || return 1
    system_python -m venv "$probe" >/dev/null 2>&1 || status=$?
    rm -rf -- "$probe"
    return "$status"
}

require_apt() {
    command -v apt-get >/dev/null 2>&1 || die "Automatic Linux setup currently supports apt-based distributions. Install Git, curl, Python 3.11+, Node ^20.19 or >=22.12, and npm manually."
}

install_linux_base() {
    require_apt
    log_info "Installing base packages with apt. sudo may prompt for permission."
    as_root apt-get update
    as_root apt-get install -y ca-certificates curl git gnupg python3 python3-pip python3-venv
}

install_linux_node() {
    local key_file list_file architecture
    require_apt
    mkdir -p "$RUNTIME_DIR"
    key_file="$RUNTIME_DIR/nodesource-repo.gpg.key"
    list_file="$RUNTIME_DIR/nodesource.list"

    command -v curl >/dev/null 2>&1 || die "curl is required before Node.js can be installed."
    command -v gpg >/dev/null 2>&1 || die "gpg is required before Node.js can be installed."
    command -v dpkg >/dev/null 2>&1 || die "dpkg is required for the Node.js apt repository."

    log_info "Configuring the NodeSource Node.js 22 apt repository."
    curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 \
        https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o "$key_file"
    as_root install -d -m 0755 /etc/apt/keyrings
    as_root gpg --dearmor --yes --output /etc/apt/keyrings/nodesource.gpg "$key_file"
    as_root chmod 0644 /etc/apt/keyrings/nodesource.gpg
    architecture="$(dpkg --print-architecture)"
    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main\n' "$architecture" > "$list_file"
    as_root install -m 0644 "$list_file" /etc/apt/sources.list.d/nodesource.list
    as_root apt-get update
    as_root apt-get install -y nodejs
}

BREW_EXEC=""

select_brew() {
    local candidate
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew brew; do
        if [[ "$candidate" == */* ]]; then
            [ -x "$candidate" ] || continue
            BREW_EXEC="$candidate"
        elif command -v "$candidate" >/dev/null 2>&1; then
            BREW_EXEC="$(command -v "$candidate")"
        else
            continue
        fi
        prepend_path_if_directory "${BREW_EXEC%/*}"
        return 0
    done
    return 1
}

ensure_brew() {
    local installer
    select_brew && return 0
    command -v /usr/bin/curl >/dev/null 2>&1 || die "macOS curl is unavailable, so Homebrew cannot be installed automatically."
    mkdir -p "$RUNTIME_DIR"
    installer="$RUNTIME_DIR/install-homebrew.sh"
    log_warn "Homebrew is missing. Its official installer may request administrator permission for standard install directories."
    /usr/bin/curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 \
        https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer"
    /bin/bash "$installer"
    select_brew || die "Homebrew was installed but is not available in this shell. Open a new terminal and rerun setup."
}

brew_install() {
    ensure_brew
    log_info "Installing $1 with Homebrew."
    "$BREW_EXEC" install "$1"
}

select_winget() {
    command -v winget.exe 2>/dev/null || command -v winget 2>/dev/null
}

winget_install_user() {
    local package_id="$1"
    local winget
    winget="$(select_winget)" || die "WinGet is unavailable. Install App Installer from Microsoft, then rerun setup."
    "$winget" install --id "$package_id" --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
}

winget_install_node() {
    local winget
    winget="$(select_winget)" || die "WinGet is unavailable. Install App Installer from Microsoft, then rerun setup."
    log_info "Trying a per-user Node.js LTS installation with WinGet."
    if ! "$winget" install --id OpenJS.NodeJS.LTS --exact --source winget --scope user --accept-source-agreements --accept-package-agreements; then
        log_warn "The Node.js package did not accept a per-user installation. The standard WinGet installer may display a Windows UAC prompt."
        "$winget" install --id OpenJS.NodeJS.LTS --exact --source winget --accept-source-agreements --accept-package-agreements
    fi
}

install_missing_runtimes() {
    local need_python=0 need_venv=0 need_node=0 need_npm=0 need_git=0 need_curl=0

    activate_known_tool_paths
    select_python || need_python=1
    if [ "$need_python" -eq 0 ] && ! python_can_create_venv; then
        need_venv=1
    fi
    select_node || need_node=1
    select_npm || need_npm=1
    git_is_available || need_git=1
    curl_is_available || need_curl=1

    if [ "$need_python" -eq 0 ] && [ "$need_venv" -eq 0 ] && [ "$need_node" -eq 0 ] && [ "$need_npm" -eq 0 ] && [ "$need_git" -eq 0 ] && [ "$need_curl" -eq 0 ]; then
        return 0
    fi

    case "$LOCAL_OS" in
        linux)
            install_linux_base
            activate_known_tool_paths
            if ! select_node || ! select_npm; then
                install_linux_node
            fi
            ;;
        macos)
            ensure_brew
            [ "$need_git" -eq 0 ] || brew_install git
            [ "$need_curl" -eq 0 ] || brew_install curl
            if [ "$need_python" -ne 0 ] || [ "$need_venv" -ne 0 ]; then
                brew_install python@3.12
            fi
            if [ "$need_node" -ne 0 ] || [ "$need_npm" -ne 0 ]; then
                brew_install node@22
            fi
            ;;
        windows)
            [ "$need_git" -eq 0 ] || winget_install_user Git.Git
            [ "$need_curl" -eq 0 ] || winget_install_user cURL.cURL
            if [ "$need_python" -ne 0 ] || [ "$need_venv" -ne 0 ]; then
                winget_install_user Python.Python.3.12
            fi
            if [ "$need_node" -ne 0 ] || [ "$need_npm" -ne 0 ]; then
                winget_install_node
            fi
            ;;
        *)
            die "Unsupported operating system: $(uname -s). Use Linux, macOS, or Windows Git Bash."
            ;;
    esac

    activate_known_tool_paths
    select_python || die "Python 3.11 or newer is still unavailable after package installation. You may need to open a new terminal or install it manually."
    python_can_create_venv || die "Python is present but cannot create virtual environments. Install the venv component and rerun setup."
    select_node || die "A Vite-compatible Node.js version is still unavailable. Required: ^20.19.0 or >=22.12.0. You may need to open a new terminal."
    select_npm || die "npm is still unavailable after Node.js installation. You may need to open a new terminal."
    git_is_available || die "Git is still unavailable after package installation."
    curl_is_available || die "curl is still unavailable after package installation."
}

validate_runtimes() {
    activate_known_tool_paths
    select_python || die "Python 3.11+ is required. Run './scripts/launchers/local.sh setup'."
    select_node || die "Node.js ^20.19.0 or >=22.12.0 is required by Vite. Run './scripts/launchers/local.sh setup'."
    select_npm || die "npm is required. Run './scripts/launchers/local.sh setup'."
    git_is_available || die "Git is required. Run './scripts/launchers/local.sh setup'."
    curl_is_available || die "curl is required. Run './scripts/launchers/local.sh setup'."

    log_ok "Python $PYTHON_VERSION: $PYTHON_EXEC"
    log_ok "Node.js $NODE_VERSION: $NODE_EXEC"
    log_ok "npm $("$NPM_EXEC" --version): $NPM_EXEC"
    log_ok "Git: $(git --version)"
    log_ok "curl: $(curl --version | sed -n '1p')"
}

venv_python_path() {
    if [ -f "$VENV_DIR/bin/python" ]; then
        printf '%s\n' "$VENV_DIR/bin/python"
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        printf '%s\n' "$VENV_DIR/Scripts/python.exe"
    else
        return 1
    fi
}

VENV_PYTHON=""

venv_is_supported() {
    local executable version
    executable="$(venv_python_path 2>/dev/null || true)"
    [ -n "$executable" ] || return 1
    version="$("$executable" -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))' 2>/dev/null || true)"
    python_version_supported "$version"
}

venv_is_owned() {
    [ -f "$VENV_DIR/.chikooza-local-venv" ] || return 1
    [ "$(sed -n '1p' "$VENV_DIR/.chikooza-local-venv")" = "$PROJECT_ROOT" ]
}

create_venv() {
    local candidate="$VENV_DIR.building.$$"
    [ ! -e "$candidate" ] || die "Temporary virtual environment already exists: $candidate"
    log_info "Creating isolated Python environment at $VENV_DIR."
    if ! system_python -m venv "$candidate"; then
        rm -rf -- "$candidate"
        die "Python could not create a virtual environment. On apt Linux, ensure python3-venv is installed."
    fi
    printf '%s\n' "$PROJECT_ROOT" > "$candidate/.chikooza-local-venv"
    mv -- "$candidate" "$VENV_DIR"
}

ensure_venv() {
    local purpose="${1:-runtime}"
    [ "$VENV_DIR" != "/" ] && [ "$VENV_DIR" != "$PROJECT_ROOT" ] || die "CHIKOOZA_LOCAL_VENV must point to a dedicated virtual-environment directory."
    if [ -d "$VENV_DIR" ]; then
        if venv_is_supported; then
            if ! venv_is_owned; then
                if [ "$purpose" = "setup" ]; then
                    die "$VENV_DIR is valid but was not created by this launcher. Setup refuses to modify it; move it aside or choose an empty CHIKOOZA_LOCAL_VENV path."
                fi
                log_warn "Using the valid existing $VENV_DIR environment without modifying or taking ownership of it."
            fi
        elif venv_is_owned; then
            log_warn "Rebuilding the launcher-owned virtual environment because its Python runtime is invalid or too old."
            rm -rf -- "$VENV_DIR"
            create_venv
        else
            die "$VENV_DIR exists but is not a valid launcher-owned Python 3.11+ environment. Move it aside manually, then rerun setup."
        fi
    else
        create_venv
    fi
    VENV_PYTHON="$(venv_python_path)"
}

create_environment_files() {
    local backend_tmp frontend_tmp

    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        [ -f "$PROJECT_ROOT/.env.example" ] || die "Backend .env.example is missing."
        backend_tmp="$PROJECT_ROOT/.env.local-setup.$$"
        log_info "Creating backend .env with the local SQLite/RAG fallback."
        awk -v backend_url="$BACKEND_URL" -v backend_host="$BACKEND_HOST" '
            BEGIN { replaced = 0 }
            /^CHIKOOZA_RAG_REQUIRE_PGVECTOR=/ {
                print "CHIKOOZA_RAG_REQUIRE_PGVECTOR=False"
                replaced = 1
                next
            }
            /^CHIKOOZA_API_BASE_URL=/ {
                print "CHIKOOZA_API_BASE_URL=" backend_url
                next
            }
            /^DJANGO_ALLOWED_HOSTS=/ {
                print "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0," backend_host
                next
            }
            { print }
            END {
                if (!replaced) print "CHIKOOZA_RAG_REQUIRE_PGVECTOR=False"
            }
        ' "$PROJECT_ROOT/.env.example" > "$backend_tmp"
        mv -- "$backend_tmp" "$PROJECT_ROOT/.env"
        log_ok "Created $PROJECT_ROOT/.env without a DATABASE_URL; Django will use SQLite."
    else
        log_info "Keeping the existing backend .env unchanged."
        if ! grep -Eq '^[[:space:]]*DATABASE_URL[[:space:]]*=' "$PROJECT_ROOT/.env" && \
           grep -Eiq '^[[:space:]]*CHIKOOZA_RAG_REQUIRE_PGVECTOR[[:space:]]*=[[:space:]]*(true|1|yes|on)' "$PROJECT_ROOT/.env"; then
            log_warn "The existing .env requires pgvector but has no DATABASE_URL. Local SQLite starts may work, but chatbot retrieval will reject this configuration."
        fi
    fi

    if [ ! -f "$FRONTEND_DIR/.env" ]; then
        [ -f "$FRONTEND_DIR/.env.example" ] || die "Frontend .env.example is missing."
        frontend_tmp="$FRONTEND_DIR/.env.local-setup.$$"
        awk -v backend_url="$BACKEND_URL" '
            /^VITE_API_BASE_URL=/ { print "VITE_API_BASE_URL=" backend_url; next }
            /^VITE_TEMPLATE_BASE_URL=/ { print "VITE_TEMPLATE_BASE_URL=" backend_url; next }
            /^REACT_APP_API_BASE_URL=/ { print "REACT_APP_API_BASE_URL=" backend_url; next }
            /^REACT_APP_TEMPLATE_BASE_URL=/ { print "REACT_APP_TEMPLATE_BASE_URL=" backend_url; next }
            { print }
        ' "$FRONTEND_DIR/.env.example" > "$frontend_tmp"
        mv -- "$frontend_tmp" "$FRONTEND_DIR/.env"
        log_ok "Created $FRONTEND_DIR/.env."
    else
        log_info "Keeping the existing frontend .env unchanged."
    fi
}

run_local_python() (
    cd "$PROJECT_ROOT"
    env \
        DJANGO_SETTINGS_MODULE=chikooza.settings \
        DJANGO_DEBUG=True \
        DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0,$BACKEND_HOST,$BACKEND_PUBLIC_HOST" \
        DJANGO_CSRF_TRUSTED_ORIGINS="${BACKEND_URL%/},${FRONTEND_URL%/}" \
        DJANGO_CSRF_COOKIE_SECURE=False \
        DJANGO_SESSION_COOKIE_SECURE=False \
        DJANGO_SECURE_SSL_REDIRECT=False \
        DJANGO_SECURE_HSTS_SECONDS=0 \
        CHIKOOZA_CORS_ALLOW_ALL=True \
        CHIKOOZA_API_BASE_URL="$BACKEND_URL" \
        CHIKOOZA_UI_BASE_URL="$FRONTEND_URL" \
        CHIKOOZA_RAG_REQUIRE_PGVECTOR=False \
        "$VENV_PYTHON" "$@"
)

validate_database_target() {
    local details engine name host expected_name is_default
    if ! details="$(
        run_local_python -c '
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chikooza.settings")
from django.conf import settings

database = settings.DATABASES["default"]
engine = str(database.get("ENGINE", ""))
name = str(database.get("NAME", ""))
expected = os.path.realpath(settings.BASE_DIR / "db1.sqlite3")
if engine == "django.db.backends.sqlite3":
    name = os.path.realpath(name)
host = str(database.get("HOST", ""))
is_default = "1" if engine == "django.db.backends.sqlite3" and name == expected else "0"
sys.stdout.write("\x1f".join((engine, name, host, expected, is_default)))
' 2>&1
    )"; then
        die "Could not inspect the configured database safely: $details"
    fi

    IFS=$'\x1f' read -r engine name host expected_name is_default <<EOF
$details
EOF
    if [ "$is_default" = 1 ]; then
        log_ok "Local SQLite database: $name"
        return 0
    fi

    [ "$ALLOW_CUSTOM_DATABASE" = true ] || die "Refusing local setup/start against database $engine at ${host:-local}/${name:-unspecified}. The default allowed target is $expected_name; set CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE=true only when this database is intentionally safe to modify."
    log_warn "Custom database explicitly allowed: $engine at ${host:-local}/${name:-unspecified}"
}

setup_local() {
    ensure_project_layout
    validate_bind_settings
    [ "$LOCAL_OS" != "unsupported" ] || die "Unsupported operating system: $(uname -s)."
    [ "$(id -u 2>/dev/null || printf 1)" -ne 0 ] || die "Run local setup as your regular user, not root. The launcher will request sudo only for missing system packages."
    if service_is_running backend || service_is_running frontend; then
        die "Stop the launcher-owned services before setup so their virtual environment and frontend dependencies are not replaced while in use."
    fi
    log_info "Preparing Chikooza locally on $LOCAL_OS."
    install_missing_runtimes
    validate_runtimes
    ensure_venv setup
    create_environment_files

    log_info "Installing backend dependencies."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"
    validate_database_target

    log_info "Installing the exact frontend lockfile dependencies with npm ci."
    (cd "$FRONTEND_DIR" && "$NPM_EXEC" ci)

    log_info "Checking Django and applying local database migrations."
    run_local_python "$PROJECT_ROOT/manage.py" check
    run_local_python "$PROJECT_ROOT/manage.py" migrate --no-input

    log_info "Loading bundled chatbot knowledge. Existing matching documents are skipped."
    run_local_python "$PROJECT_ROOT/manage.py" ingest_chatbot_knowledge

    log_ok "Local setup is complete. Start with: ./scripts/launchers/local.sh start"
}

resolve_start_runtime() {
    ensure_project_layout
    validate_bind_settings
    [ "$(id -u 2>/dev/null || printf 1)" -ne 0 ] || die "Run the local launcher as your regular user, not root."
    validate_runtimes
    [ -f "$PROJECT_ROOT/.env" ] || die "Backend .env is missing. Run './scripts/launchers/local.sh setup'."
    [ -f "$FRONTEND_DIR/.env" ] || die "Frontend .env is missing. Run './scripts/launchers/local.sh setup'."
    ensure_venv runtime
    validate_database_target
    [ -f "$FRONTEND_DIR/node_modules/vite/bin/vite.js" ] || die "Frontend dependencies are missing. Run './scripts/launchers/local.sh setup'."
}

state_file_for() {
    case "$1" in
        backend) printf '%s\n' "$BACKEND_STATE" ;;
        frontend) printf '%s\n' "$FRONTEND_STATE" ;;
        *) return 1 ;;
    esac
}

read_state() {
    local state_file
    state_file="$(state_file_for "$1")" || return 1
    [ -f "$state_file" ] || return 1
    IFS='|' read -r STATE_PID STATE_TOKEN < "$state_file" || return 1
    [[ "$STATE_PID" =~ ^[0-9]+$ ]] || return 1
    [[ "$STATE_TOKEN" =~ ^[A-Za-z0-9._-]+$ ]] || return 1
}

process_command() {
    local pid="$1"
    if [ -r "/proc/$pid/cmdline" ]; then
        tr '\000' ' ' < "/proc/$pid/cmdline"
    elif ps -ww -p "$pid" -o command= >/dev/null 2>&1; then
        ps -ww -p "$pid" -o command=
    elif ps -p "$pid" -o command= >/dev/null 2>&1; then
        ps -p "$pid" -o command=
    else
        return 1
    fi
}

process_is_expected() {
    local service="$1" pid="$2" token="$3" command_line
    kill -0 "$pid" 2>/dev/null || return 1
    command_line="$(process_command "$pid" 2>/dev/null || true)"
    [ -n "$command_line" ] || return 1
    [[ "$command_line" == *"local.sh"* ]] || return 1
    [[ "$command_line" == *"__supervise"* ]] || return 1
    [[ "$command_line" == *"$service"* ]] || return 1
    [[ "$command_line" == *"$token"* ]]
}

process_is_gone_or_zombie() {
    local pid="$1" state
    kill -0 "$pid" 2>/dev/null || return 0
    state="$(ps -p "$pid" -o stat= 2>/dev/null || true)"
    [[ "$state" == Z* ]]
}

service_is_running() {
    local service="$1" state_file
    state_file="$(state_file_for "$service")"
    read_state "$service" || return 1
    if process_is_expected "$service" "$STATE_PID" "$STATE_TOKEN"; then
        return 0
    fi
    if process_is_gone_or_zombie "$STATE_PID"; then
        rm -f -- "$state_file"
    fi
    return 1
}

write_state() {
    local service="$1" pid="$2" token="$3" state_file state_tmp
    state_file="$(state_file_for "$service")"
    rm -f -- "$state_file.stop-failed"
    state_tmp="$state_file.tmp.$$"
    printf '%s|%s\n' "$pid" "$token" > "$state_tmp"
    chmod 600 "$state_tmp" 2>/dev/null || true
    mv -- "$state_tmp" "$state_file"
}

stop_service() {
    local service="$1" state_file failure_file failure_pid attempt
    state_file="$(state_file_for "$service")"
    failure_file="$state_file.stop-failed"
    if ! read_state "$service"; then
        log_info "$service is not running under this launcher."
        return 0
    fi

    if ! kill -0 "$STATE_PID" 2>/dev/null; then
        rm -f -- "$state_file"
        log_info "$service was already stopped."
        return 0
    fi

    if ! process_is_expected "$service" "$STATE_PID" "$STATE_TOKEN"; then
        if process_is_gone_or_zombie "$STATE_PID"; then
            rm -f -- "$state_file"
            log_info "$service was already stopped."
            return 0
        fi
        log_warn "Refusing to signal PID $STATE_PID: it does not match this launcher's $service supervisor token."
        return 1
    fi

    log_info "Stopping $service supervisor (PID $STATE_PID)."
    rm -f -- "$failure_file"
    kill -TERM "$STATE_PID"
    attempt=0
    while [ "$attempt" -lt 100 ]; do
        if ! process_is_expected "$service" "$STATE_PID" "$STATE_TOKEN"; then
            rm -f -- "$state_file"
            if [ -f "$failure_file" ]; then
                failure_pid="$(sed -n '1p' "$failure_file" 2>/dev/null || true)"
                rm -f -- "$failure_file"
                log_warn "$service supervisor could not stop its launcher-owned child${failure_pid:+ PID $failure_pid}."
                return 1
            fi
            log_ok "$service stopped."
            return 0
        fi
        sleep 0.2
        attempt=$((attempt + 1))
    done

    log_warn "$service did not stop after 20 seconds. It was not force-killed; inspect PID $STATE_PID manually."
    return 1
}

stop_local() {
    local result=0
    mkdir -p "$RUNTIME_DIR"
    stop_service frontend || result=1
    stop_service backend || result=1
    return "$result"
}

http_code() {
    local url="$1" code
    code="$(curl --max-time 3 --noproxy '*' --silent --show-error --output /dev/null --write-out '%{http_code}' "$url" 2>/dev/null || true)"
    printf '%s\n' "${code:-000}"
}

http_is_healthy() {
    case "$(http_code "$1")" in
        2??|3??) return 0 ;;
        *) return 1 ;;
    esac
}

port_is_available() {
    local host="$1" port="$2"
    "$VENV_PYTHON" - "$host" "$port" <<'PY'
import socket
import sys
import errno

host = sys.argv[1]
port = int(sys.argv[2])
try:
    addresses = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
except socket.gaierror:
    raise SystemExit(1)

for family, kind, protocol, _, address in addresses:
    sock = socket.socket(family, kind, protocol)
    try:
        sock.bind(address)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise SystemExit(1)
        if exc.errno in {errno.EACCES, errno.EPERM}:
            raise SystemExit(2)
        raise SystemExit(3)
    finally:
        sock.close()
raise SystemExit(0)
PY
}

assert_port_available() {
    local host="$1" port="$2" result
    if port_is_available "$host" "$port"; then
        return 0
    else
        result=$?
    fi
    case "$result" in
        1) die "$host:$port is already occupied, but it is not owned by this launcher. Free the port manually; nothing was killed." ;;
        2) die "The current user is not permitted to bind $host:$port. Choose an unreserved local port or correct system permissions." ;;
        *) die "Could not validate the bind address $host:$port. Check the host name and local network configuration." ;;
    esac
}

wait_for_http() {
    local name="$1" url="$2" attempts=0
    while [ "$attempts" -lt 30 ]; do
        http_is_healthy "$url" && return 0
        sleep 1
        attempts=$((attempts + 1))
    done
    log_warn "$name did not become healthy at $url within 30 seconds."
    return 1
}

new_token() {
    printf '%s-%s-%s-%s' "$PROJECT_ID" "$$" "$(date +%s)" "$RANDOM"
}

supervise_process() {
    local service="$2" token="$3" workdir="$4"
    local child_pid=0 child_status=0
    shift 4

    supervisor_cleanup() {
        local attempt=0 windows_pid="" state_file failure_file
        state_file="$(state_file_for "$service")"
        failure_file="$state_file.stop-failed"
        rm -f -- "$failure_file"
        trap - INT TERM HUP
        if [ "$child_pid" -gt 0 ] && ! process_is_gone_or_zombie "$child_pid"; then
            if [ "$LOCAL_OS" = "windows" ] && command -v taskkill.exe >/dev/null 2>&1; then
                windows_pid="$(sed -n '1p' "/proc/$child_pid/winpid" 2>/dev/null || printf '%s' "$child_pid")"
                MSYS2_ARG_CONV_EXCL='*' taskkill.exe /PID "$windows_pid" /T >/dev/null 2>&1 || true
            else
                kill -TERM "$child_pid" 2>/dev/null || true
            fi
            while [ "$attempt" -lt 25 ] && ! process_is_gone_or_zombie "$child_pid"; do
                sleep 0.2
                attempt=$((attempt + 1))
            done
            if ! process_is_gone_or_zombie "$child_pid"; then
                log_warn "$service child PID $child_pid ignored graceful shutdown; forcing only this launcher-owned process tree."
                if [ "$LOCAL_OS" = "windows" ] && command -v taskkill.exe >/dev/null 2>&1; then
                    MSYS2_ARG_CONV_EXCL='*' taskkill.exe /PID "$windows_pid" /T /F >/dev/null 2>&1 || true
                else
                    kill -KILL "$child_pid" 2>/dev/null || true
                fi
            fi
            attempt=0
            while [ "$attempt" -lt 25 ] && ! process_is_gone_or_zombie "$child_pid"; do
                sleep 0.2
                attempt=$((attempt + 1))
            done
            if process_is_gone_or_zombie "$child_pid"; then
                wait "$child_pid" 2>/dev/null || true
            else
                printf '%s\n' "$child_pid" > "$failure_file"
                chmod 600 "$failure_file" 2>/dev/null || true
                log_warn "$service child PID $child_pid is still alive after a targeted force-stop."
                exit 1
            fi
        fi
        rm -f -- "$failure_file"
        exit 0
    }

    trap supervisor_cleanup INT TERM HUP
    cd "$workdir"
    "$@" &
    child_pid=$!
    wait "$child_pid" || child_status=$?
    log_warn "$service process exited with status $child_status (supervisor token $token)."
    return "$child_status"
}

start_local() {
    local backend_token frontend_token backend_pid frontend_pid exit_status=0
    resolve_start_runtime
    mkdir -p "$RUNTIME_DIR" "$PROJECT_ROOT/logs"
    START_TAIL_PID=0

    if service_is_running backend || service_is_running frontend; then
        die "A launcher-owned service is already running. Use status, stop, or restart."
    fi
    assert_port_available "$BACKEND_HOST" "$BACKEND_PORT"
    assert_port_available "$FRONTEND_HOST" "$FRONTEND_PORT"

    : > "$BACKEND_LOG"
    : > "$FRONTEND_LOG"
    backend_token="$(new_token)-backend"
    frontend_token="$(new_token)-frontend"

    bash "$SCRIPT_PATH" __supervise backend "$backend_token" "$PROJECT_ROOT" \
        env \
        DJANGO_SETTINGS_MODULE=chikooza.settings \
        DJANGO_DEBUG=True \
        DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0,$BACKEND_HOST,$BACKEND_PUBLIC_HOST" \
        DJANGO_CSRF_TRUSTED_ORIGINS="${BACKEND_URL%/},${FRONTEND_URL%/}" \
        DJANGO_CSRF_COOKIE_SECURE=False \
        DJANGO_SESSION_COOKIE_SECURE=False \
        DJANGO_SECURE_SSL_REDIRECT=False \
        DJANGO_SECURE_HSTS_SECONDS=0 \
        CHIKOOZA_CORS_ALLOW_ALL=True \
        CHIKOOZA_API_BASE_URL="$BACKEND_URL" \
        CHIKOOZA_UI_BASE_URL="$FRONTEND_URL" \
        CHIKOOZA_RAG_REQUIRE_PGVECTOR=False \
        "$VENV_PYTHON" -u "$PROJECT_ROOT/manage.py" runserver "$BACKEND_HOST:$BACKEND_PORT" --noreload \
        >> "$BACKEND_LOG" 2>&1 &
    backend_pid=$!
    write_state backend "$backend_pid" "$backend_token"

    bash "$SCRIPT_PATH" __supervise frontend "$frontend_token" "$FRONTEND_DIR" \
        env \
        VITE_API_BASE_URL="$BACKEND_URL" \
        VITE_TEMPLATE_BASE_URL="$BACKEND_URL" \
        REACT_APP_API_BASE_URL="$BACKEND_URL" \
        REACT_APP_TEMPLATE_BASE_URL="$BACKEND_URL" \
        "$NODE_EXEC" "$FRONTEND_DIR/node_modules/vite/bin/vite.js" \
        --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort \
        >> "$FRONTEND_LOG" 2>&1 &
    frontend_pid=$!
    write_state frontend "$frontend_pid" "$frontend_token"

    start_cleanup() {
        local original_status=$?
        trap - EXIT INT TERM HUP
        if [ "$START_TAIL_PID" -gt 0 ] && kill -0 "$START_TAIL_PID" 2>/dev/null; then
            kill -TERM "$START_TAIL_PID" 2>/dev/null || true
            wait "$START_TAIL_PID" 2>/dev/null || true
        fi
        stop_local || true
        exit "$original_status"
    }
    trap start_cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM HUP

    log_info "Waiting for Django and Vite."
    if ! wait_for_http "Backend readiness" "$BACKEND_READY_URL" || ! wait_for_http "Frontend" "$FRONTEND_URL"; then
        printf '\nBackend log:\n' >&2
        tail -n 30 "$BACKEND_LOG" >&2 || true
        printf '\nFrontend log:\n' >&2
        tail -n 30 "$FRONTEND_LOG" >&2 || true
        return 1
    fi

    log_ok "Backend: $BACKEND_URL"
    log_ok "Frontend: $FRONTEND_URL"
    log_info "Streaming logs. Press Ctrl+C to stop both services."
    tail -n 20 -f "$BACKEND_LOG" "$FRONTEND_LOG" &
    START_TAIL_PID=$!

    while service_is_running backend && service_is_running frontend; do
        sleep 2
    done
    log_warn "A service exited unexpectedly. The other service will now be stopped."
    exit_status=1
    return "$exit_status"
}

status_local() {
    local result=0
    if service_is_running backend; then
        read_state backend
        log_ok "backend is running under this launcher (PID $STATE_PID)."
    else
        log_warn "backend is not running under this launcher."
        result=1
    fi
    if service_is_running frontend; then
        read_state frontend
        log_ok "frontend is running under this launcher (PID $STATE_PID)."
    else
        log_warn "frontend is not running under this launcher."
        result=1
    fi
    return "$result"
}

health_local() {
    local result=0 code
    command -v curl >/dev/null 2>&1 || die "curl is required for health checks. Run setup."

    service_is_running backend || { log_warn "backend process is not launcher-owned/running."; result=1; }
    code="$(http_code "$BACKEND_READY_URL")"
    case "$code" in
        2??|3??) log_ok "backend readiness: $code ($BACKEND_READY_URL)" ;;
        *) log_warn "backend readiness failed: $code ($BACKEND_READY_URL)"; result=1 ;;
    esac

    service_is_running frontend || { log_warn "frontend process is not launcher-owned/running."; result=1; }
    code="$(http_code "$FRONTEND_URL")"
    case "$code" in
        2??|3??) log_ok "frontend HTTP health: $code ($FRONTEND_URL)" ;;
        *) log_warn "frontend HTTP health failed: $code ($FRONTEND_URL)"; result=1 ;;
    esac
    return "$result"
}

logs_local() {
    local follow=0
    [ -f "$BACKEND_LOG" ] || [ -f "$FRONTEND_LOG" ] || die "No local logs exist yet. Start the application first."
    service_is_running backend && follow=1
    service_is_running frontend && follow=1
    if [ "$follow" -eq 1 ]; then
        log_info "Following logs. Ctrl+C exits the viewer without stopping services."
        tail -n 100 -f "$BACKEND_LOG" "$FRONTEND_LOG"
    else
        tail -n 100 "$BACKEND_LOG" "$FRONTEND_LOG"
    fi
}

COMMAND="${1:-help}"

if [ "$COMMAND" = "__supervise" ]; then
    [ "$#" -ge 6 ] || exit 64
    supervise_process "$@"
    exit $?
fi

case "$COMMAND" in
    bootstrap) setup_local; start_local ;;
    setup) setup_local ;;
    start) start_local ;;
    stop) stop_local ;;
    restart) stop_local; start_local ;;
    status) status_local ;;
    logs) logs_local ;;
    health) health_local ;;
    help|-h|--help) usage ;;
    deploy|update|rollback)
        die "'$COMMAND' is intentionally unavailable in the local launcher. It never changes Git state or performs server deployment."
        ;;
    *)
        usage >&2
        die "Unknown command: $COMMAND"
        ;;
esac
