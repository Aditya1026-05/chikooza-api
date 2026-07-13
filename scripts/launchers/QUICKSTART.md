# Chikooza Command Cheatsheet

Use the maintained launchers below. The older `deploy-*`, `test-all.*`, and
per-platform check scripts are retained only for historical compatibility.

## Local First Run

Linux, macOS, or Windows Git Bash:

```bash
./scripts/launchers/local.sh bootstrap
```

Windows Command Prompt or PowerShell:

```bat
scripts\launchers\local-windows.cmd bootstrap
```

The local launcher installs/checks runtimes and dependencies, prepares SQLite
for a fresh environment or preserves an existing database configuration, loads
bundled chatbot knowledge, and starts Django and Vite. Press `Ctrl+C` to stop
both launcher-owned processes. Existing non-default databases require the
explicit safety override documented in `scripts/launchers/README.md`.

Common local commands:

```bash
./scripts/launchers/local.sh setup
./scripts/launchers/local.sh start
./scripts/launchers/local.sh stop
./scripts/launchers/local.sh status
./scripts/launchers/local.sh logs
./scripts/launchers/local.sh health
```

## Ubuntu Production Server

Install and edit the protected configuration first:

```bash
sudo install -d -m 0750 /etc/chikooza
sudo install -m 0600 scripts/launchers/server.env.example /etc/chikooza/server.env
sudoedit /etc/chikooza/server.env
```

First deployment on Ubuntu 24.04:

```bash
sudo ./scripts/launchers/server-linux.sh bootstrap
```

Later deployments and operations:

```bash
sudo ./scripts/launchers/server-linux.sh deploy
sudo ./scripts/launchers/server-linux.sh status
sudo ./scripts/launchers/server-linux.sh logs --follow
sudo ./scripts/launchers/server-linux.sh health
sudo ./scripts/launchers/server-linux.sh rollback
```

The production launcher uses PostgreSQL/pgvector, Gunicorn, systemd, Nginx,
and optional Certbot. macOS and Windows launchers are local workflows, not
public production hosting.

Production identities are fixed: `chikooza-build` builds releases,
`chikooza` runs the service, and `chikooza-web` grants limited shared access to
Nginx. A deploy stages code, a root-only release environment, Nginx, and
systemd; failed activation restores the former code/environment/configuration.
Manual rollback changes code/assets but keeps the current runtime environment.
Database migrations are not reversed.

For HTTPS, first deploy with `ENABLE_CERTBOT=true` and
`CERTBOT_STAGING=true`. After that succeeds, set `CERTBOT_STAGING=false` and
run `deploy` again to obtain the production certificate through the Certbot
webroot flow.

Config edits apply only on `bootstrap` or `deploy`. `stop` and `logs --follow`
still work if the server config is broken. Pre-migration backups are root-only
and format-verified, but restoring one is a separate procedure that must be
tested before production use.

See `scripts/launchers/README.md` for configuration, safety checks,
troubleshooting, and platform limitations.
