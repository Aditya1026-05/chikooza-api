# Local Start Commands

Run these commands from the repository root.

`bootstrap` performs setup and then starts Django and Vite. Do not run `start`
immediately after `bootstrap`; leave `bootstrap` running, or press `Ctrl+C` to
stop it before using a later-start command.

## PostgreSQL on macOS

These commands use the existing Homebrew PostgreSQL 17 installation. If a
different version is installed, replace `postgresql@17` with that formula.

### First Run

1. Start PostgreSQL:

```bash
brew services start postgresql@17
```

2. Confirm that PostgreSQL is accepting connections:

```bash
pg_isready -h 127.0.0.1 -p 5432
```

The expected result is:

```text
127.0.0.1:5432 - accepting connections
```

3. Set up the project and start Django and Vite:

```bash
CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE=true ./scripts/launchers/local.sh bootstrap
```

Keep that terminal open. Press `Ctrl+C` to stop Django and Vite.

### Later Starts

1. Ensure PostgreSQL is running:

```bash
brew services start postgresql@17
```

2. Confirm that it is ready:

```bash
pg_isready -h 127.0.0.1 -p 5432
```

3. Start Django and Vite:

```bash
CHIKOOZA_LOCAL_ALLOW_CUSTOM_DATABASE=true ./scripts/launchers/local.sh start
```

Stopping the application with `Ctrl+C` does not stop PostgreSQL. Stop the
database separately only when it is no longer needed:

```bash
brew services stop postgresql@17
```

## SQLite

SQLite does not require a separate database service.

### Fresh Environment First Run

If `.env` does not already select PostgreSQL, set up the project and start both
application services with:

```bash
./scripts/launchers/local.sh bootstrap
```

### Fresh Environment Later Starts

```bash
./scripts/launchers/local.sh start
```

### Existing `.env` Selects PostgreSQL

To use SQLite temporarily without editing the existing `.env`, override the
database only for the current command.

First setup and start:

```bash
DATABASE_URL= CHIKOOZA_RAG_REQUIRE_PGVECTOR=False ./scripts/launchers/local.sh bootstrap
```

Later starts:

```bash
DATABASE_URL= CHIKOOZA_RAG_REQUIRE_PGVECTOR=False ./scripts/launchers/local.sh start
```

PostgreSQL and SQLite contain separate data. Switching databases does not copy
users, farms, flocks, or other records between them.
