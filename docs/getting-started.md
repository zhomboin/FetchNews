# Getting Started

This guide explains how to start the current FetchNews stack locally and verify the engineering baseline that now exists in the repository.

## What You Can Validate Today

The current implementation can already validate these end-to-end behaviors:

- backend API starts and responds to health checks
- host PostgreSQL is used as the primary local database
- Alembic migrations create the schema
- login protects the admin console when auth is enabled
- whitelisted source ingestion can be triggered manually or by schedule
- normalized items, stories, drafts, and publish jobs are queryable
- publishing jobs can be created, dispatched, polled, retried, and written back
- operations summary exposes alerts, failure groups, and section/platform metrics

## Recommended Local Stack

Required local services:

- PostgreSQL running on the host machine
- Redis running either on the host or via Compose

Recommended startup path:

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

Important notes:

- Compose no longer starts a PostgreSQL container
- application containers connect to host PostgreSQL through `host.docker.internal`
- migrations should be run before the API, worker, and beat services start using the database

## Environment Setup

Create `.env` in the repo root and start from [.env.example](/D:/Code/Project/FetchNews/.env.example).

Key variables:

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_DATABASE_BOOTSTRAP_MODE=skip
APP_REDIS_URL=redis://localhost:6379/0
APP_AUTH_ENABLED=true
APP_AUTH_SECRET_KEY=change-this-before-exposing-the-console
APP_BOOTSTRAP_ADMIN_USERNAME=admin
APP_BOOTSTRAP_ADMIN_PASSWORD=admin-secret
VITE_API_BASE=http://localhost:8000
```

## Manual Startup Without Compose

1. Install backend dependencies.

```bash
python -m pip install -e .[dev]
```

2. Install frontend dependencies.

```bash
cd web
npm install
cd ..
```

3. Run migrations.

```bash
alembic upgrade head
```

4. Start the backend API.

```bash
uvicorn fetchnews.main:app --host 0.0.0.0 --port 8000 --reload
```

5. Start the worker.

```bash
celery -A fetchnews.tasks.worker.celery_app worker --loglevel=info
```

6. Start beat.

```bash
celery -A fetchnews.tasks.worker.celery_app beat --loglevel=info
```

7. Start the frontend.

```bash
cd web
npm run dev -- --host 0.0.0.0
```

## Validation Checklist

### 1. Health check

Open [http://localhost:8000/healthz](http://localhost:8000/healthz).

Expected response:

```json
{"status":"ok","service":"FetchNews"}
```

### 2. Auth config and login

Open [http://localhost:8000/auth/config](http://localhost:8000/auth/config).

Expected response when auth is enabled:

```json
{"auth_enabled":true}
```

Then open [http://localhost:5173](http://localhost:5173), log in with the bootstrap admin account, and confirm the console loads instead of the login screen.

### 3. Source catalog

Open [http://localhost:8000/sources](http://localhost:8000/sources) after logging in through the SPA or calling the endpoint with a token.

You should see enabled source specs such as:

- `github-trending`
- `arxiv-cs-ai`
- `openai-blog`
- `x-allowlist`

### 4. Manual ingest run

From the frontend, open [http://localhost:5173/ingestion](http://localhost:5173/ingestion) and trigger an ingest run.

Expected behavior:

- a new ingest run is created
- the run appears in the list automatically
- failures are isolated per source and visible in the run details

### 5. Story review and draft generation

Open [http://localhost:5173/stories](http://localhost:5173/stories), approve one or more stories, then go to [http://localhost:5173/articles](http://localhost:5173/articles) and generate a daily, weekly, or monthly digest.

Expected behavior:

- a draft is created or rebuilt
- the selected story scope is preserved
- variants for `wechat`, `x`, and `telegram` are available

### 6. Publishing and ops monitoring

From the draft center, create publish jobs and then open [http://localhost:5173](http://localhost:5173) to inspect the ops dashboard.

Expected behavior:

- publish jobs appear in the draft center and `/publish-jobs`
- failed jobs can be retried
- ops dashboard shows alerts, grouped failures, and platform metrics

## Verification Commands

Run these before claiming the environment is healthy:

```bash
python -m pytest
```

```bash
cd web
npm run test:run
```

```bash
cd web
npm run build
```
