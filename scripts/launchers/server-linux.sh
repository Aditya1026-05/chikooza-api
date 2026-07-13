#!/usr/bin/env bash

# Native Ubuntu 24.04 production deployment for Chikooza.

set -Eeuo pipefail
IFS=$'\n\t'
umask 027

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
DEFAULT_CONFIG="/etc/chikooza/server.env"
CONFIG_FILE="${CHIKOOZA_CONFIG:-$DEFAULT_CONFIG}"
COMMAND=""
FOLLOW_LOGS=false
LOCK_FD=""
BUILD_RELEASE=""
DEPLOY_IN_PROGRESS=false

APP_NAME=chikooza
APP_USER=chikooza
APP_GROUP=chikooza
INSTALL_ROOT=/srv/chikooza
ROOT_DOMAIN=""
REPO_URL=""
REPO_BRANCH=""
API_DOMAIN=""
UI_DOMAIN=""
MANAGE_DATABASE=true
PG_MAJOR=16
DB_NAME=chikooza
DB_USER=chikooza
DB_PASSWORD=""
DB_HOST=127.0.0.1
DB_PORT=5432
DJANGO_SECRET_KEY=""
GROQ_API_KEY=""
GROQ_API_KEYS=""
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODEL=""
GIT_SSH_KEY=""
NODE_VERSION=22.23.1
GUNICORN_PORT=8001
GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=120
RUN_INGEST=true
ENABLE_CERTBOT=true
CERTBOT_EMAIL=""
CERTBOT_STAGING=true
KEEP_RELEASES=5
KEEP_DB_BACKUPS=7
HEALTH_ATTEMPTS=30
HEALTH_DELAY=2
NGINX_UPLOAD_LIMIT=25m

BUILD_USER=""
BUILD_GROUP=""
WEB_GROUP=chikooza-web
CURRENT_ENV_LINK=""
CERTBOT_WEBROOT=""
CERTIFICATE_NAME=""
CERTIFICATE_DIR=""
SERVICE_NAME=chikooza.service
HOST_CONFIG_STAGED=false
NGINX_BACKUP=""
UNIT_BACKUP=""
NGINX_SITE_EXISTED=false
UNIT_FILE_EXISTED=false
ENABLED_SITE_TARGET=""
DEFAULT_SITE_TARGET=""
UNIT_WAS_ENABLED=false
NGINX_WAS_ENABLED=false
NGINX_WAS_ACTIVE=false

declare -a EXTRA_ENV_KEYS=()
declare -a EXTRA_ENV_VALUES=()
declare -a APP_ENV_ARGS=()

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
warn() { printf '[%s] WARNING: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }

on_error() {
    local status=$? line="${BASH_LINENO[0]:-unknown}"
    printf '[%s] ERROR: server-linux.sh failed near line %s (exit %s).\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$line" "$status" >&2
    exit "$status"
}
trap on_error ERR

cleanup_on_exit() {
    local status=$? current="" previous=""
    trap - EXIT
    set +e
    if [ "$HOST_CONFIG_STAGED" = true ]; then
        warn "Restoring the former Nginx and systemd configuration."
        restore_host_configuration
    fi
    if [ "$DEPLOY_IN_PROGRESS" = true ] && [ -n "$BUILD_USER" ] && id "$BUILD_USER" >/dev/null 2>&1; then
        pkill -TERM -u "$BUILD_USER" 2>/dev/null || true
        sleep 0.5
        pkill -KILL -u "$BUILD_USER" 2>/dev/null || true
    fi
    if [ "$DEPLOY_IN_PROGRESS" = true ] && [ -n "$BUILD_RELEASE" ] && [ -d "$BUILD_RELEASE" ]; then
        current="$(readlink -f "${CURRENT_LINK:-/nonexistent}" 2>/dev/null || true)"
        previous="$(readlink -f "${PREVIOUS_LINK:-/nonexistent}" 2>/dev/null || true)"
        case "$BUILD_RELEASE" in
            "${RELEASES_DIR:-/nonexistent}"/*)
                if [ "$BUILD_RELEASE" != "$current" ] && [ "$BUILD_RELEASE" != "$previous" ]; then
                    warn "Removing failed staged release ${BUILD_RELEASE##*/}."
                    rm -rf --one-file-system -- "$BUILD_RELEASE"
                fi
                ;;
        esac
    fi
    exit "$status"
}
trap cleanup_on_exit EXIT

usage() {
    cat <<'EOF'
Usage: sudo ./scripts/launchers/server-linux.sh [--config PATH] <command> [options]

Commands:
  bootstrap        Provision Ubuntu and perform the first deployment
  deploy           Fetch, build, migrate, activate, restart, and verify
  start            Start the already-deployed Nginx/systemd configuration
  stop             Stop the Chikooza systemd service
  restart          Restart and verify the Chikooza service
  status           Show active releases and service status
  logs [--follow]  Show application journal logs
  health           Verify systemd, Nginx, and public application readiness
  rollback          Switch to the previous code/assets release
  config-template   Print the production configuration template
  help              Show this help

Options:
  --config PATH     Config file (default: /etc/chikooza/server.env)

Production support is intentionally limited to Ubuntu 24.04 with systemd.
Configuration changes are applied by bootstrap/deploy, not start/restart.
EOF
}

print_config_template() {
    if [ -f "$SCRIPT_DIR/server.env.example" ]; then
        cat "$SCRIPT_DIR/server.env.example"
    else
        die "Missing template: $SCRIPT_DIR/server.env.example"
    fi
}

parse_arguments() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --config)
                [ "$#" -ge 2 ] || die "--config requires a path."
                CONFIG_FILE="$2"
                shift 2
                ;;
            --follow)
                FOLLOW_LOGS=true
                shift
                ;;
            bootstrap|deploy|start|stop|restart|status|logs|health|rollback|config-template|help)
                [ -z "$COMMAND" ] || die "Only one command may be supplied."
                COMMAND="$1"
                shift
                ;;
            -h|--help)
                COMMAND=help
                shift
                ;;
            *) die "Unknown argument: $1" ;;
        esac
    done
    [ -n "$COMMAND" ] || COMMAND=help
    [ "$FOLLOW_LOGS" = false ] || [ "$COMMAND" = logs ] || die "--follow is only valid with logs."
}

require_root() {
    [ "${EUID:-$(id -u)}" -eq 0 ] || die "The $COMMAND command must run through sudo/root."
}

require_supported_host() {
    [ -r /etc/os-release ] || die "Cannot identify the operating system."
    # shellcheck disable=SC1091
    . /etc/os-release
    [ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = 24.04 ] || \
        die "Ubuntu 24.04 is required; detected ${PRETTY_NAME:-unknown}."
    [ "$(ps -p 1 -o comm= 2>/dev/null | tr -d ' ')" = systemd ] || \
        die "systemd must be PID 1 on the production server."
    if command -v systemd-detect-virt >/dev/null 2>&1 && systemd-detect-virt --container --quiet; then
        die "Container hosts are not supported by this native server launcher."
    fi
    if grep -Eiq 'microsoft|wsl' /proc/sys/kernel/osrelease 2>/dev/null; then
        die "WSL is supported only for local use, not public production deployment."
    fi
}

trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

decode_value() {
    local value
    value="$(trim "$1")"
    if [[ "$value" == \"* ]]; then
        [[ "$value" == *\" && ${#value} -ge 2 ]] || die "Unclosed double quote in $CONFIG_FILE."
        value="${value:1:${#value}-2}"
    elif [[ "$value" == \'* ]]; then
        [[ "$value" == *\' && ${#value} -ge 2 ]] || die "Unclosed single quote in $CONFIG_FILE."
        value="${value:1:${#value}-2}"
    fi
    [[ "$value" != *$'\r'* && "$value" != *$'\n'* ]] || die "Multiline config values are unsupported."
    printf '%s' "$value"
}

is_config_key() {
    case "$1" in
        REPO_URL|REPO_BRANCH|API_DOMAIN|UI_DOMAIN|ROOT_DOMAIN|APP_NAME|APP_USER|APP_GROUP|INSTALL_ROOT|\
        MANAGE_DATABASE|PG_MAJOR|DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT|DJANGO_SECRET_KEY|\
        GROQ_API_KEY|GROQ_API_KEYS|GROQ_MODEL|GROQ_FALLBACK_MODEL|GIT_SSH_KEY|NODE_VERSION|\
        GUNICORN_PORT|GUNICORN_WORKERS|GUNICORN_TIMEOUT|RUN_INGEST|ENABLE_CERTBOT|CERTBOT_EMAIL|\
        CERTBOT_STAGING|KEEP_RELEASES|KEEP_DB_BACKUPS|HEALTH_ATTEMPTS|HEALTH_DELAY|NGINX_UPLOAD_LIMIT)
            return 0
            ;;
        *) return 1 ;;
    esac
}

load_config() {
    [ -f "$CONFIG_FILE" ] || die "Missing config $CONFIG_FILE. Install scripts/launchers/server.env.example there first."
    [ ! -L "$CONFIG_FILE" ] || die "The server config must not be a symbolic link."
    local owner mode line line_number=0 key raw value app_key
    owner="$(stat -c '%u' "$CONFIG_FILE")"
    mode="$(stat -c '%a' "$CONFIG_FILE")"
    [ "$owner" -eq 0 ] || die "The server config must be owned by root."
    (( (8#$mode & 8#077) == 0 )) || die "The server config must use mode 0600 (no group/world access)."

    local seen_keys=$'\n'
    while IFS= read -r line || [ -n "$line" ]; do
        line_number=$((line_number + 1))
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*$ || "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" == *=* ]] || die "Invalid config syntax at line $line_number."
        key="$(trim "${line%%=*}")"
        raw="${line#*=}"
        [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "Invalid config key at line $line_number."
        [[ "$seen_keys" != *$'\n'"$key"$'\n'* ]] || die "Duplicate config key: $key"
        value="$(decode_value "$raw")"
        if [[ "$key" == ENV__* ]]; then
            app_key="${key#ENV__}"
            [[ "$app_key" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "Invalid application environment key: $key"
            case "$app_key" in
                DATABASE_URL|DJANGO_SETTINGS_MODULE|DJANGO_DEBUG|DJANGO_SECRET_KEY|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|\
                DJANGO_CSRF_COOKIE_SECURE|DJANGO_SESSION_COOKIE_SECURE|CHIKOOZA_CORS_ALLOW_ALL|\
                DJANGO_SECURE_SSL_REDIRECT|DJANGO_SECURE_HSTS_SECONDS|DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS|DJANGO_SECURE_HSTS_PRELOAD|\
                CHIKOOZA_CORS_ALLOWED_ORIGINS|CHIKOOZA_API_BASE_URL|CHIKOOZA_UI_BASE_URL|\
                CHIKOOZA_RAG_REQUIRE_PGVECTOR|CHIKOOZA_RAG_VECTOR_DIMENSIONS|CHIKOOZA_RAG_EMBEDDING_PROVIDER|\
                GROQ_API_KEY|GROQ_API_KEYS|GROQ_MODEL|GROQ_FALLBACK_MODEL|\
                AIBOT_SQL_LLM_PROVIDER|AIBOT_SQL_MODEL|AIBOT_SQL_FALLBACK_MODEL|AIBOT_SQL_ANSWER_MODEL|\
                CHIKOOZA_FIXED_OTP|HOME|PATH|PYTHONHOME|PYTHONPATH|LD_*|PYTHONUNBUFFERED)
                    die "$key attempts to override a deployment-owned environment value."
                    ;;
            esac
            EXTRA_ENV_KEYS+=("$app_key")
            EXTRA_ENV_VALUES+=("$value")
        elif is_config_key "$key"; then
            printf -v "$key" '%s' "$value"
        else
            die "Unsupported config key $key at line $line_number."
        fi
        seen_keys+="$key"$'\n'
    done < "$CONFIG_FILE"
}

is_bool() { [ "$1" = true ] || [ "$1" = false ]; }

node_version_supported() {
    local major minor
    major="${NODE_VERSION%%.*}"
    minor="${NODE_VERSION#*.}"
    minor="${minor%%.*}"
    if [ "$major" -eq 20 ]; then
        [ "$minor" -ge 19 ]
    elif [ "$major" -eq 22 ]; then
        [ "$minor" -ge 12 ]
    else
        [ "$major" -gt 22 ]
    fi
}

validate_config() {
    local required certificate_fingerprint key_owner key_mode
    for required in REPO_URL REPO_BRANCH API_DOMAIN UI_DOMAIN DB_PASSWORD DJANGO_SECRET_KEY; do
        [ -n "${!required:-}" ] || die "Required config value $required is missing."
    done
    [ "$APP_NAME" = chikooza ] || die "APP_NAME is fixed to chikooza to prevent system service collisions."
    [ "$APP_USER" = chikooza ] || die "APP_USER is fixed to the unprivileged chikooza account."
    [ "$APP_GROUP" = chikooza ] || die "APP_GROUP is fixed to the unprivileged chikooza group."
    [[ "$DB_NAME" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || die "DB_NAME is invalid."
    [[ "$DB_USER" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || die "DB_USER is invalid."
    [[ "$DB_HOST" =~ ^[A-Za-z0-9._-]+$ ]] || die "DB_HOST must be an IPv4 address or DNS hostname."
    [[ "$REPO_BRANCH" =~ ^[A-Za-z0-9._/-]+$ && "$REPO_BRANCH" != -* && "$REPO_BRANCH" != *..* ]] || die "REPO_BRANCH is invalid."
    [[ "$REPO_URL" == https://* || "$REPO_URL" == ssh://* || "$REPO_URL" == git@*:* || "$REPO_URL" == file://* ]] || die "REPO_URL must be HTTPS, SSH, or file URL."
    [[ "$REPO_URL" != *[[:space:]]* ]] || die "REPO_URL must not contain whitespace."
    local domain
    for domain in "$API_DOMAIN" "$UI_DOMAIN" ${ROOT_DOMAIN:+"$ROOT_DOMAIN"}; do
        [[ "$domain" =~ ^([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]] || die "Invalid domain: $domain"
    done
    [ "$API_DOMAIN" != "$UI_DOMAIN" ] || die "API_DOMAIN and UI_DOMAIN must be different."
    [[ "$INSTALL_ROOT" =~ ^/(srv|opt)/[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)*$ ]] || die "INSTALL_ROOT must be a simple absolute path below /srv or /opt."
    [[ "/$INSTALL_ROOT/" != */../* && "/$INSTALL_ROOT/" != */./* ]] || die "INSTALL_ROOT must not contain dot path components."
    is_bool "$MANAGE_DATABASE" || die "MANAGE_DATABASE must be true or false."
    is_bool "$RUN_INGEST" || die "RUN_INGEST must be true or false."
    is_bool "$ENABLE_CERTBOT" || die "ENABLE_CERTBOT must be true or false."
    is_bool "$CERTBOT_STAGING" || die "CERTBOT_STAGING must be true or false."
    [[ "$PG_MAJOR" =~ ^[0-9]+$ ]] || die "PG_MAJOR must be numeric."
    [ "$PG_MAJOR" -ge 13 ] || die "PG_MAJOR must be 13 or newer for pgvector."
    [ "$PG_MAJOR" -le 18 ] || die "PG_MAJOR must be 18 or older."
    [[ "$NODE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && node_version_supported || die "NODE_VERSION must satisfy Vite: ^20.19.0 or >=22.12.0."
    local numeric
    for numeric in DB_PORT GUNICORN_PORT GUNICORN_WORKERS GUNICORN_TIMEOUT KEEP_RELEASES KEEP_DB_BACKUPS HEALTH_ATTEMPTS HEALTH_DELAY; do
        [[ "${!numeric}" =~ ^[0-9]+$ ]] || die "$numeric must be numeric."
    done
    [ "$DB_PORT" -ge 1 ] && [ "$DB_PORT" -le 65535 ] || die "DB_PORT is invalid."
    [ "$GUNICORN_PORT" -ge 1024 ] && [ "$GUNICORN_PORT" -le 65535 ] || die "GUNICORN_PORT must be between 1024 and 65535."
    [ "$GUNICORN_WORKERS" -ge 1 ] || die "GUNICORN_WORKERS must be at least 1."
    [ "$GUNICORN_WORKERS" -le 64 ] || die "GUNICORN_WORKERS must not exceed 64."
    [ "$GUNICORN_TIMEOUT" -ge 1 ] && [ "$GUNICORN_TIMEOUT" -le 3600 ] || die "GUNICORN_TIMEOUT must be between 1 and 3600."
    [ "$KEEP_RELEASES" -ge 2 ] || die "KEEP_RELEASES must be at least 2."
    [ "$KEEP_RELEASES" -le 50 ] || die "KEEP_RELEASES must not exceed 50."
    [ "$KEEP_DB_BACKUPS" -ge 1 ] || die "KEEP_DB_BACKUPS must be at least 1."
    [ "$KEEP_DB_BACKUPS" -le 365 ] || die "KEEP_DB_BACKUPS must not exceed 365."
    [ "$HEALTH_ATTEMPTS" -ge 1 ] || die "HEALTH_ATTEMPTS must be at least 1."
    [ "$HEALTH_ATTEMPTS" -le 300 ] || die "HEALTH_ATTEMPTS must not exceed 300."
    [ "$HEALTH_DELAY" -ge 1 ] && [ "$HEALTH_DELAY" -le 60 ] || die "HEALTH_DELAY must be between 1 and 60."
    [[ "$NGINX_UPLOAD_LIMIT" =~ ^[0-9]+[kKmMgG]?$ ]] || die "NGINX_UPLOAD_LIMIT is invalid."
    case "$NGINX_UPLOAD_LIMIT" in 0|0k|0K|0m|0M|0g|0G) die "NGINX_UPLOAD_LIMIT must be greater than zero." ;; esac
    [ "${#DB_PASSWORD}" -ge 16 ] || die "DB_PASSWORD must contain at least 16 characters."
    [ "${#DJANGO_SECRET_KEY}" -ge 32 ] || die "DJANGO_SECRET_KEY must contain at least 32 characters."
    [[ "$DB_PASSWORD" != replace-* && "$DJANGO_SECRET_KEY" != replace-* ]] || die "Replace all example secrets."
    if [ "$ENABLE_CERTBOT" = true ]; then
        [[ "$CERTBOT_EMAIL" == *@*.* ]] || die "CERTBOT_EMAIL is required when ENABLE_CERTBOT=true."
        [[ "$CERTBOT_EMAIL" != replace-* ]] || die "Replace the example CERTBOT_EMAIL before enabling HTTPS."
    fi
    if [ -n "$GIT_SSH_KEY" ]; then
        [[ "$GIT_SSH_KEY" == /* && -f "$GIT_SSH_KEY" && -r "$GIT_SSH_KEY" ]] || die "GIT_SSH_KEY must be a readable absolute file."
        [[ "$GIT_SSH_KEY" =~ ^/[A-Za-z0-9._/-]+$ && "/$GIT_SSH_KEY/" != */../* ]] || die "GIT_SSH_KEY contains unsupported path characters."
        key_owner="$(stat -c '%u' "$GIT_SSH_KEY")"
        key_mode="$(stat -c '%a' "$GIT_SSH_KEY")"
        [ "$key_owner" -eq 0 ] || die "GIT_SSH_KEY must be owned by root."
        (( (8#$key_mode & 8#077) == 0 )) || die "GIT_SSH_KEY must not be accessible by group or other users."
    fi
    case "$DB_USER" in postgres|pg_*|rdsadmin|azure_pg_admin) die "DB_USER uses a reserved privileged role name." ;; esac
    case "$DB_NAME" in postgres|template0|template1) die "DB_NAME uses a reserved PostgreSQL database name." ;; esac
    if [ "$MANAGE_DATABASE" = true ]; then
        case "$DB_HOST" in 127.0.0.1|localhost) ;; *) die "MANAGE_DATABASE=true requires DB_HOST=127.0.0.1 or localhost." ;; esac
        [ "$DB_PORT" -eq 5432 ] || die "MANAGE_DATABASE=true requires the clean-server PostgreSQL port 5432."
    fi
    [ "$ROOT_DOMAIN" != "$API_DOMAIN" ] && [ "$ROOT_DOMAIN" != "$UI_DOMAIN" ] || die "ROOT_DOMAIN must be blank or distinct from API_DOMAIN and UI_DOMAIN."

    RELEASES_DIR="$INSTALL_ROOT/releases"
    SHARED_DIR="$INSTALL_ROOT/shared"
    MEDIA_DIR="$SHARED_DIR/media"
    CHATBOT_LOG_DIR="$SHARED_DIR/chatbot_logs"
    AIBOT_LOG_DIR="$SHARED_DIR/aibot_logs"
    BACKUP_DIR="$INSTALL_ROOT/backups"
    REPOSITORY_DIR="$INSTALL_ROOT/repository.git"
    CURRENT_LINK="$INSTALL_ROOT/current"
    PREVIOUS_LINK="$INSTALL_ROOT/previous"
    APP_CONFIG_DIR="/etc/$APP_NAME"
    CURRENT_ENV_LINK="$APP_CONFIG_DIR/current.env"
    SERVICE_NAME="$APP_NAME.service"
    NGINX_SITE="/etc/nginx/sites-available/$APP_NAME"
    LOCK_FILE="/run/lock/$APP_NAME-deploy.lock"
    PUBLIC_SCHEME=http
    [ "$ENABLE_CERTBOT" = false ] || PUBLIC_SCHEME=https
    BUILD_USER="$APP_USER-build"
    BUILD_GROUP="$APP_GROUP-build"
    CERTBOT_WEBROOT="$SHARED_DIR/certbot"
    certificate_fingerprint="$(printf '%s|%s|%s' "$API_DOMAIN" "$UI_DOMAIN" "$ROOT_DOMAIN" | sha256sum)"
    certificate_fingerprint="${certificate_fingerprint%% *}"
    CERTIFICATE_NAME="${APP_NAME//_/-}-${certificate_fingerprint:0:12}"
    [ "$CERTBOT_STAGING" = false ] || CERTIFICATE_NAME="$CERTIFICATE_NAME-staging"
    CERTIFICATE_DIR="/etc/letsencrypt/live/$CERTIFICATE_NAME"
}

require_command() { command -v "$1" >/dev/null 2>&1 || die "Missing command $1; run bootstrap first."; }

acquire_lock() {
    [ -z "$LOCK_FD" ] || return 0
    require_command flock
    exec {LOCK_FD}>"$LOCK_FILE"
    flock -n "$LOCK_FD" || die "Another $APP_NAME deployment is already running."
}

git_command() {
    if [ -n "$GIT_SSH_KEY" ]; then
        GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" git "$@"
    else
        git "$@"
    fi
}

install_base_packages() {
    log "Installing Ubuntu system packages."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg git openssh-client build-essential xz-utils \
        python3 python3-dev python3-pip python3-venv libpq-dev \
        nginx rsync jq openssl postgresql-common procps
    if [ "$ENABLE_CERTBOT" = true ]; then
        apt-get install -y --no-install-recommends certbot
    fi
}

install_node() {
    local deb_arch node_arch archive base_url temporary checksum_line
    deb_arch="$(dpkg --print-architecture)"
    case "$deb_arch" in
        amd64) node_arch=x64 ;;
        arm64) node_arch=arm64 ;;
        *) die "Unsupported Node.js CPU architecture: $deb_arch" ;;
    esac
    archive="node-v$NODE_VERSION-linux-$node_arch.tar.xz"
    base_url="https://nodejs.org/dist/v$NODE_VERSION"
    temporary="$(mktemp -d)"
    log "Installing verified Node.js $NODE_VERSION."
    curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
        "$base_url/$archive" -o "$temporary/$archive"
    curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
        "$base_url/SHASUMS256.txt" -o "$temporary/SHASUMS256.txt"
    checksum_line="$(grep "  $archive\$" "$temporary/SHASUMS256.txt")"
    [ -n "$checksum_line" ] || die "Node.js checksum entry was not found."
    printf '%s\n' "$checksum_line" > "$temporary/CHECKSUM"
    (cd "$temporary" && sha256sum --check --strict CHECKSUM)
    install -d -m 0755 /usr/local/lib/nodejs
    rm -rf -- "/usr/local/lib/nodejs/node-v$NODE_VERSION-linux-$node_arch"
    tar -xJf "$temporary/$archive" -C /usr/local/lib/nodejs
    ln -sfn "/usr/local/lib/nodejs/node-v$NODE_VERSION-linux-$node_arch/bin/node" /usr/local/bin/node
    ln -sfn "/usr/local/lib/nodejs/node-v$NODE_VERSION-linux-$node_arch/bin/npm" /usr/local/bin/npm
    ln -sfn "/usr/local/lib/nodejs/node-v$NODE_VERSION-linux-$node_arch/bin/npx" /usr/local/bin/npx
    rm -rf -- "$temporary"
    [ "$(node --version)" = "v$NODE_VERSION" ] || die "Node.js installation verification failed."
}

configure_pgdg() {
    install -d -m 0755 /usr/share/postgresql-common/pgdg
    curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor --yes -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg
    chmod 0644 /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg
    printf 'deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] https://apt.postgresql.org/pub/repos/apt noble-pgdg main\n' \
        > /etc/apt/sources.list.d/pgdg.list
    chmod 0644 /etc/apt/sources.list.d/pgdg.list
    apt-get update
}

install_postgresql() {
    configure_pgdg
    apt-get install -y --no-install-recommends "postgresql-client-$PG_MAJOR"
    if [ "$MANAGE_DATABASE" = true ]; then
        apt-get install -y --no-install-recommends \
            "postgresql-$PG_MAJOR" "postgresql-$PG_MAJOR-pgvector"
        systemctl enable --now postgresql
    fi
}

assert_only_groups() {
    local user="$1" group allowed match
    local IFS=' '
    shift
    for group in $(id -nG "$user"); do
        match=false
        for allowed in "$@"; do
            [ "$group" != "$allowed" ] || match=true
        done
        [ "$match" = true ] || die "$user belongs to unexpected group $group. Remove privileged group memberships first."
    done
}

create_service_account() {
    [ "$(realpath -m "$INSTALL_ROOT")" = "$INSTALL_ROOT" ] || \
        die "INSTALL_ROOT must not traverse a symbolic link."
    [ ! -L "$APP_CONFIG_DIR" ] || die "$APP_CONFIG_DIR must not be a symbolic link."
    getent group "$APP_GROUP" >/dev/null 2>&1 || groupadd --system "$APP_GROUP"
    getent group "$BUILD_GROUP" >/dev/null 2>&1 || groupadd --system "$BUILD_GROUP"
    getent group "$WEB_GROUP" >/dev/null 2>&1 || groupadd --system "$WEB_GROUP"
    if ! id "$APP_USER" >/dev/null 2>&1; then
        useradd --system --gid "$APP_GROUP" --create-home \
            --home-dir "/var/lib/$APP_USER" --shell /usr/sbin/nologin "$APP_USER"
    fi
    if ! id "$BUILD_USER" >/dev/null 2>&1; then
        useradd --system --gid "$BUILD_GROUP" --create-home \
            --home-dir "/var/lib/$BUILD_USER" --shell /usr/sbin/nologin "$BUILD_USER"
    fi
    [ "$(id -u "$APP_USER")" -ne 0 ] || die "$APP_USER must not be a privileged account."
    [ "$(id -u "$BUILD_USER")" -ne 0 ] || die "$BUILD_USER must not be a privileged account."
    [ "$(id -gn "$APP_USER")" = "$APP_GROUP" ] || die "$APP_USER exists but its primary group is not $APP_GROUP."
    [ "$(id -gn "$BUILD_USER")" = "$BUILD_GROUP" ] || die "$BUILD_USER exists but its primary group is not $BUILD_GROUP."
    install -d -o "$APP_USER" -g "$APP_GROUP" -m 0750 "/var/lib/$APP_USER"
    install -d -o "$BUILD_USER" -g "$BUILD_GROUP" -m 0750 "/var/lib/$BUILD_USER"
    install -d -o root -g root -m 0755 "$INSTALL_ROOT" "$RELEASES_DIR" "$SHARED_DIR"
    install -d -o "$APP_USER" -g "$WEB_GROUP" -m 2750 "$MEDIA_DIR"
    chgrp -hR "$WEB_GROUP" "$MEDIA_DIR"
    find "$MEDIA_DIR" -type d -exec chmod 2750 {} +
    find "$MEDIA_DIR" -type f -exec chmod 0640 {} +
    install -d -o "$APP_USER" -g "$APP_GROUP" -m 0750 "$CHATBOT_LOG_DIR" "$AIBOT_LOG_DIR"
    install -d -o root -g root -m 0700 "$BACKUP_DIR"
    install -d -o root -g root -m 0750 "$APP_CONFIG_DIR"
    install -d -o root -g root -m 0755 "$CERTBOT_WEBROOT"
    id www-data >/dev/null 2>&1 || die "The Nginx www-data account is missing."
    case " $(id -nG "$BUILD_USER") " in
        *" $APP_GROUP "*) gpasswd --delete "$BUILD_USER" "$APP_GROUP" >/dev/null ;;
    esac
    case " $(id -nG "$BUILD_USER") " in
        *" $WEB_GROUP "*) gpasswd --delete "$BUILD_USER" "$WEB_GROUP" >/dev/null ;;
    esac
    case " $(id -nG www-data) " in
        *" $APP_GROUP "*) gpasswd --delete www-data "$APP_GROUP" >/dev/null ;;
    esac
    usermod --append --groups "$WEB_GROUP" "$APP_USER"
    usermod --append --groups "$WEB_GROUP" www-data
    assert_only_groups "$BUILD_USER" "$BUILD_GROUP"
    assert_only_groups "$APP_USER" "$APP_GROUP" "$WEB_GROUP"
}

provision_database() {
    [ "$MANAGE_DATABASE" = true ] || return 0
    local sql_file
    log "Provisioning PostgreSQL role, database, and pgvector extension."
    sql_file="$(mktemp)"
    CHIKOOZA_PROVISION_DB_USER="$DB_USER" \
    CHIKOOZA_PROVISION_DB_NAME="$DB_NAME" \
    CHIKOOZA_PROVISION_DB_PASSWORD="$DB_PASSWORD" \
        python3 > "$sql_file" <<'PY'
import os


def literal(value):
    return "'" + value.replace("'", "''") + "'"


user = literal(os.environ["CHIKOOZA_PROVISION_DB_USER"])
name = literal(os.environ["CHIKOOZA_PROVISION_DB_NAME"])
password = literal(os.environ["CHIKOOZA_PROVISION_DB_PASSWORD"])
print("SELECT format('CREATE ROLE %I LOGIN', {0})".format(user))
print("WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = {0}) \\gexec".format(user))
print(
    "SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB "
    "NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', {0}, {1}) \\gexec".format(
        user, password
    )
)
print("SELECT format('CREATE DATABASE %I OWNER %I', {0}, {1})".format(name, user))
print("WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = {0}) \\gexec".format(name))
print("SELECT format('ALTER DATABASE %I OWNER TO %I', {0}, {1}) \\gexec".format(name, user))
PY
    chmod 0600 "$sql_file"
    if ! runuser -u postgres -- psql --no-psqlrc --set=ON_ERROR_STOP=1 \
        --port="$DB_PORT" --dbname=postgres < "$sql_file"; then
        rm -f -- "$sql_file"
        die "PostgreSQL role/database provisioning failed."
    fi
    rm -f -- "$sql_file"
    runuser -u postgres -- psql --no-psqlrc --set=ON_ERROR_STOP=1 \
        --port="$DB_PORT" --dbname="$DB_NAME" \
        -c 'CREATE EXTENSION IF NOT EXISTS vector;'
}

urlencode() {
    CHIKOOZA_URL_VALUE="$1" python3 -c \
        'import os, urllib.parse; print(urllib.parse.quote(os.environ["CHIKOOZA_URL_VALUE"], safe=""))'
}

build_environment() {
    local encoded_password cors_origins allowed_hosts hsts_seconds=0 key index
    encoded_password="$(urlencode "$DB_PASSWORD")"
    DATABASE_URL="postgresql://$DB_USER:$encoded_password@$DB_HOST:$DB_PORT/$DB_NAME"
    cors_origins="$PUBLIC_SCHEME://$UI_DOMAIN"
    allowed_hosts="$API_DOMAIN,localhost,127.0.0.1"
    if [ -n "$ROOT_DOMAIN" ]; then
        cors_origins="$cors_origins,$PUBLIC_SCHEME://$ROOT_DOMAIN"
    fi
    [ -n "$GROQ_FALLBACK_MODEL" ] || GROQ_FALLBACK_MODEL="$GROQ_MODEL"
    if [ "$ENABLE_CERTBOT" = true ] && [ "$CERTBOT_STAGING" = false ]; then
        hsts_seconds=31536000
    fi
    APP_ENV_ARGS=(
        "DJANGO_SETTINGS_MODULE=chikooza.settings"
        "DJANGO_DEBUG=False"
        "DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY"
        "DJANGO_ALLOWED_HOSTS=$allowed_hosts"
        "DJANGO_CSRF_TRUSTED_ORIGINS=$PUBLIC_SCHEME://$API_DOMAIN,$cors_origins"
        "DJANGO_CSRF_COOKIE_SECURE=$ENABLE_CERTBOT"
        "DJANGO_SESSION_COOKIE_SECURE=$ENABLE_CERTBOT"
        "DJANGO_SECURE_SSL_REDIRECT=$ENABLE_CERTBOT"
        "DJANGO_SECURE_HSTS_SECONDS=$hsts_seconds"
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False"
        "DJANGO_SECURE_HSTS_PRELOAD=False"
        "DATABASE_URL=$DATABASE_URL"
        "CHIKOOZA_CORS_ALLOW_ALL=False"
        "CHIKOOZA_CORS_ALLOWED_ORIGINS=$cors_origins"
        "CHIKOOZA_API_BASE_URL=$PUBLIC_SCHEME://$API_DOMAIN/"
        "CHIKOOZA_UI_BASE_URL=$PUBLIC_SCHEME://$UI_DOMAIN"
        "GROQ_API_KEY=$GROQ_API_KEY"
        "GROQ_API_KEYS=$GROQ_API_KEYS"
        "GROQ_MODEL=$GROQ_MODEL"
        "GROQ_FALLBACK_MODEL=$GROQ_FALLBACK_MODEL"
        "CHIKOOZA_RAG_REQUIRE_PGVECTOR=True"
        "CHIKOOZA_RAG_VECTOR_DIMENSIONS=384"
        "CHIKOOZA_RAG_EMBEDDING_PROVIDER=hash"
        "AIBOT_SQL_LLM_PROVIDER=groq"
        "AIBOT_SQL_MODEL=$GROQ_MODEL"
        "AIBOT_SQL_FALLBACK_MODEL=$GROQ_FALLBACK_MODEL"
        "AIBOT_SQL_ANSWER_MODEL=$GROQ_MODEL"
        "PYTHONUNBUFFERED=1"
    )
    for ((index = 0; index < ${#EXTRA_ENV_KEYS[@]}; index++)); do
        key="${EXTRA_ENV_KEYS[$index]}"
        APP_ENV_ARGS+=("$key=${EXTRA_ENV_VALUES[$index]}")
    done
}

quote_environment_value() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    printf '"%s"' "$value"
}

write_app_environment() {
    local destination="$1" temporary item key value
    build_environment
    temporary="$(mktemp)"
    for item in "${APP_ENV_ARGS[@]}"; do
        key="${item%%=*}"
        value="${item#*=}"
        printf '%s=%s\n' "$key" "$(quote_environment_value "$value")" >> "$temporary"
    done
    install -o root -g root -m 0600 "$temporary" "$destination"
    rm -f -- "$temporary"
}

run_as_app() {
    local item name
    (
        for name in $(compgen -e); do
            unset "$name" 2>/dev/null || true
        done
        export HOME="/var/lib/$APP_USER"
        export PATH=/usr/local/bin:/usr/bin:/bin
        export LANG=C.UTF-8
        export USER="$APP_USER"
        export LOGNAME="$APP_USER"
        for item in "${APP_ENV_ARGS[@]}"; do
            export "$item"
        done
        runuser --preserve-environment -u "$APP_USER" -- "$@"
    )
}

run_as_builder() {
    runuser -u "$BUILD_USER" -- env -i \
        HOME="/var/lib/$BUILD_USER" \
        PATH=/usr/local/bin:/usr/bin:/bin \
        LANG=C.UTF-8 \
        "$@"
}

terminate_builder_processes() {
    local attempt=0
    if pgrep -u "$BUILD_USER" >/dev/null 2>&1; then
        pkill -TERM -u "$BUILD_USER" 2>/dev/null || true
        while [ "$attempt" -lt 25 ] && pgrep -u "$BUILD_USER" >/dev/null 2>&1; do
            sleep 0.2
            attempt=$((attempt + 1))
        done
        pgrep -u "$BUILD_USER" >/dev/null 2>&1 && pkill -KILL -u "$BUILD_USER" 2>/dev/null || true
    fi
    sleep 0.2
    if pgrep -u "$BUILD_USER" >/dev/null 2>&1; then
        die "The isolated build account still has running processes; refusing root post-processing."
    fi
}

ensure_database_ready() {
    local vector_version
    PGPASSWORD="$DB_PASSWORD" pg_isready --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" >/dev/null || \
        die "PostgreSQL is not reachable at $DB_HOST:$DB_PORT/$DB_NAME."
    vector_version="$(PGPASSWORD="$DB_PASSWORD" psql --no-psqlrc --tuples-only --no-align \
        --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
        -c "SELECT extversion FROM pg_extension WHERE extname='vector'" 2>/dev/null || true)"
    [ -n "$vector_version" ] || die "The configured database does not have the pgvector extension enabled."
    log "PostgreSQL and pgvector $vector_version are ready."
}

ensure_repository() {
    if [ -n "$GIT_SSH_KEY" ]; then
        install -d -o root -g root -m 0700 /root/.ssh
    fi
    if [ ! -d "$REPOSITORY_DIR" ]; then
        log "Creating the Git mirror."
        git_command clone --mirror "$REPO_URL" "$REPOSITORY_DIR"
    else
        git_command --git-dir="$REPOSITORY_DIR" remote set-url origin "$REPO_URL"
    fi
    git_command --git-dir="$REPOSITORY_DIR" fetch --prune origin \
        "+refs/heads/$REPO_BRANCH:refs/remotes/origin/$REPO_BRANCH"
}

create_release() {
    local revision release_id release
    revision="$(git --git-dir="$REPOSITORY_DIR" rev-parse "refs/remotes/origin/$REPO_BRANCH")"
    release_id="$(date -u '+%Y%m%d%H%M%S')-${revision:0:12}-$$"
    release="$RELEASES_DIR/$release_id"
    [ ! -e "$release" ] || die "Release already exists: $release"
    install -d -o root -g "$APP_GROUP" -m 0755 "$release"
    BUILD_RELEASE="$release"
    git --git-dir="$REPOSITORY_DIR" archive "$revision" | tar -x -C "$release"
    rm -rf -- "$release/REVISION"
    printf '%s\n' "$revision" > "$release/REVISION"
    [ -f "$release/manage.py" ] || die "Release does not contain manage.py at its root."
    [ -f "$release/chikooza-ui/package-lock.json" ] || die "Release is missing the frontend lockfile."
    [ -f "$release/requirements.txt" ] || die "Release is missing requirements.txt."
    rm -rf -- "$release/media" "$release/chatbot_logs" "$release/aibot_logs" "$release/.env"
    chown -hR "$BUILD_USER:$BUILD_GROUP" "$release"
}

build_release() {
    local release="$1" frontend="$1/chikooza-ui" api_url
    log "Building release ${release##*/}."
    run_as_builder python3 -m venv "$release/venv"
    run_as_builder "$release/venv/bin/python" -m pip install \
        --disable-pip-version-check --no-cache-dir --upgrade pip wheel
    run_as_builder "$release/venv/bin/python" -m pip install \
        --disable-pip-version-check --no-cache-dir --requirement "$release/requirements.txt"
    api_url="$PUBLIC_SCHEME://$API_DOMAIN/"
    (
        cd "$frontend"
        run_as_builder npm ci --no-audit --no-fund --cache "$release/.npm-cache"
        run_as_builder env \
            VITE_API_BASE_URL="$api_url" \
            VITE_TEMPLATE_BASE_URL="$api_url" \
            REACT_APP_API_BASE_URL="$api_url" \
            REACT_APP_TEMPLATE_BASE_URL="$api_url" \
            npm run build
    )
    [ -f "$frontend/build/index.html" ] || die "Vite did not create chikooza-ui/build/index.html."
    terminate_builder_processes
    [ -d "$release/venv" ] && [ ! -L "$release/venv" ] || die "The build replaced its virtual environment with an unsafe path."
    [ -d "$frontend" ] && [ ! -L "$frontend" ] || die "The build replaced the frontend directory with an unsafe path."
    [ -d "$frontend/build" ] && [ ! -L "$frontend/build" ] || die "The frontend output directory is unsafe."
    [ -z "$(find "$frontend/build" -type l -print -quit)" ] || die "The frontend output contains a symbolic link."
    rm -rf -- "$frontend/node_modules" "$release/.npm-cache"
    rm -rf -- "$release/media" "$release/chatbot_logs" "$release/aibot_logs" \
        "$release/.env" "$release/.runtime.env" "$release/static"
    chown -hR root:"$APP_GROUP" "$release"
    chmod -R u=rwX,g=rX,o= "$release"
    chown root:"$WEB_GROUP" "$release" "$frontend"
    chown -hR root:"$WEB_GROUP" "$frontend/build"
    chmod 0750 "$release" "$frontend"
    chmod -R u=rwX,g=rX,o= "$frontend/build"
    ln -s "$MEDIA_DIR" "$release/media"
    ln -s "$CHATBOT_LOG_DIR" "$release/chatbot_logs"
    ln -s "$AIBOT_LOG_DIR" "$release/aibot_logs"
    chown -h root:"$APP_GROUP" "$release/media" "$release/chatbot_logs" "$release/aibot_logs"
    write_app_environment "$release/.runtime.env"
    install -d -o "$APP_USER" -g "$APP_GROUP" -m 0755 "$release/static"
    run_as_app "$release/venv/bin/python" "$release/manage.py" check --deploy
    run_as_app "$release/venv/bin/python" "$release/manage.py" collectstatic --noinput
    chown -hR root:"$WEB_GROUP" "$release/static"
    chmod -R u=rwX,g=rX,o= "$release/static"
}

backup_database() {
    local backup="$BACKUP_DIR/${BUILD_RELEASE##*/}-pre-migrate.dump"
    log "Creating pre-migration database backup."
    PGPASSWORD="$DB_PASSWORD" pg_dump --format=custom --no-owner --no-acl \
        --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
        --file="$backup" "$DB_NAME"
    pg_restore --list "$backup" >/dev/null || die "The new database backup failed pg_restore validation."
    chown root:root "$backup"
    chmod 0600 "$backup"
}

prune_backups() {
    local count=0 backup
    while IFS= read -r backup; do
        count=$((count + 1))
        [ "$count" -le "$KEEP_DB_BACKUPS" ] || rm -f -- "$backup"
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*-pre-migrate.dump' -print | sort -r)
}

migrate_release() {
    local release="$1"
    backup_database
    log "Applying Django migrations."
    run_as_app "$release/venv/bin/python" "$release/manage.py" migrate --noinput
    if [ "$RUN_INGEST" = true ]; then
        log "Loading bundled chatbot knowledge."
        run_as_app "$release/venv/bin/python" "$release/manage.py" ingest_chatbot_knowledge
    fi
    prune_backups
}

write_systemd_service() {
    local temporary
    temporary="$(mktemp)"
    cat > "$temporary" <<EOF
[Unit]
Description=Chikooza Django Gunicorn service
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
SupplementaryGroups=$WEB_GROUP
WorkingDirectory=$CURRENT_LINK
EnvironmentFile=$CURRENT_ENV_LINK
Environment=HOME=/var/lib/$APP_USER
ExecStart=$CURRENT_LINK/venv/bin/gunicorn chikooza.wsgi:application --chdir $CURRENT_LINK --bind 127.0.0.1:$GUNICORN_PORT --workers $GUNICORN_WORKERS --timeout $GUNICORN_TIMEOUT --access-logfile - --error-logfile -
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGTERM
UMask=0027
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
ReadWritePaths=$SHARED_DIR
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

[Install]
WantedBy=multi-user.target
EOF
    install -o root -g root -m 0644 "$temporary" "/etc/systemd/system/$SERVICE_NAME"
    rm -f -- "$temporary"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
}

validate_nginx_candidate() {
    local site_file="$1" test_config
    test_config="$(mktemp)"
    cat > "$test_config" <<EOF
pid /run/nginx-chikooza-config-test.pid;
error_log stderr;
events {}
http {
    include /etc/nginx/mime.types;
    include $site_file;
}
EOF
    if ! nginx -t -q -c "$test_config"; then
        rm -f -- "$test_config"
        die "The generated Nginx candidate is invalid; the installed site was not changed."
    fi
    rm -f -- "$test_config"
}

write_nginx_site() {
    local temporary installed ui_names hsts_directive=""
    ui_names="$UI_DOMAIN"
    [ -z "$ROOT_DOMAIN" ] || ui_names="$ui_names $ROOT_DOMAIN"
    temporary="$(mktemp)"
    if [ "$ENABLE_CERTBOT" = true ] && certificate_is_usable; then
        if [ "$CERTBOT_STAGING" = false ]; then
            hsts_directive='add_header Strict-Transport-Security "max-age=31536000" always;'
        fi
        cat > "$temporary" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $API_DOMAIN $ui_names;

    location ^~ /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
        default_type text/plain;
        try_files \$uri =404;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $API_DOMAIN;
    client_max_body_size $NGINX_UPLOAD_LIMIT;
    ssl_certificate $CERTIFICATE_DIR/fullchain.pem;
    ssl_certificate_key $CERTIFICATE_DIR/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:ChikoozaTLS:10m;
    ssl_session_timeout 1d;
    $hsts_directive

    location /static/ {
        alias $CURRENT_LINK/static/;
        expires 7d;
    }

    location /media/ {
        alias $MEDIA_DIR/;
        expires 1h;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://127.0.0.1:$GUNICORN_PORT;
        proxy_connect_timeout 5s;
        proxy_read_timeout ${GUNICORN_TIMEOUT}s;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $ui_names;
    root $CURRENT_LINK/chikooza-ui/build;
    index index.html;
    ssl_certificate $CERTIFICATE_DIR/fullchain.pem;
    ssl_certificate_key $CERTIFICATE_DIR/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:ChikoozaTLS:10m;
    ssl_session_timeout 1d;
    $hsts_directive

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
    else
        cat > "$temporary" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $API_DOMAIN;
    client_max_body_size $NGINX_UPLOAD_LIMIT;

    location ^~ /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
        default_type text/plain;
        try_files \$uri =404;
    }

    location /static/ {
        alias $CURRENT_LINK/static/;
        expires 7d;
    }

    location /media/ {
        alias $MEDIA_DIR/;
        expires 1h;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://127.0.0.1:$GUNICORN_PORT;
        proxy_connect_timeout 5s;
        proxy_read_timeout ${GUNICORN_TIMEOUT}s;
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name $ui_names;
    root $CURRENT_LINK/chikooza-ui/build;
    index index.html;

    location ^~ /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
        default_type text/plain;
        try_files \$uri =404;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
    fi
    validate_nginx_candidate "$temporary"
    installed="$NGINX_SITE.new.$$"
    install -o root -g root -m 0644 "$temporary" "$installed"
    rm -f -- "$temporary"
    mv -f -- "$installed" "$NGINX_SITE"
    ln -sfn "$NGINX_SITE" "/etc/nginx/sites-enabled/$APP_NAME"
    rm -f -- /etc/nginx/sites-enabled/default
    nginx -t
    systemctl enable --now nginx
}

stage_host_configuration() {
    local unit_file="/etc/systemd/system/$SERVICE_NAME"
    [ "$HOST_CONFIG_STAGED" = false ] || return 0
    NGINX_BACKUP="$(mktemp)"
    UNIT_BACKUP="$(mktemp)"
    NGINX_SITE_EXISTED=false
    UNIT_FILE_EXISTED=false
    ENABLED_SITE_TARGET=""
    DEFAULT_SITE_TARGET=""
    UNIT_WAS_ENABLED=false
    NGINX_WAS_ENABLED=false
    NGINX_WAS_ACTIVE=false
    if [ -f "$NGINX_SITE" ]; then
        cp -p -- "$NGINX_SITE" "$NGINX_BACKUP"
        NGINX_SITE_EXISTED=true
    fi
    if [ -f "$unit_file" ]; then
        cp -p -- "$unit_file" "$UNIT_BACKUP"
        UNIT_FILE_EXISTED=true
    fi
    [ ! -L "/etc/nginx/sites-enabled/$APP_NAME" ] || \
        ENABLED_SITE_TARGET="$(readlink "/etc/nginx/sites-enabled/$APP_NAME")"
    [ ! -L /etc/nginx/sites-enabled/default ] || \
        DEFAULT_SITE_TARGET="$(readlink /etc/nginx/sites-enabled/default)"
    systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null && UNIT_WAS_ENABLED=true
    systemctl is-enabled --quiet nginx 2>/dev/null && NGINX_WAS_ENABLED=true
    systemctl is-active --quiet nginx 2>/dev/null && NGINX_WAS_ACTIVE=true
    HOST_CONFIG_STAGED=true
}

discard_host_configuration_backup() {
    [ "$HOST_CONFIG_STAGED" = true ] || return 0
    rm -f -- "$NGINX_BACKUP" "$UNIT_BACKUP"
    NGINX_BACKUP=""
    UNIT_BACKUP=""
    HOST_CONFIG_STAGED=false
}

restore_host_configuration() {
    local unit_file="/etc/systemd/system/$SERVICE_NAME"
    [ "$HOST_CONFIG_STAGED" = true ] || return 0
    [ "$UNIT_WAS_ENABLED" = true ] || systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true
    if [ "$NGINX_SITE_EXISTED" = true ]; then
        install -o root -g root -m 0644 "$NGINX_BACKUP" "$NGINX_SITE"
    else
        rm -f -- "$NGINX_SITE"
    fi
    if [ "$UNIT_FILE_EXISTED" = true ]; then
        install -o root -g root -m 0644 "$UNIT_BACKUP" "$unit_file"
    else
        rm -f -- "$unit_file"
    fi
    rm -f -- "/etc/nginx/sites-enabled/$APP_NAME" /etc/nginx/sites-enabled/default
    [ -z "$ENABLED_SITE_TARGET" ] || \
        ln -s "$ENABLED_SITE_TARGET" "/etc/nginx/sites-enabled/$APP_NAME"
    [ -z "$DEFAULT_SITE_TARGET" ] || \
        ln -s "$DEFAULT_SITE_TARGET" /etc/nginx/sites-enabled/default
    systemctl daemon-reload || warn "systemd could not reload the restored unit file."
    if [ "$UNIT_WAS_ENABLED" = true ]; then
        systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || warn "The restored service could not be re-enabled."
    fi
    if [ "$NGINX_WAS_ENABLED" = true ]; then
        systemctl enable nginx >/dev/null 2>&1 || warn "Nginx could not be re-enabled."
    else
        systemctl disable nginx >/dev/null 2>&1 || true
    fi
    if command -v nginx >/dev/null 2>&1 && nginx -t >/dev/null 2>&1; then
        if [ "$NGINX_WAS_ACTIVE" = true ]; then
            if systemctl is-active --quiet nginx; then
                systemctl reload nginx || warn "Nginx could not reload the restored site."
            else
                systemctl start nginx || warn "Nginx could not restart with the restored site."
            fi
        else
            systemctl stop nginx >/dev/null 2>&1 || true
        fi
    else
        warn "The restored Nginx configuration did not validate."
    fi
    discard_host_configuration_backup
}

ensure_host_configuration() {
    stage_host_configuration
    if [ "$ENABLE_CERTBOT" = true ] && ! certificate_is_usable; then
        # Certificate recovery and first issuance need an active HTTP challenge site.
        write_nginx_site
    fi
    configure_certbot
    write_nginx_site
    write_systemd_service
}

set_link_atomically() {
    local target="$1" link="$2" temporary="${link%/*}/.${link##*/}.new.$$"
    rm -f -- "$temporary"
    ln -s "$target" "$temporary"
    mv -Tf "$temporary" "$link"
}

restore_link_state() {
    local target="$1" link="$2"
    if [ -n "$target" ]; then
        set_link_atomically "$target" "$link"
    else
        rm -f -- "$link"
    fi
}

internal_readiness_check() {
    local max_attempts="${1:-$HEALTH_ATTEMPTS}" attempt=0 code body_file
    body_file="$(mktemp)"
    while [ "$attempt" -lt "$max_attempts" ]; do
        code="$(curl --silent --show-error --max-time 5 --noproxy '*' \
            --header "Host: $API_DOMAIN" --header "X-Forwarded-Proto: $PUBLIC_SCHEME" \
            --output "$body_file" \
            --write-out '%{http_code}' "http://127.0.0.1:$GUNICORN_PORT/health/ready" 2>/dev/null || true)"
        if [ "$code" = 200 ] && grep -q '"status": "ok"' "$body_file" 2>/dev/null; then
            rm -f -- "$body_file"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep "$HEALTH_DELAY"
    done
    rm -f -- "$body_file"
    return 1
}

public_readiness_check() {
    local max_attempts="${1:-$HEALTH_ATTEMPTS}" attempt=0 api_code ui_code port body_file
    local -a curl_args
    body_file="$(mktemp)"
    port=80
    [ "$PUBLIC_SCHEME" = http ] || port=443
    curl_args=(--silent --show-error --max-time 5 --noproxy '*' \
        --resolve "$API_DOMAIN:$port:127.0.0.1")
    if [ "$CERTBOT_STAGING" = true ] && [ "$ENABLE_CERTBOT" = true ]; then
        curl_args+=(--insecure)
    fi
    while [ "$attempt" -lt "$max_attempts" ]; do
        api_code="$(curl "${curl_args[@]}" --output "$body_file" --write-out '%{http_code}' \
            "$PUBLIC_SCHEME://$API_DOMAIN/health/ready" 2>/dev/null || true)"
        ui_code="$(curl "${curl_args[@]/$API_DOMAIN/$UI_DOMAIN}" --output /dev/null --write-out '%{http_code}' \
            "$PUBLIC_SCHEME://$UI_DOMAIN/" 2>/dev/null || true)"
        if [ "$api_code" = 200 ] && [ "$ui_code" = 200 ] && \
           grep -q '"status": "ok"' "$body_file" 2>/dev/null; then
            rm -f -- "$body_file"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep "$HEALTH_DELAY"
    done
    rm -f -- "$body_file"
    return 1
}

deployment_readiness_check() {
    local attempts="${1:-$HEALTH_ATTEMPTS}"
    internal_readiness_check "$attempts" && public_readiness_check "$attempts"
}

activate_release() {
    local release="$1" switch_environment="${2:-true}"
    local old_current="" old_environment="" old_previous="" activation_ok=true
    [ -d "$release" ] || die "Release directory does not exist: $release"
    if [ "$switch_environment" = true ]; then
        [ -s "$release/.runtime.env" ] || die "Release environment is missing: $release/.runtime.env"
    else
        [ -L "$CURRENT_ENV_LINK" ] || die "The current runtime environment link is missing."
    fi
    [ ! -L "$CURRENT_LINK" ] || old_current="$(readlink -f "$CURRENT_LINK")"
    [ ! -L "$CURRENT_ENV_LINK" ] || old_environment="$(readlink -f "$CURRENT_ENV_LINK")"
    [ ! -L "$PREVIOUS_LINK" ] || old_previous="$(readlink -f "$PREVIOUS_LINK")"

    if [ -n "$old_current" ]; then
        set_link_atomically "$old_current" "$PREVIOUS_LINK"
    else
        rm -f -- "$PREVIOUS_LINK"
    fi
    set_link_atomically "$release" "$CURRENT_LINK"
    if [ "$switch_environment" = true ]; then
        set_link_atomically "$release/.runtime.env" "$CURRENT_ENV_LINK"
    fi

    systemctl restart "$SERVICE_NAME" || activation_ok=false
    if [ "$activation_ok" = true ]; then
        systemctl reload nginx || activation_ok=false
    fi
    if [ "$activation_ok" = true ]; then
        deployment_readiness_check || activation_ok=false
    fi
    if [ "$activation_ok" = true ]; then
        discard_host_configuration_backup
        return 0
    fi

    warn "Activation failed; restoring the former release and environment. Database migrations are not reversed."
    restore_link_state "$old_current" "$CURRENT_LINK"
    restore_link_state "$old_environment" "$CURRENT_ENV_LINK"
    restore_link_state "$old_previous" "$PREVIOUS_LINK"
    restore_host_configuration
    if [ -n "$old_current" ] && [ -n "$old_environment" ]; then
        systemctl restart "$SERVICE_NAME" || warn "The restored application service could not restart."
        systemctl reload nginx || warn "Nginx could not reload after restoration."
        deployment_readiness_check 3 || warn "The restored release did not pass readiness checks."
    else
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    fi
    return 1
}

certificate_is_usable() {
    local domain
    [ -s "$CERTIFICATE_DIR/fullchain.pem" ] && [ -s "$CERTIFICATE_DIR/privkey.pem" ] || return 1
    openssl x509 -in "$CERTIFICATE_DIR/fullchain.pem" -noout -checkend 86400 >/dev/null 2>&1 || return 1
    for domain in "$API_DOMAIN" "$UI_DOMAIN" ${ROOT_DOMAIN:+"$ROOT_DOMAIN"}; do
        openssl x509 -in "$CERTIFICATE_DIR/fullchain.pem" -noout -checkhost "$domain" >/dev/null 2>&1 || return 1
    done
}

configure_certbot() {
    [ "$ENABLE_CERTBOT" = true ] || return 0
    local temporary
    local -a args
    if ! command -v certbot >/dev/null 2>&1; then
        log "Installing Certbot because HTTPS is enabled."
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        apt-get install -y --no-install-recommends certbot
    fi
    if ! certificate_is_usable; then
        systemctl reload nginx
        args=(certonly --webroot --webroot-path "$CERTBOT_WEBROOT" --non-interactive \
            --agree-tos --email "$CERTBOT_EMAIL" --cert-name "$CERTIFICATE_NAME" \
            -d "$API_DOMAIN" -d "$UI_DOMAIN")
        [ ! -e "$CERTIFICATE_DIR" ] || args+=(--force-renewal)
        [ -z "$ROOT_DOMAIN" ] || args+=(-d "$ROOT_DOMAIN")
        if [ "$CERTBOT_STAGING" = true ]; then
            args+=(--staging)
            warn "Certbot staging is enabled; browsers will not trust this certificate."
        fi
        certbot "${args[@]}"
    fi
    certificate_is_usable || die "Certbot did not create a current certificate covering every configured domain."
    temporary="$(mktemp)"
    cat > "$temporary" <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
    install -d -o root -g root -m 0755 /etc/letsencrypt/renewal-hooks/deploy
    install -o root -g root -m 0755 "$temporary" \
        "/etc/letsencrypt/renewal-hooks/deploy/$APP_NAME-reload-nginx"
    rm -f -- "$temporary"
    systemctl enable --now certbot.timer
}

prune_releases() {
    local count=0 release current previous
    current="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
    previous="$(readlink -f "$PREVIOUS_LINK" 2>/dev/null || true)"
    while IFS= read -r release; do
        count=$((count + 1))
        if [ "$count" -gt "$KEEP_RELEASES" ] && [ "$release" != "$current" ] && [ "$release" != "$previous" ]; then
            rm -rf --one-file-system -- "$release"
        fi
    done < <(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d -print | sort -r)
}

verify_deploy_commands() {
    local command
    for command in git python3 node npm pg_dump pg_restore pg_isready psql nginx \
        systemctl curl flock runuser realpath openssl pgrep pkill sha256sum \
        getent groupadd useradd usermod gpasswd find install tar; do
        require_command "$command"
    done
    [ "$(node --version)" = "v$NODE_VERSION" ] || die "Node.js v$NODE_VERSION is required; run bootstrap."
}

deploy_release() {
    acquire_lock
    verify_deploy_commands
    create_service_account
    terminate_builder_processes
    ensure_database_ready
    ensure_repository
    DEPLOY_IN_PROGRESS=true
    create_release
    build_release "$BUILD_RELEASE"
    migrate_release "$BUILD_RELEASE"
    ensure_host_configuration
    activate_release "$BUILD_RELEASE" || die "Deployment activation failed. Inspect: journalctl -u $SERVICE_NAME"
    prune_releases
    DEPLOY_IN_PROGRESS=false
    log "Deployment complete: ${BUILD_RELEASE##*/}"
}

bootstrap_server() {
    acquire_lock
    install_base_packages
    install_node
    install_postgresql
    create_service_account
    provision_database
    ensure_database_ready
    deploy_release
    log "Bootstrap complete. API: $PUBLIC_SCHEME://$API_DOMAIN/ UI: $PUBLIC_SCHEME://$UI_DOMAIN/"
}

rollback_release() {
    local target
    acquire_lock
    [ -L "$CURRENT_LINK" ] || die "No active release exists."
    [ -L "$PREVIOUS_LINK" ] || die "No previous release exists."
    target="$(readlink -f "$PREVIOUS_LINK")"
    [ -d "$target" ] || die "Previous release directory is missing: $target"
    activate_release "$target" false || die "Rollback failed. Database migrations were not changed."
    log "Rolled back code/assets to ${target##*/} with the current runtime environment. Database migrations were not reversed."
}

health_command() {
    systemctl is-active --quiet "$SERVICE_NAME" || die "$SERVICE_NAME is not active."
    systemctl is-active --quiet nginx || die "nginx is not active."
    nginx -t >/dev/null
    deployment_readiness_check || die "Internal or public application readiness failed."
    log "Systemd, Nginx, internal Django, and public API/UI readiness are healthy."
}

status_command() {
    printf 'Current release:  %s\n' "$(readlink -f "$CURRENT_LINK" 2>/dev/null || printf none)"
    printf 'Previous release: %s\n' "$(readlink -f "$PREVIOUS_LINK" 2>/dev/null || printf none)"
    systemctl --no-pager --full status "$SERVICE_NAME" nginx || true
    if systemctl is-active --quiet "$SERVICE_NAME" && deployment_readiness_check 1; then
        printf 'Readiness:       healthy\n'
    else
        printf 'Readiness:       unavailable\n'
    fi
}

logs_command() {
    local args=(--unit "$SERVICE_NAME" --lines 100 --no-pager)
    [ "$FOLLOW_LOGS" = false ] || args+=(--follow)
    journalctl "${args[@]}"
}

main() {
    parse_arguments "$@"
    case "$COMMAND" in
        help) usage; return 0 ;;
        config-template) print_config_template; return 0 ;;
    esac

    require_root
    require_supported_host
    case "$COMMAND" in
        stop)
            systemctl stop chikooza.service
            return 0
            ;;
        logs)
            SERVICE_NAME=chikooza.service
            logs_command
            return 0
            ;;
    esac
    load_config
    validate_config
    build_environment

    case "$COMMAND" in
        bootstrap) bootstrap_server ;;
        deploy) deploy_release ;;
        start)
            systemctl start nginx "$SERVICE_NAME"
            health_command
            ;;
        stop) systemctl stop "$SERVICE_NAME" ;;
        restart)
            systemctl restart "$SERVICE_NAME"
            health_command
            ;;
        status) status_command ;;
        logs) logs_command ;;
        health) health_command ;;
        rollback) rollback_release ;;
        *) die "Unsupported command: $COMMAND" ;;
    esac
}

main "$@"
