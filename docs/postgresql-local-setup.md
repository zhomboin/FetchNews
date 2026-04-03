# Local PostgreSQL Setup

This document explains how FetchNews now uses host PostgreSQL as the preferred local database and how Alembic fits into that flow.

## 1. Effective Database Settings

Primary configuration entry points:

- [fetchnews/settings.py](/D:/Code/Project/FetchNews/fetchnews/settings.py)
- [.env.example](/D:/Code/Project/FetchNews/.env.example)
- [docker-compose.yml](/D:/Code/Project/FetchNews/docker-compose.yml)
- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)

Key environment variables:

- `APP_DATABASE_URL`
- `APP_DATABASE_BOOTSTRAP_MODE`

Recommended local values:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_DATABASE_BOOTSTRAP_MODE=skip
```

Meaning:

- PostgreSQL is now the preferred local development database
- SQLAlchemy metadata bootstrap is still used automatically for `SQLite` and tests
- PostgreSQL paths should use Alembic migrations instead of `create_all`

## 2. Required SQL For This Round

If you are bootstrapping a fresh local PostgreSQL instance for the current codebase, these are the SQL statements you need to execute manually first:

```sql
CREATE USER fetchnews WITH PASSWORD 'fetchnews';
CREATE DATABASE fetchnews OWNER fetchnews;
GRANT ALL PRIVILEGES ON DATABASE fetchnews TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

If the role or database already exists, use the safer update path instead of recreating them:

```sql
ALTER USER fetchnews WITH PASSWORD 'fetchnews';
ALTER DATABASE fetchnews OWNER TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

Practical boundary for this round:

- the SQL above is the only database bootstrap SQL you are expected to run by hand
- table creation and later schema changes should go through Alembic
- the bootstrap admin account is created by application startup, not by manual SQL

Optional extensions for later phases:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Neither extension is required by the current codebase.

## 3. How Schema Initialization Works Now

Current behavior is defined in [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py).

Bootstrap modes:

- `create_all`: create tables from SQLAlchemy metadata
- `skip`: do not create tables automatically
- `auto`: use `create_all` for tests and `SQLite`, use `skip` for PostgreSQL

Recommended PostgreSQL path:

1. keep `APP_DATABASE_BOOTSTRAP_MODE=skip`
2. run `alembic upgrade head`
3. start the API, worker, and beat services

What happens after the manual SQL:

- `alembic upgrade head` applies the initial schema migration
- application startup ensures the bootstrap admin account exists when `APP_AUTH_ENABLED=true`
- you should not manually paste the full table DDL into `psql`

## 4. Alembic Commands

Initial migration assets now live in:

- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)
- [alembic/env.py](/D:/Code/Project/FetchNews/alembic/env.py)
- [alembic/versions/20260401_0001_initial_schema.py](/D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py)

Apply the schema:

```bash
alembic upgrade head
```

Check the current version:

```bash
alembic current
```

Create a new migration after schema changes:

```bash
alembic revision --autogenerate -m "describe change"
```

## 5. Compose Behavior

Compose now assumes PostgreSQL is already running on the host machine.

Application containers use:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@host.docker.internal:5432/fetchnews
```

Recommended sequence:

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

Important notes:

- `migrate` runs Alembic against the host PostgreSQL instance
- `api`, `worker`, and `beat` use `APP_DATABASE_BOOTSTRAP_MODE=skip`
- Compose no longer declares a PostgreSQL service

## 6. What Tables Exist After Migration

The initial migration creates at least these tables:

- `users`
- `audit_logs`
- `sources`
- `ingest_runs`
- `raw_items`
- `normalized_items`
- `stories`
- `article_drafts`
- `post_variants`
- `publish_jobs`
- `alembic_version`

## 7. Verification

After running migrations, verify with:

1. `alembic current`
2. `curl http://localhost:8000/healthz`
3. `python -m pytest`

If you want to verify the database directly in `psql`, these queries are sufficient:

```sql
\dt
SELECT version_num FROM alembic_version;
SELECT username, role, is_active FROM users ORDER BY id;
```

If the API starts but PostgreSQL has no tables, check these first:

- `APP_DATABASE_BOOTSTRAP_MODE` is not accidentally set to `skip` without running Alembic
- `APP_DATABASE_URL` points to the intended host database
- the local Python or container environment has `psycopg` available
