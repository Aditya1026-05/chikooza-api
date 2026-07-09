# Chikooza Deployment Runbook

This document explains how to deploy the Chikooza project in a DigitalOcean-style
setup using Django, PostgreSQL, Gunicorn, Nginx, and the React/Vite frontend.

The main production server should be Linux. Windows and macOS are usually used by
developers to prepare code, run checks, build the frontend, and push changes to
the Linux server or hosting platform.

## 1. What We Are Deploying

Chikooza has three main parts:

1. Django backend
   - Project root contains `manage.py`.
   - Main Django settings are in `chikooza/settings.py`.
   - Production app entry is `chikooza/wsgi.py`.
   - Production server command is `gunicorn chikooza.wsgi:application`.

2. React/Vite frontend
   - Frontend code is inside `chikooza-ui/`.
   - Build command is `npm run build`.
   - Production output folder is `chikooza-ui/build/`.

3. PostgreSQL database
   - Production should use PostgreSQL through `DATABASE_URL`.
   - The public chatbot RAG feature should use PostgreSQL with the `pgvector`
     extension available.

Production request flow:

```text
User browser
    |
    v
Nginx
    |
    +--> React frontend static files
    |
    +--> Gunicorn
             |
             v
          Django
             |
             v
        PostgreSQL
```

## 2. Important Values To Decide First

Replace these placeholder values before running production commands:

```bash
REPO_URL="https://github.com/your-org/chikooza-api.git"
BRANCH="correct-version"

PROJECT_DIR="/srv/chikooza"
APP_DIR="/srv/chikooza/app"

API_DOMAIN="api.chikooza.com"
UI_DOMAIN="www.chikooza.com"

DB_NAME="chikooza_db"
DB_USER="chikooza_user"
DB_PASSWORD="replace-with-strong-db-password"

DJANGO_SECRET_KEY="replace-with-long-random-django-secret"
GROQ_API_KEY="replace-with-real-groq-key"
```

Important production note:

Do not set this in production:

```bash
CHIKOOZA_FIXED_OTP=123456
```

That fixed OTP is only for local testing.

## 3. Ready-Made Scripts In This Repo

The repo now includes deployment/local helper scripts in `scripts/`.

Production Linux VPS:

```bash
cp scripts/chikooza_deploy.env.example scripts/chikooza_deploy.env
nano scripts/chikooza_deploy.env
bash scripts/linux_vps_deploy.sh
```

Local Linux check:

```bash
bash scripts/linux_local_check.sh
```

Local macOS check:

```bash
bash scripts/macos_local_check.sh
```

Local Windows check with PowerShell:

```powershell
.\scripts\windows_local_check.ps1
```

Local Windows check with Git Bash or WSL:

```bash
bash scripts/windows_git_bash_local_check.sh
```

Important distinction:

- `scripts/linux_vps_deploy.sh` is the real production-style VPS script. It
  installs/configures PostgreSQL, Gunicorn, systemd, Nginx, and the frontend.
- Windows and macOS scripts are local validation scripts. They install project
  dependencies, run checks/tests, and build the frontend, but they do not set up
  Gunicorn/Nginx production hosting.

## 4. Linux VPS Production Deployment

Use this section on a Linux server such as Ubuntu/Debian on DigitalOcean.

Run commands as a sudo-capable user.

### Step 1: Install Operating System Packages

```bash
sudo apt update
sudo apt install -y \
  git \
  curl \
  nginx \
  postgresql \
  postgresql-contrib \
  python3 \
  python3-venv \
  python3-dev \
  build-essential \
  libpq-dev
```

What this does:

- `git`: downloads the project code.
- `nginx`: public web server and reverse proxy.
- `postgresql`: production database.
- `python3-venv`: creates Python virtual environment.
- `python3-dev`, `build-essential`, `libpq-dev`: help install Python packages
  that need native compilation or PostgreSQL bindings.

### Step 2: Create PostgreSQL Database And User

```bash
sudo -u postgres psql
```

Inside the PostgreSQL prompt, run:

```sql
CREATE DATABASE chikooza_db;
CREATE USER chikooza_user WITH PASSWORD 'replace-with-strong-db-password';
ALTER ROLE chikooza_user SET client_encoding TO 'utf8';
ALTER ROLE chikooza_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE chikooza_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE chikooza_db TO chikooza_user;
\c chikooza_db
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

What this does:

- Creates the production database.
- Creates the database user used by Django.
- Enables `vector` if pgvector is installed and supported.

If `CREATE EXTENSION vector` fails, the database server does not currently have
pgvector installed or enabled. In that case use a PostgreSQL provider that
supports pgvector, or install the pgvector package for that PostgreSQL version.

### Step 3: Download Project Code

```bash
sudo mkdir -p /srv/chikooza
sudo chown -R "$USER":"$USER" /srv/chikooza
git clone -b correct-version https://github.com/your-org/chikooza-api.git /srv/chikooza/app
cd /srv/chikooza/app
```

What this does:

- Creates a stable production folder.
- Clones the selected branch into `/srv/chikooza/app`.

### Step 4: Create Python Environment And Install Backend Packages

```bash
cd /srv/chikooza/app
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

What this does:

- Creates isolated Python environment in `venv/`.
- Installs Django, Gunicorn, DRF, WhiteNoise, PostgreSQL driver, and other
  backend dependencies from `requirements.txt`.

### Step 5: Create Backend Environment File

```bash
sudo nano /etc/chikooza.env
```

Add this content, replacing placeholder values:

```bash
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=replace-with-long-random-django-secret
DJANGO_ALLOWED_HOSTS=api.chikooza.com

DATABASE_URL=postgres://chikooza_user:replace-with-strong-db-password@127.0.0.1:5432/chikooza_db

CHIKOOZA_CORS_ALLOW_ALL=False
CHIKOOZA_CORS_ALLOWED_ORIGINS=https://www.chikooza.com
CHIKOOZA_API_BASE_URL=https://api.chikooza.com/
CHIKOOZA_UI_BASE_URL=https://www.chikooza.com

GROQ_API_KEY=replace-with-real-groq-key
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODEL=llama-3.1-8b-instant

CHIKOOZA_RAG_REQUIRE_PGVECTOR=True
CHIKOOZA_RAG_VECTOR_DIMENSIONS=384
CHIKOOZA_RAG_EMBEDDING_PROVIDER=hash

AIBOT_SQL_LLM_PROVIDER=groq
AIBOT_SQL_MODEL=llama-3.1-8b-instant
AIBOT_SQL_FALLBACK_MODEL=llama-3.1-8b-instant
AIBOT_SQL_ANSWER_MODEL=llama-3.1-8b-instant
```

Then secure the file:

```bash
sudo chown root:www-data /etc/chikooza.env
sudo chmod 640 /etc/chikooza.env
```

What this does:

- Stores production secrets outside Git.
- Lets systemd/Gunicorn read the variables.
- Prevents normal users from reading secrets.

### Step 6: Run Django Production Preparation Commands

```bash
cd /srv/chikooza/app
set -a
source /etc/chikooza.env
set +a

venv/bin/python manage.py check
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/python manage.py ingest_chatbot_knowledge
```

What this does:

- `check`: verifies Django configuration.
- `migrate`: creates/updates PostgreSQL tables.
- `collectstatic`: collects backend/admin static files into `static/`.
- `ingest_chatbot_knowledge`: loads chatbot RAG documents into the database.

If chatbot knowledge ingestion is slow, run it once during first deployment and
again only when knowledge documents change.

### Step 7: Create systemd Service For Gunicorn

```bash
sudo nano /etc/systemd/system/chikooza.service
```

Add:

```ini
[Unit]
Description=Chikooza Django Gunicorn service
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/chikooza/app
EnvironmentFile=/etc/chikooza.env
ExecStart=/srv/chikooza/app/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8001 chikooza.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then set permissions and start it:

```bash
sudo chown -R www-data:www-data /srv/chikooza/app
sudo systemctl daemon-reload
sudo systemctl enable chikooza
sudo systemctl start chikooza
sudo systemctl status chikooza
```

What this does:

- systemd keeps Gunicorn running.
- Gunicorn listens privately on `127.0.0.1:8001`.
- Nginx will forward public requests to Gunicorn.

Useful log command:

```bash
sudo journalctl -u chikooza -f
```

### Step 8: Configure Nginx For Backend API

```bash
sudo nano /etc/nginx/sites-available/chikooza-api
```

Add:

```nginx
server {
    listen 80;
    server_name api.chikooza.com;

    client_max_body_size 25M;

    location /static/ {
        alias /srv/chikooza/app/static/;
    }

    location /media/ {
        alias /srv/chikooza/app/media/;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8001;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/chikooza-api /etc/nginx/sites-enabled/chikooza-api
sudo nginx -t
sudo systemctl restart nginx
```

What this does:

- Nginx receives public traffic on `api.chikooza.com`.
- Static/media files are served from disk.
- API requests are forwarded to Gunicorn/Django.

### Step 9: Configure HTTPS

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Create HTTPS certificate:

```bash
sudo certbot --nginx -d api.chikooza.com
```

What this does:

- Adds HTTPS for the backend API.
- Updates Nginx config automatically.

### Step 10: Deploy The React Frontend On The Same VPS

Install Node.js. Use a current Node version supported by the project build tool.
One common server setup is NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

Build the frontend:

```bash
cd /srv/chikooza/app/chikooza-ui
npm install
VITE_API_BASE_URL=https://api.chikooza.com/ \
VITE_TEMPLATE_BASE_URL=https://api.chikooza.com/ \
npm run build
```

Copy the build output to a public web folder:

```bash
sudo mkdir -p /var/www/chikooza-ui
sudo rsync -a --delete /srv/chikooza/app/chikooza-ui/build/ /var/www/chikooza-ui/
sudo chown -R www-data:www-data /var/www/chikooza-ui
```

Create Nginx frontend config:

```bash
sudo nano /etc/nginx/sites-available/chikooza-ui
```

Add:

```nginx
server {
    listen 80;
    server_name www.chikooza.com chikooza.com;

    root /var/www/chikooza-ui;
    index index.html;

    location / {
        try_files $uri /index.html;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/chikooza-ui /etc/nginx/sites-enabled/chikooza-ui
sudo nginx -t
sudo systemctl restart nginx
```

Add HTTPS:

```bash
sudo certbot --nginx -d www.chikooza.com -d chikooza.com
```

What this does:

- Builds React into static files.
- Serves those files from Nginx.
- `try_files $uri /index.html` allows React Router pages to work after refresh.

## 5. Windows Developer Commands

Use this on a Windows developer laptop. This is not the normal production server
setup. It is for local checks before pushing code.

PowerShell:

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py check
python manage.py test

Set-Location chikooza-ui
npm install
npm run build
```

What this does:

- Verifies backend dependencies and tests locally.
- Verifies the React production build locally.
- Does not create the production Gunicorn/Nginx server.

To deploy after local checks:

```powershell
git status
git add .
git commit -m "Prepare deployment"
git push origin correct-version
```

Then the Linux server or hosting platform pulls/deploys that branch.

## 6. macOS Developer Commands

Use this on a macOS developer laptop. This is also not the normal production
server setup.

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py check
python manage.py test

cd chikooza-ui
npm install
npm run build
```

What this does:

- Checks the Django backend locally.
- Checks the frontend production build locally.
- Prepares confidence before pushing/deploying.

To deploy after local checks:

```bash
git status
git add .
git commit -m "Prepare deployment"
git push origin correct-version
```

## 7. Linux Developer Commands

For a Linux developer machine, local validation is:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py check
python manage.py test

cd chikooza-ui
npm install
npm run build
```

This is local validation, not the full VPS production setup.

## 8. Updating An Existing Linux Deployment

After the first deployment, updates are shorter.

```bash
cd /srv/chikooza/app
sudo -u www-data git pull origin correct-version
sudo -u www-data venv/bin/pip install -r requirements.txt

set -a
source /etc/chikooza.env
set +a

sudo -u www-data venv/bin/python manage.py check
sudo -u www-data venv/bin/python manage.py migrate
sudo -u www-data venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart chikooza
```

If frontend code changed and frontend is hosted on the same VPS:

```bash
cd /srv/chikooza/app/chikooza-ui
sudo -u www-data npm install
sudo -u www-data VITE_API_BASE_URL=https://api.chikooza.com/ VITE_TEMPLATE_BASE_URL=https://api.chikooza.com/ npm run build
sudo rsync -a --delete /srv/chikooza/app/chikooza-ui/build/ /var/www/chikooza-ui/
sudo systemctl reload nginx
```

If chatbot documents changed:

```bash
cd /srv/chikooza/app
set -a
source /etc/chikooza.env
set +a
sudo -u www-data venv/bin/python manage.py ingest_chatbot_knowledge
```

## 9. Quick Verification Checklist

Backend:

```bash
curl -I https://api.chikooza.com/admin/
sudo systemctl status chikooza
sudo journalctl -u chikooza -n 100
```

Frontend:

```bash
curl -I https://www.chikooza.com
```

Manual browser checks:

1. Open `https://www.chikooza.com`.
2. Register/login.
3. Create a farm.
4. Create a flock.
5. Add purchase.
6. Add daily data.
7. Add sale.
8. Open report screens.
9. Test public chatbot.
10. Open `https://api.chikooza.com/admin/`.

## 10. Simple Supervisor Explanation

If asked what the deployment script does, say:

> The Linux deployment installs system packages, creates PostgreSQL database,
> downloads the project, creates a Python virtual environment, installs backend
> dependencies, sets production environment variables, runs Django migrations,
> collects static files, loads chatbot knowledge, starts Django through Gunicorn
> using systemd, and puts Nginx in front as the public web server. The React
> frontend is built with Vite using `npm run build` and served by Nginx as static
> files.

If asked why Windows/macOS are separate, say:

> Gunicorn plus Nginx production hosting is normally Linux server work. Windows
> and macOS commands are mostly for local checking and preparing code before it is
> pushed to the Linux deployment server.

## 11. References

- DigitalOcean Django/PostgreSQL/Gunicorn/Nginx deployment tutorial:
  https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-debian-11
