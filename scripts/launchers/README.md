# Chikooza Launchers

Chikooza has two supported native workflows:

- `server-linux.sh` deploys the public application on one Ubuntu server.
- `local.sh` runs a local development instance on Linux, macOS, or Windows Git
  Bash. `local-windows.cmd` installs/opens Git Bash and forwards the same local
  commands.

These workflows do not use Docker. They intentionally share command names where
the operating systems support the same behavior, but local runs are not public
server deployments.

For copy-ready macOS PostgreSQL and SQLite startup commands, see
[`start.md`](start.md).

For the ordered fresh Ubuntu server procedure, see
[`start-linux.md`](start-linux.md).

## Local First Run

From the repository root on Linux, macOS, or Git Bash:

```bash
./scripts/launchers/local.sh bootstrap
```

From Command Prompt or PowerShell on Windows:

```bat
scripts\launchers\local-windows.cmd bootstrap
```

`bootstrap` checks or installs the required runtimes, creates local environment
files when absent, installs Python and Node dependencies, migrates the selected
local database, loads bundled chatbot knowledge, and starts Django and Vite. A
fresh environment defaults to SQLite; an existing `.env` is preserved. It
streams both logs until `Ctrl+C`, which stops both launcher-owned processes.

The first run downloads a substantial Python/AI dependency set and therefore
needs an internet connection and free disk space.

### Local Prerequisites

- Linux: an apt-based distribution whose `python3` package is 3.11 or newer,
  plus `sudo` when system packages are missing.
- macOS: a supported Homebrew installation; the launcher can install Homebrew,
  but its official installer may request administrator permission.
- Windows: Windows 10/11 with WinGet. The CMD launcher installs Git for Windows
  when possible; package installers may still display a UAC prompt.
- Supported runtimes are Python 3.11 or newer and Node.js `^20.19.0` or
  `>=22.12.0`. Setup installs the supported distribution Python on Linux,
  Python 3.12 on macOS/Windows, and Node.js 22 when needed.

### Local Commands

```text
bootstrap  Set up everything and start interactively
setup      Install/check dependencies and configure data without starting
start      Start Django and Vite interactively
stop       Stop only processes owned by this launcher
restart    Stop owned processes and start interactively
status     Show launcher-owned process status
logs       Show or follow local backend/frontend logs
health     Check owned processes, database readiness, and frontend HTTP
help       Show command help
```

The same command is passed after either launcher. For example:

```bash
./scripts/launchers/local.sh health
```

```bat
scripts\launchers\local-windows.cmd health
```

Optional local overrides:

```text
CHIKOOZA_LOCAL_VENV
CHIKOOZA_LOCAL_BACKEND_HOST
CHIKOOZA_LOCAL_BACKEND_PORT
CHIKOOZA_LOCAL_FRONTEND_HOST
CHIKOOZA_LOCAL_FRONTEND_PORT
CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE
CHIKOOZA_PYTHON
CHIKOOZA_NODE
```

Setup never overwrites an existing backend or frontend `.env`. On a fresh
checkout it creates a local SQLite configuration with
`CHIKOOZA_RAG_REQUIRE_PGVECTOR=False` and makes the frontend API URL match the
selected backend host and port.

For safety, setup and start accept only this checkout's `db1.sqlite3` by
default. An existing PostgreSQL or custom SQLite target is refused before any
migration, ingestion, or server start. Set
`CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE=true` only when that database is
deliberately safe for local use. Runtime URL variables are injected into Django
and Vite, so stale values in preserved env files cannot silently point the
running local UI at a different API.

For an intentionally safe existing PostgreSQL development database, explicitly
allow the custom target on each command:

```bash
CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE=true ./scripts/launchers/local.sh bootstrap
```

On macOS, `Connection refused` at `127.0.0.1:5432` usually means the Homebrew
PostgreSQL service is stopped. Start and verify the installed formula before
retrying; replace `postgresql@17` when a different formula version is installed:

```bash
brew services start postgresql@17
pg_isready -h 127.0.0.1 -p 5432
```

`pg_isready` only checks the service. It does not start PostgreSQL. The local
launcher manages Django and Vite but deliberately does not start or stop a
custom database service.

SQLite is a lightweight local fallback. It does not provide production
PostgreSQL/pgvector behavior or production process supervision. The local
launcher also never pulls Git changes, deploys publicly, or provides rollback;
`deploy`, `update`, and `rollback` are rejected there.

## Ubuntu Production Server

The production launcher supports only Ubuntu 24.04 with systemd and must be run
with root privileges. It installs and configures native packages: Python,
Node.js, PostgreSQL with pgvector, Gunicorn, Nginx, and optionally Certbot. It
does not install Docker.

Before bootstrap, provide:

- a clean Ubuntu 24.04 VPS with `sudo`, systemd, internet access, and ports 80
  and 443 available;
- DNS records for the API and UI domains pointing to that server;
- access to the Git repository, including an SSH deploy key for a private repo;
- strong database and Django secrets; and
- enough memory and disk for Python AI packages, frontend builds, releases, and
  database backups.

Install a protected configuration file:

```bash
sudo install -d -m 0750 /etc/chikooza
sudo install -m 0600 scripts/launchers/server.env.example /etc/chikooza/server.env
sudoedit /etc/chikooza/server.env
```

At minimum, set `REPO_URL`, `REPO_BRANCH`, `API_DOMAIN`, `UI_DOMAIN`,
`DB_PASSWORD`, `DJANGO_SECRET_KEY`, and the staged HTTPS `CERTBOT_EMAIL`. For a
private repository, configure `GIT_SSH_KEY`. HTTPS staging is enabled by
default; set `ENABLE_CERTBOT=false` explicitly only for a private, temporary
HTTP evaluation.

`APP_NAME`, `APP_USER`, and `APP_GROUP` are fixed to `chikooza`; changing them
is rejected. Provisioning creates separate unprivileged identities for each
role: `chikooza-build:chikooza-build` installs and builds an isolated release,
`chikooza:chikooza` runs Gunicorn, and the `chikooza-web` group gives the
service and Nginx only the shared file access they need. Dependency lifecycle
scripts run as the build user, and Django commands run as the application user;
neither runs as root.

Run the one-time server bootstrap:

```bash
sudo ./scripts/launchers/server-linux.sh bootstrap
```

Bootstrap installs system dependencies, prepares the managed PostgreSQL
database when enabled, creates the application user/directories, installs
systemd and Nginx configuration, and performs the first deployment.

### Server Commands

```text
bootstrap        Provision a fresh Ubuntu server and perform the first deploy
deploy           Fetch, build, migrate, switch release, restart, and verify
start            Start the systemd application service
stop             Stop the systemd application service
restart          Restart and verify the service
status           Show release, systemd, Nginx, and readiness status
logs [--follow]  Show journal logs, optionally following them
health           Check systemd, Nginx, and public API/UI readiness
rollback         Switch back to the previous code/assets release
config-template  Print a compatible configuration template
```

Examples:

```bash
sudo ./scripts/launchers/server-linux.sh deploy
sudo ./scripts/launchers/server-linux.sh logs --follow
sudo ./scripts/launchers/server-linux.sh health
sudo ./scripts/launchers/server-linux.sh rollback
```

The default config is `/etc/chikooza/server.env`. Use another protected file
with either form:

```bash
sudo ./scripts/launchers/server-linux.sh --config /secure/path/server.env deploy
sudo CHIKOOZA_CONFIG=/secure/path/server.env ./scripts/launchers/server-linux.sh deploy
```

Configuration is parsed as literal `KEY=value` data, not executed as shell
code. Do not add `export`, command substitutions, or shell expressions. Keys
prefixed with `ENV__` are passed to the Django service after the prefix is
removed, allowing additional application settings without editing the script.
Configuration changes are staged only by `bootstrap` or `deploy`; `start` and
`restart` reuse the already-installed release environment, Nginx site, and
systemd unit. `stop` and `logs` intentionally do not parse the config, so they
remain available when `/etc/chikooza/server.env` is missing or malformed.

Each deploy builds an isolated staged release under the unprivileged build
account, writes a root-only `.runtime.env` inside that release, runs Django
checks, creates a database backup, applies migrations, and stages candidate
Nginx and systemd configuration. Activation switches the code and environment
links together, restarts Gunicorn, reloads Nginx, and requires internal Django,
public Nginx API, and public Nginx UI checks to pass. If activation fails, the
former code link, environment link, Nginx site, and systemd unit are restored.

Every deployment creates a PostgreSQL custom-format backup before migrations,
validates it with `pg_restore --list`, and stores it under
`/srv/chikooza/backups` by default. The directory is root-only and backup files
are mode `0600`; `KEEP_DB_BACKUPS` controls local retention. These backups are
not an off-server disaster-recovery system.

Rollback switches code and built assets to the previous release while keeping
the current runtime environment and host configuration. It does **not** reverse
database migrations, and the launcher does not automate database restore. Test
a documented `pg_restore` procedure separately on a disposable database before
relying on it. Schema-breaking releases still require an operator-approved
recovery plan. Media, logs, and backups live in shared directories rather than
individual releases.

### HTTPS with Certbot

Certbot uses the Nginx webroot challenge; it does not let Certbot rewrite the
site configuration. After all configured DNS names resolve to the VPS and
ports 80/443 are reachable, test issuance against Let's Encrypt staging first:

```text
ENABLE_CERTBOT=true
CERTBOT_EMAIL=admin@example.com
CERTBOT_STAGING=true
```

Run `bootstrap` for a new server or `deploy` for an existing installation. The
staging certificate is intentionally not browser-trusted. After staging
succeeds, change only `CERTBOT_STAGING=false` and run another deployment:

```bash
sudo ./scripts/launchers/server-linux.sh deploy
```

That deployment requests the production certificate, installs the HTTPS Nginx
site, and enables the renewal timer and Nginx reload hook. Changing the config
without running `deploy` does not change the installed certificate or site.

### Operations Limits

- Firewall rules, cloud security groups, DNS, off-server backups, monitoring,
  and repository credentials remain operator responsibilities.
- The generated configuration assumes Nginx on this VPS terminates public TLS;
  upstream load-balancer/CDN TLS termination needs a separately reviewed proxy
  and trusted-header configuration.
- `MANAGE_DATABASE=false` can target an existing PostgreSQL service, but that
  service must already provide the required database/user and pgvector support.
- The server launcher is intentionally rejected on macOS, Windows, WSL, other
  Linux distributions, containers, and hosts without systemd.

## Health Endpoints

The API exposes public responses containing status labels only:

```text
GET /health/live   Django process liveness; does not query the database
GET /health/ready  Readiness; executes SELECT 1 against the configured database
GET /health/       Alias for readiness
```

Readiness returns HTTP 503 when the database is unavailable. These checks do
not validate Groq, email delivery, DNS, pgvector quality, or every application
workflow. The server `health` command additionally validates systemd and Nginx,
then reaches the API readiness route and UI through the public Nginx hostnames
resolved to loopback. This verifies the installed local proxy, TLS certificate,
and UI route (staging deliberately skips certificate trust), but not external
DNS, firewall, or internet reachability.

## Validation Scope

The shared local launcher has been exercised on macOS with existing runtimes
and dependencies, including start, health, runtime URL overrides, and clean
shutdown. Full package installation/bootstrap, the Windows Git Bash/WinGet
path, and the Linux apt path have not been run on their target systems in this
development environment. The production script has received Bash syntax,
help/template, and code-path checks, but a complete Ubuntu 24.04 bootstrap
covering apt, PostgreSQL/pgvector, systemd, Nginx, and Certbot has not been run
here. Rehearse it on a disposable Ubuntu 24.04 server, including a failed
deployment and a separate database restore, before using it for production.

## Older Scripts

The older scripts in the parent `scripts/` directory remain for compatibility
and historical reference. They are not the supported fresh-system workflows
described in this guide.
