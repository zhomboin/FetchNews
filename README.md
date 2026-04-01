# FetchNews

FetchNews is an AI news aggregation, review, and multi-platform distribution system for Chinese-speaking AI practitioners.

## Current State

The repository now supports a working internal workflow:

- ingest whitelisted sources on a schedule or on demand
- persist raw items
- normalize, deduplicate, cluster, and score stories
- generate daily, weekly, and monthly drafts
- generate `wechat`, `x`, and `telegram` post variants
- review stories and drafts in the React admin console
- schedule publishing jobs, poll results, retry failures, and record feedback
- protect the console with login, role-based access, and audit logging
- feed source governance, section momentum, and platform engagement back into ranking and copy strategy

Current phase status:

- `Phase 00` to `Phase 05`: baseline implementation completed
- `Phase 06`: in progress

For the detailed implementation snapshot, see:

- [docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)

## Implemented Capabilities

### Backend

- `FastAPI` application and REST API
- `SQLAlchemy` models and persistence layer
- `Celery + Redis` workers and scheduling
- source catalog, ingest runs, and raw item storage
- normalization and story clustering pipeline
- daily / weekly / monthly draft generation
- publishing job orchestration, result writeback, retries, and feedback recording
- auth config, login, current-user resolution, and route protection
- audit log persistence for key write operations
- ops summary, alerts, diagnostics, and governance feedback loops

### Frontend

- `React SPA + Vite + TypeScript` admin console
- login screen for protected environments
- ingestion monitoring page
- stories review and filtering page
- article draft center and pre-publish review flow
- ops dashboard, alerts, and drill-down views
- frontend test baseline with `Vitest` and Testing Library

### Data and Deployment

- Alembic migration baseline
- PostgreSQL-first local development path
- Docker Compose flow that targets host PostgreSQL
- explicit database bootstrap modes for `SQLite` vs `PostgreSQL`

## Key Docs

- Current implementation status: [docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)
- Architecture: [docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- Implementation roadmap: [docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- Master project plan: [docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)
- Project plan index: [docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- Getting started: [docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)
- Local PostgreSQL setup: [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)
- Engineering and ops baseline: [docs/engineering-ops-baseline.md](/D:/Code/Project/FetchNews/docs/engineering-ops-baseline.md)
- Frontend style: [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- TypeScript style: [docs/typescript-style.md](/D:/Code/Project/FetchNews/docs/typescript-style.md)
- Content sources: [docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)

## Local Startup

Recommended startup path when PostgreSQL is already running on the host machine:

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

Then open:

- API: [http://localhost:8000](http://localhost:8000)
- Admin console: [http://localhost:5173](http://localhost:5173)
- Ingestion page: [http://localhost:5173/ingestion](http://localhost:5173/ingestion)

Default bootstrap credentials in local development are controlled by environment variables:

- username: `APP_BOOTSTRAP_ADMIN_USERNAME`
- password: `APP_BOOTSTRAP_ADMIN_PASSWORD`

More details:

- [docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)

## Verification Commands

Backend:

```bash
python -m pytest
```

Frontend tests:

```bash
cd web
npm run test:run
```

Frontend build:

```bash
cd web
npm run build
```

## Next High-Priority Work

- real external source connectors
- real publishing connectors for target platforms
- real LLM provider integration for summaries and long-form content
- `pgvector` / embedding-based similarity and retrieval
- audit-log inspection views and stronger alert delivery channels

## Encoding Rules

- all text files use `UTF-8` without `BOM`
- all text files use `LF` line endings
- enforced by [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) and [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes)
