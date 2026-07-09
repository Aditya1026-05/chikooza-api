# Chikooza Scripts

These scripts are helper scripts for deployment and local validation.

## Production Linux VPS

Use this on an Ubuntu/Debian server such as a DigitalOcean droplet.

```bash
cp scripts/chikooza_deploy.env.example scripts/chikooza_deploy.env
nano scripts/chikooza_deploy.env
bash scripts/linux_vps_deploy.sh
```

The production script installs system packages, creates PostgreSQL database/user,
sets up the Django backend with Gunicorn/systemd, configures Nginx, builds the
React frontend, and optionally enables HTTPS through Certbot.

Do not commit `scripts/chikooza_deploy.env`; it contains secrets and is ignored
by Git.

## Local Checks

Linux:

```bash
bash scripts/linux_local_check.sh
```

macOS:

```bash
bash scripts/macos_local_check.sh
```

Windows PowerShell:

```powershell
.\scripts\windows_local_check.ps1
```

Windows Git Bash or WSL:

```bash
bash scripts/windows_git_bash_local_check.sh
```

The local scripts create a virtual environment, install backend dependencies, run
Django checks/tests, install frontend dependencies, and run the frontend build.
They do not configure Gunicorn or Nginx.
