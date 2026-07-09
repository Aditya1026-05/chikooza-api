#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "ERROR: deployment failed near line ${LINENO}" >&2' ERR

log() {
  printf '\n==> %s\n' "$*"
}

warn() {
  printf '\nWARNING: %s\n' "$*" >&2
}

fail() {
  printf '\nERROR: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    fail "Required variable $name is empty. Fill scripts/chikooza_deploy.env first."
  fi
}

is_true() {
  case "${1:-}" in
    true|TRUE|1|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

sql_literal() {
  printf "'%s'" "$(printf "%s" "$1" | sed "s/'/''/g")"
}

sql_ident() {
  printf '"%s"' "$(printf "%s" "$1" | sed 's/"/""/g')"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${CHIKOOZA_DEPLOY_ENV:-$SCRIPT_DIR/chikooza_deploy.env}"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
else
  fail "Missing $ENV_FILE. Copy scripts/chikooza_deploy.env.example to scripts/chikooza_deploy.env and fill it."
fi

REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-correct-version}"
PROJECT_DIR="${PROJECT_DIR:-/srv/chikooza}"
APP_DIR="${APP_DIR:-$PROJECT_DIR/app}"
SERVICE_NAME="${SERVICE_NAME:-chikooza}"

API_DOMAIN="${API_DOMAIN:-}"
UI_DOMAIN="${UI_DOMAIN:-}"
ROOT_DOMAIN="${ROOT_DOMAIN:-}"

DB_NAME="${DB_NAME:-chikooza_db}"
DB_USER="${DB_USER:-chikooza_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-}"
GROQ_API_KEY="${GROQ_API_KEY:-}"

INSTALL_NODE="${INSTALL_NODE:-false}"
ENABLE_CERTBOT="${ENABLE_CERTBOT:-false}"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-true}"
SETUP_DATABASE="${SETUP_DATABASE:-true}"
RUN_INGEST="${RUN_INGEST:-true}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"

FRONTEND_WEB_ROOT="${FRONTEND_WEB_ROOT:-/var/www/chikooza-ui}"
GUNICORN_BIND="${GUNICORN_BIND:-127.0.0.1:8001}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"

require_env REPO_URL
require_env API_DOMAIN
require_env UI_DOMAIN
require_env DB_PASSWORD
require_env DJANGO_SECRET_KEY

if [ "$(uname -s)" != "Linux" ]; then
  fail "This production deployment script must run on Linux."
fi

require_cmd sudo
require_cmd git

if is_true "$INSTALL_SYSTEM_PACKAGES"; then
  log "Installing Linux system packages"
  sudo apt update
  sudo apt install -y \
    git \
    curl \
    nginx \
    rsync \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev
fi

if is_true "$SETUP_DATABASE"; then
  log "Creating PostgreSQL database and user"
  require_cmd psql

  DB_USER_LITERAL="$(sql_literal "$DB_USER")"
  DB_USER_IDENT="$(sql_ident "$DB_USER")"
  DB_NAME_LITERAL="$(sql_literal "$DB_NAME")"
  DB_NAME_IDENT="$(sql_ident "$DB_NAME")"
  DB_PASSWORD_LITERAL="$(sql_literal "$DB_PASSWORD")"

  if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = $DB_USER_LITERAL" | grep -q 1; then
    sudo -u postgres psql -c "ALTER USER $DB_USER_IDENT WITH PASSWORD $DB_PASSWORD_LITERAL;"
  else
    sudo -u postgres psql -c "CREATE USER $DB_USER_IDENT WITH PASSWORD $DB_PASSWORD_LITERAL;"
  fi

  if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = $DB_NAME_LITERAL" | grep -q 1; then
    log "Database $DB_NAME already exists"
  else
    sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
  fi

  sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME_IDENT TO $DB_USER_IDENT;"
  sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER_IDENT;"

  if sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"; then
    log "pgvector extension is available"
  else
    warn "pgvector extension could not be enabled. Chatbot vector search may not work until PostgreSQL has pgvector support."
  fi
fi

log "Preparing project directory"
sudo mkdir -p "$PROJECT_DIR"
sudo chown -R "$USER":"$USER" "$PROJECT_DIR"

if [ -d "$APP_DIR/.git" ]; then
  log "Updating existing Git checkout"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
elif [ -e "$APP_DIR" ]; then
  fail "$APP_DIR exists but is not a Git checkout. Move it or set APP_DIR differently."
else
  log "Cloning project"
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

log "Installing Python backend dependencies"
cd "$APP_DIR"
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/pip install -r requirements.txt

log "Writing backend environment file"
DATABASE_URL="postgres://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

sudo tee /etc/chikooza.env >/dev/null <<ENVEOF
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS=$API_DOMAIN

DATABASE_URL=$DATABASE_URL

CHIKOOZA_CORS_ALLOW_ALL=False
CHIKOOZA_CORS_ALLOWED_ORIGINS=https://$UI_DOMAIN
CHIKOOZA_API_BASE_URL=https://$API_DOMAIN/
CHIKOOZA_UI_BASE_URL=https://$UI_DOMAIN

GROQ_API_KEY=$GROQ_API_KEY
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant

CHIKOOZA_RAG_REQUIRE_PGVECTOR=True
CHIKOOZA_RAG_VECTOR_DIMENSIONS=384
CHIKOOZA_RAG_EMBEDDING_PROVIDER=hash

AIBOT_SQL_LLM_PROVIDER=groq
AIBOT_SQL_MODEL=llama-3.1-8b-instant
AIBOT_SQL_FALLBACK_MODEL=llama-3.1-8b-instant
AIBOT_SQL_ANSWER_MODEL=llama-3.1-8b-instant
ENVEOF

sudo chown root:www-data /etc/chikooza.env
sudo chmod 640 /etc/chikooza.env

export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY
export DJANGO_ALLOWED_HOSTS="$API_DOMAIN"
export DATABASE_URL
export CHIKOOZA_CORS_ALLOW_ALL=False
export CHIKOOZA_CORS_ALLOWED_ORIGINS="https://$UI_DOMAIN"
export CHIKOOZA_API_BASE_URL="https://$API_DOMAIN/"
export CHIKOOZA_UI_BASE_URL="https://$UI_DOMAIN"
export GROQ_API_KEY
export GROQ_MODEL=llama-3.1-8b-instant
export GROQ_FALLBACK_MODEL=llama-3.1-8b-instant
export CHIKOOZA_RAG_REQUIRE_PGVECTOR=True
export CHIKOOZA_RAG_VECTOR_DIMENSIONS=384
export CHIKOOZA_RAG_EMBEDDING_PROVIDER=hash
export AIBOT_SQL_LLM_PROVIDER=groq
export AIBOT_SQL_MODEL=llama-3.1-8b-instant
export AIBOT_SQL_FALLBACK_MODEL=llama-3.1-8b-instant
export AIBOT_SQL_ANSWER_MODEL=llama-3.1-8b-instant

log "Running Django checks, migrations, and static collection"
venv/bin/python manage.py check
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput

if is_true "$RUN_INGEST"; then
  log "Loading chatbot knowledge"
  venv/bin/python manage.py ingest_chatbot_knowledge
fi

sudo mkdir -p "$APP_DIR/static" "$APP_DIR/media"
sudo chown -R www-data:www-data "$APP_DIR/static" "$APP_DIR/media"

log "Creating systemd Gunicorn service"
sudo tee "/etc/systemd/system/$SERVICE_NAME.service" >/dev/null <<SERVICEEOF
[Unit]
Description=Chikooza Django Gunicorn service
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/chikooza.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers $GUNICORN_WORKERS --bind $GUNICORN_BIND chikooza.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

log "Configuring Nginx backend site"
sudo tee /etc/nginx/sites-available/chikooza-api >/dev/null <<NGINXEOF
server {
    listen 80;
    server_name $API_DOMAIN;

    client_max_body_size 25M;

    location /static/ {
        alias $APP_DIR/static/;
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://$GUNICORN_BIND;
    }
}
NGINXEOF

sudo ln -sfn /etc/nginx/sites-available/chikooza-api /etc/nginx/sites-enabled/chikooza-api

if is_true "$DEPLOY_FRONTEND"; then
  log "Building and deploying React frontend"
  if ! command -v npm >/dev/null 2>&1; then
    if is_true "$INSTALL_NODE"; then
      curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
      sudo apt install -y nodejs
    else
      fail "npm is missing. Install Node.js manually or set INSTALL_NODE=true in scripts/chikooza_deploy.env."
    fi
  fi

  cd "$APP_DIR/chikooza-ui"
  npm install
  VITE_API_BASE_URL="https://$API_DOMAIN/" \
    VITE_TEMPLATE_BASE_URL="https://$API_DOMAIN/" \
    npm run build

  sudo mkdir -p "$FRONTEND_WEB_ROOT"
  sudo rsync -a --delete "$APP_DIR/chikooza-ui/build/" "$FRONTEND_WEB_ROOT/"
  sudo chown -R www-data:www-data "$FRONTEND_WEB_ROOT"

  FRONTEND_SERVER_NAMES="$UI_DOMAIN"
  if [ -n "$ROOT_DOMAIN" ]; then
    FRONTEND_SERVER_NAMES="$FRONTEND_SERVER_NAMES $ROOT_DOMAIN"
  fi

  sudo tee /etc/nginx/sites-available/chikooza-ui >/dev/null <<NGINXEOF
server {
    listen 80;
    server_name $FRONTEND_SERVER_NAMES;

    root $FRONTEND_WEB_ROOT;
    index index.html;

    location / {
        try_files \$uri /index.html;
    }
}
NGINXEOF

  sudo ln -sfn /etc/nginx/sites-available/chikooza-ui /etc/nginx/sites-enabled/chikooza-ui
fi

log "Testing and restarting Nginx"
sudo nginx -t
sudo systemctl restart nginx

if is_true "$ENABLE_CERTBOT"; then
  log "Enabling HTTPS with Certbot"
  sudo apt install -y certbot python3-certbot-nginx
  sudo certbot --nginx -d "$API_DOMAIN"
  if is_true "$DEPLOY_FRONTEND"; then
    if [ -n "$ROOT_DOMAIN" ]; then
      sudo certbot --nginx -d "$UI_DOMAIN" -d "$ROOT_DOMAIN"
    else
      sudo certbot --nginx -d "$UI_DOMAIN"
    fi
  fi
fi

log "Deployment finished"
sudo systemctl --no-pager status "$SERVICE_NAME" || true
printf '\nBackend:  https://%s\n' "$API_DOMAIN"
if is_true "$DEPLOY_FRONTEND"; then
  printf 'Frontend: https://%s\n' "$UI_DOMAIN"
fi
