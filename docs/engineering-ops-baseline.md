# Engineering And Ops Baseline

This document summarizes the engineering and operations hardening that now exists in the repository.

## Included In This Baseline

### Alembic migrations

Implemented:

- Alembic config and environment files
- initial schema migration for the current SQLAlchemy model set
- explicit separation between `SQLite` test bootstrap and PostgreSQL migration flow

Key files:

- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)
- [alembic/env.py](/D:/Code/Project/FetchNews/alembic/env.py)
- [alembic/versions/20260401_0001_initial_schema.py](/D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py)
- [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py)

SQL boundary for this round:

- manual SQL is limited to creating the PostgreSQL role, database, and schema ownership
- application tables are created through Alembic, not pasted manually into `psql`
- see [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md) for the exact SQL block

### PostgreSQL formalization

Implemented:

- host PostgreSQL is the recommended local database path
- compose no longer assumes a PostgreSQL container
- explicit `APP_DATABASE_BOOTSTRAP_MODE` support
- `migrate` service for the compose workflow

Key files:

- [docker-compose.yml](/D:/Code/Project/FetchNews/docker-compose.yml)
- [.env.example](/D:/Code/Project/FetchNews/.env.example)
- [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### Login, permissions, and audit

Implemented:

- auth feature flag endpoint: `GET /auth/config`
- login endpoint: `POST /auth/login`
- current-user endpoint: `GET /auth/me`
- role-based access control for protected API routes
- bootstrap admin account via environment variables
- audit log persistence for key mutating operations

Current roles:

- `viewer`: read-only API access
- `editor`: review, generate, publish, and manual operational actions
- `admin`: full access, currently used for bootstrap login

Key files:

- [fetchnews/core/security.py](/D:/Code/Project/FetchNews/fetchnews/core/security.py)
- [fetchnews/core/audit.py](/D:/Code/Project/FetchNews/fetchnews/core/audit.py)
- [fetchnews/main.py](/D:/Code/Project/FetchNews/fetchnews/main.py)
- [fetchnews/models.py](/D:/Code/Project/FetchNews/fetchnews/models.py)

### Alerts and monitoring

Implemented:

- alerts in ops summary
- grouped recent failures
- platform metrics
- section review metrics
- recommendation feed
- frontend ops alert cards and drill-down support

Key files:

- [fetchnews/ops/service.py](/D:/Code/Project/FetchNews/fetchnews/ops/service.py)
- [web/src/features/ops/ops-dashboard-page.tsx](/D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx)

### Frontend test baseline

Implemented:

- `Vitest` test runner
- `Testing Library` setup
- API auth-header test
- login form submission test

Commands:

```bash
cd web
npm run test:run
```

Key files:

- [web/package.json](/D:/Code/Project/FetchNews/web/package.json)
- [web/vite.config.ts](/D:/Code/Project/FetchNews/web/vite.config.ts)
- [web/src/lib/api.test.ts](/D:/Code/Project/FetchNews/web/src/lib/api.test.ts)
- [web/src/features/auth/login-page.test.tsx](/D:/Code/Project/FetchNews/web/src/features/auth/login-page.test.tsx)

## Remaining Gaps

Still not fully implemented:

- user management UI and password reset flow
- audit-log inspection UI and export endpoints
- external alert delivery such as email, webhook, or Slack
- production monitoring stack such as Prometheus / Grafana or Sentry
- staged migration strategy for existing long-lived PostgreSQL environments
