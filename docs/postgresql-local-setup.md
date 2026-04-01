# Local PostgreSQL Setup

This document explains how to switch the local FetchNews environment from the current SQLite default to a local PostgreSQL database.

## 1. Where PostgreSQL Is Configured

Current database configuration entry points:

- [fetchnews/settings.py](/D:/Code/Project/FetchNews/fetchnews/settings.py)
- [.env.example](/D:/Code/Project/FetchNews/.env.example)
- [docker-compose.yml](/D:/Code/Project/FetchNews/docker-compose.yml)

The effective backend database setting is:

- `APP_DATABASE_URL`

It is loaded in [fetchnews/settings.py](/D:/Code/Project/FetchNews/fetchnews/settings.py) as `database_url`.

Recommended local default value:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
```

Important note:

- the current code already supports PostgreSQL URLs
- the current `docker-compose.yml` now assumes PostgreSQL is already running on the host machine
- the current schema initialization path is `Base.metadata.create_all(...)`
- there is no Alembic migration setup yet

## 2. Recommended Local PostgreSQL Connection

Recommended local connection string:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
```

If you use Docker for PostgreSQL on the same machine, `localhost:5432` is the simplest choice.

## 3. Python Dependency

To use PostgreSQL, make sure the Python environment includes a PostgreSQL driver.

Recommended driver:

- `psycopg` (psycopg 3)

If it is not already present in the environment, install it manually:

```bash
python -m pip install psycopg[binary]
```

If you prefer the older driver, this also works:

```bash
python -m pip install psycopg2-binary
```

## 4. Minimal Initialization SQL

At the current project stage, PostgreSQL initialization is minimal. The application creates tables on startup through SQLAlchemy metadata, so the database-side SQL only needs to create the user and database.

Recommended initialization SQL:

```sql
CREATE USER fetchnews WITH PASSWORD 'fetchnews';
CREATE DATABASE fetchnews OWNER fetchnews;
GRANT ALL PRIVILEGES ON DATABASE fetchnews TO fetchnews;
```

If the user already exists, use a safer sequence such as:

```sql
ALTER USER fetchnews WITH PASSWORD 'fetchnews';
```

Then create the database if needed.

## 5. Optional SQL For Future Work

These are not required for the current codebase, but are likely to be useful later.

### Optional extension for future vector search

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Do not run this unless your PostgreSQL instance already has `pgvector` installed.

### Optional extension for UUID / crypto helpers

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

This is not required by the current models.

## 6. How To Start PostgreSQL Locally

### Option A: Existing local PostgreSQL service

If PostgreSQL is already installed locally:

1. create the user and database with the SQL above
2. set `APP_DATABASE_URL` in `.env`
3. start the API / worker / beat / web processes


## 7. What To Change In This Repo

### Option 1: Local `.env`

Create or update `.env` in the repo root:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_REDIS_URL=redis://localhost:6379/0
APP_CORS_ORIGINS=["http://localhost:5173"]
```

This is the simplest local override.

### Option 2: `docker-compose.yml`

The repository now ships with a Compose setup that connects application containers to the PostgreSQL instance running on the host machine. The `api`, `worker`, and `beat` services point to:

```yaml
environment:
  APP_DATABASE_URL: ${APP_DATABASE_URL:-postgresql+psycopg://fetchnews:fetchnews@host.docker.internal:5432/fetchnews}
```

Important notes:

- inside Docker containers, `localhost` means the container itself, not your host machine
- for Docker Desktop on Windows, `host.docker.internal` is the correct hostname to reach the host PostgreSQL instance
- the Compose file also adds `host.docker.internal:host-gateway` as an extra host entry to improve compatibility
- if your local PostgreSQL uses different credentials or database names, override `APP_DATABASE_URL` before running Compose

Example override in a local `.env` file:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@host.docker.internal:5432/fetchnews
```

## 8. How Schema Initialization Works Today

Current behavior is defined in [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py):

- `create_engine_and_factory(...)` builds the SQLAlchemy engine
- `init_database(...)` calls `Base.metadata.create_all(bind=engine)`

This means:

- table creation is automatic on startup
- there is currently no separate SQL file for table DDL
- the only required manual SQL is database and user creation

## 9. Recommended Startup Order With PostgreSQL

1. start PostgreSQL on the host machine
2. create the database user and database
3. make sure the host PostgreSQL listens on `localhost:5432`
4. configure `APP_DATABASE_URL`
5. start Redis
6. start API
7. start Celery worker
8. start Celery beat
9. start frontend

## 10. Verification Steps

After switching to PostgreSQL, verify with:

1. check backend health:

```bash
curl http://localhost:8000/healthz
```

2. trigger one ingest run:

```bash
curl -X POST http://localhost:8000/ingest/run   -H "Content-Type: application/json"   -d '{"source_slugs":["github-trending","openai-blog"]}'
```

3. confirm tables were created in PostgreSQL:

- `sources`
- `ingest_runs`
- `raw_items`
- `normalized_items`
- `stories`
- `article_drafts`
- `post_variants`
- `publish_jobs`

## 11. Current Caveats

- the app still uses `Base.metadata.create_all(...)` instead of migrations
- existing SQLite data is not migrated automatically
- there is no Alembic migration layer yet
- the host PostgreSQL instance must already be running before Compose starts
- switching an existing local environment from SQLite to PostgreSQL does not migrate old data automatically

## 12. Recommended Next Step

Once local PostgreSQL is confirmed working, the next engineering step should be:

1. introduce Alembic migrations
2. make PostgreSQL the primary production backend path formally
3. add health checks and readiness gates to Compose services
4. add backup / restore guidance for local and staging environments
