# Ubuntu Server Start Guide

This guide deploys Chikooza to a fresh Ubuntu 24.04 server using the native
`server-linux.sh` launcher. Run the commands in order. The production workflow
does not use Docker or SQLite.

The launcher installs and configures PostgreSQL with pgvector, Python, Node.js,
Gunicorn, systemd, Nginx, and optional Certbot HTTPS. Test the complete process
on a disposable Ubuntu 24.04 server before using it for production.

## 1. Prepare the Server and DNS

Before connecting to the server:

1. Create a clean Ubuntu 24.04 VPS.
2. Allow inbound SSH on port `22`.
3. Allow inbound HTTP on port `80`.
4. Allow inbound HTTPS on port `443`.
5. Point the `API_DOMAIN` DNS record to the server IP.
6. Point the `UI_DOMAIN` DNS record to the server IP.
7. If using `ROOT_DOMAIN`, point that DNS record to the server IP too.

Do not enable Certbot until every configured domain resolves to this server and
ports 80 and 443 are publicly reachable.

## 2. Connect to the Server

Replace the example user and IP with the sudo-capable Ubuntu user and server
address:

```bash
ssh ubuntu@203.0.113.10
```

Confirm the operating system:

```bash
cat /etc/os-release
```

The result must identify Ubuntu `24.04`. The production launcher intentionally
rejects other Linux distributions, macOS, Windows, WSL, and containers.

## 3. Obtain the Launcher

Install Git for the initial operator checkout and OpenSSL for secret generation:

```bash
sudo apt-get update
```

```bash
sudo apt-get install -y git openssl openssh-client
```

For the current public HTTPS repository, clone the deployment branch:

```bash
git clone --branch correct-version https://github.com/RadianceVA/chikooza-api.git "$HOME/chikooza-bootstrap"
```

Enter the repository root:

```bash
cd "$HOME/chikooza-bootstrap"
```

For a private repository, do not run the public clone command above. Prepare a
dedicated root-owned read-only deploy key instead:

```bash
sudo install -d -o root -g root -m 0700 /root/.ssh
```

```bash
sudo ssh-keygen -t ed25519 -N '' -C chikooza-read-only -f /root/.ssh/chikooza_deploy
```

Display the public key:

```bash
sudo cat /root/.ssh/chikooza_deploy.pub
```

Add that public key to the repository as a read-only deploy key. Then clone the
private repository into a root-owned operator checkout:

```bash
sudo git \
  -c core.sshCommand='ssh -i /root/.ssh/chikooza_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  clone \
  --branch correct-version \
  git@github.com:RadianceVA/chikooza-api.git \
  /opt/chikooza-bootstrap
```

Enter the private-repository checkout:

```bash
cd /opt/chikooza-bootstrap
```

## 4. Generate Secrets

Generate a database password:

```bash
openssl rand -hex 32
```

Save the output securely. Generate a different Django secret key:

```bash
openssl rand -hex 32
```

Do not commit either value, paste them into chat, or reuse the same value for
both settings.

## 5. Install the Protected Server Configuration

Create the protected configuration directory:

```bash
sudo install -d -o root -g root -m 0750 /etc/chikooza
```

Copy the configuration template:

```bash
sudo install -o root -g root -m 0600 scripts/launchers/server.env.example /etc/chikooza/server.env
```

Open the protected configuration:

```bash
sudoedit /etc/chikooza/server.env
```

This is the production configuration file. Do not create or use a project
`.env` on the server. Values must use literal `KEY=value` lines. Do not add
`export`, shell commands, command substitutions, or shell expressions.

## 6. Set the Required Configuration Values

Replace these values inside `/etc/chikooza/server.env`:

```text
REPO_URL=https://github.com/RadianceVA/chikooza-api.git
REPO_BRANCH=correct-version
API_DOMAIN=api.example.com
UI_DOMAIN=www.example.com
ROOT_DOMAIN=example.com
DB_PASSWORD=paste-the-generated-database-password
DJANGO_SECRET_KEY=paste-the-generated-django-secret
CERTBOT_EMAIL=admin@example.com
```

Rules:

- `REPO_URL` must identify the repository to deploy.
- `REPO_BRANCH` must identify the production branch.
- `API_DOMAIN` serves Django, including `/admin/` and API endpoints.
- `UI_DOMAIN` serves the React application.
- `ROOT_DOMAIN` is optional; leave it blank when the root domain is not used.
- `DB_PASSWORD` must contain at least 16 characters.
- `DJANGO_SECRET_KEY` must contain at least 32 characters.
- `CERTBOT_EMAIL` is required when HTTPS is enabled.

Keep these fixed application identity values unchanged:

```text
APP_NAME=chikooza
APP_USER=chikooza
APP_GROUP=chikooza
INSTALL_ROOT=/srv/chikooza
```

For a PostgreSQL database managed on this VPS, keep:

```text
MANAGE_DATABASE=true
PG_MAJOR=16
DB_NAME=chikooza
DB_USER=chikooza
DB_HOST=127.0.0.1
DB_PORT=5432
```

For the first HTTPS deployment, keep staging enabled:

```text
ENABLE_CERTBOT=true
CERTBOT_STAGING=true
```

The staging certificate is intentionally not trusted by browsers. It verifies
DNS, ports, Nginx, and the Certbot challenge without consuming production
certificate limits.

AI configuration is optional:

```text
GROQ_API_KEY=
GROQ_API_KEYS=
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODEL=
```

Leave the keys blank for retrieval-only fallbacks. Additional supported Django
settings can be passed as `ENV__NAME=value`; the launcher removes `ENV__`
before passing the setting to Django.

## 7. Configure a Private Repository Key When Required

Skip this step for a public HTTPS `REPO_URL`.

If Section 3's private-repository flow was used, the protected key is already
installed. Use the repository's SSH URL and key path in
`/etc/chikooza/server.env`:

```text
REPO_URL=git@github.com:RadianceVA/chikooza-api.git
GIT_SSH_KEY=/root/.ssh/chikooza_deploy
```

Confirm that the corresponding public key has read-only repository access.

## 8. Verify Configuration Permissions

Run:

```bash
sudo stat -c '%U:%G %a %n' /etc/chikooza/server.env
```

The expected ownership and mode are:

```text
root:root 600 /etc/chikooza/server.env
```

## 9. Run the First Deployment

From the operator checkout root, run exactly one bootstrap command:

```bash
sudo ./scripts/launchers/server-linux.sh bootstrap
```

`bootstrap` installs system dependencies, configures PostgreSQL and pgvector,
creates restricted application identities, fetches the configured branch,
builds the frontend, installs Python dependencies, runs Django checks and
`collectstatic`, backs up the database, runs migrations, loads chatbot
knowledge, installs systemd and Nginx, starts the application, and verifies
health.

Do not run `start` after a successful `bootstrap`; the application is already
running.

## 10. Check the Deployment

Show deployment and service status:

```bash
sudo ./scripts/launchers/server-linux.sh status
```

Run all configured health checks:

```bash
sudo ./scripts/launchers/server-linux.sh health
```

Follow application logs:

```bash
sudo ./scripts/launchers/server-linux.sh logs --follow
```

Press `Ctrl+C` to stop following logs. This does not stop the deployed
application.

With staging HTTPS enabled, the browser will not trust the temporary
certificate. The application URLs are still:

```text
API:   https://<API_DOMAIN>/
Admin: https://<API_DOMAIN>/admin/
UI:    https://<UI_DOMAIN>/
```

The launcher deploys the Django admin route and static assets. It does not
automatically create a Django superuser. An existing superuser remains in the
database across deployments.

## 11. Promote HTTPS to a Production Certificate

After the staging deployment and health checks succeed, reopen the config:

```bash
sudoedit /etc/chikooza/server.env
```

Change only:

```text
CERTBOT_STAGING=false
```

Apply the configuration and request the trusted production certificate:

```bash
sudo ./scripts/launchers/server-linux.sh deploy
```

Run health checks again:

```bash
sudo ./scripts/launchers/server-linux.sh health
```

## 12. Deploy Later Code or Supported Configuration Changes

The deployment launcher fetches `REPO_BRANCH` from `REPO_URL`. Push the intended
application commit to that branch before deploying it.

For the public operator checkout, update the deployment script before running
it. Set `DEPLOYMENT_BRANCH` to the same value used by `REPO_BRANCH`:

```bash
cd "$HOME/chikooza-bootstrap"
```

```bash
DEPLOYMENT_BRANCH=correct-version
```

```bash
git fetch origin "$DEPLOYMENT_BRANCH"
```

```bash
git switch "$DEPLOYMENT_BRANCH"
```

```bash
git pull --ff-only origin "$DEPLOYMENT_BRANCH"
```

For the root-owned private operator checkout, use its deploy key:

```bash
DEPLOYMENT_BRANCH=correct-version
```

```bash
sudo git \
  -C /opt/chikooza-bootstrap \
  -c core.sshCommand='ssh -i /root/.ssh/chikooza_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  fetch origin "$DEPLOYMENT_BRANCH"
```

```bash
sudo git -C /opt/chikooza-bootstrap switch "$DEPLOYMENT_BRANCH"
```

```bash
sudo git \
  -C /opt/chikooza-bootstrap \
  -c core.sshCommand='ssh -i /root/.ssh/chikooza_deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  pull --ff-only origin "$DEPLOYMENT_BRANCH"
```

```bash
cd /opt/chikooza-bootstrap
```

Deploy the configured branch:

```bash
sudo ./scripts/launchers/server-linux.sh deploy
```

`deploy` builds a staged release, creates a verified pre-migration database
backup, runs migrations, activates the release, restarts Gunicorn, reloads
Nginx, and verifies public and internal health. A separate `start` command is
not required.

`deploy` applies supported application environment, domain, Gunicorn, Nginx,
Certbot, and release-policy changes. It does not rotate the actual PostgreSQL
role password, migrate an existing database to another name or host, or perform
a PostgreSQL major-version upgrade. Changing `NODE_VERSION` requires another
`bootstrap`. Plan database identity, location, password, and major-version
changes as separate tested database operations before editing those values.

## 13. Start, Stop, Restart, and Roll Back

Stop the Gunicorn application service:

```bash
sudo ./scripts/launchers/server-linux.sh stop
```

Nginx remains running after `stop`, so the built UI may still load while API
requests fail. Start the already-installed Nginx and Gunicorn services with:

```bash
sudo ./scripts/launchers/server-linux.sh start
```

`start` reuses the installed configuration; it does not apply config-file
changes. Use `deploy` for those changes.

Restart Gunicorn and verify the existing deployment:

```bash
sudo ./scripts/launchers/server-linux.sh restart
```

`restart` does not regenerate or reload Nginx configuration.

Switch code and built assets to the previous release:

```bash
sudo ./scripts/launchers/server-linux.sh rollback
```

Rollback does not reverse database migrations or restore a database backup.
Schema-breaking releases require a separately tested database recovery plan.

## Command Summary

```text
First fresh server deployment:  sudo ./scripts/launchers/server-linux.sh bootstrap
Later deployment:               sudo ./scripts/launchers/server-linux.sh deploy
Health check:                   sudo ./scripts/launchers/server-linux.sh health
Status:                         sudo ./scripts/launchers/server-linux.sh status
Follow logs:                    sudo ./scripts/launchers/server-linux.sh logs --follow
Start an existing deployment:   sudo ./scripts/launchers/server-linux.sh start
Stop the application:           sudo ./scripts/launchers/server-linux.sh stop
Restart the application:        sudo ./scripts/launchers/server-linux.sh restart
Roll back code/assets:           sudo ./scripts/launchers/server-linux.sh rollback
```
