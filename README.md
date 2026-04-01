# FetchNews

FetchNews is an AI news aggregation, review, and multi-platform distribution system for Chinese-speaking AI practitioners.

## Current State

The repository is no longer just a planning shell. It now supports a working internal pipeline:

- ingest whitelisted sources on a schedule or on demand
- persist raw items
- normalize, deduplicate, cluster, and score stories
- generate daily, weekly, and monthly drafts
- generate `wechat`, `x`, and `telegram` post variants
- review stories and drafts in the React admin console
- schedule publishing jobs, poll results, retry failures, and record feedback
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
- ops summary, diagnostics, and governance feedback loops

### Frontend

- `React SPA + Vite + TypeScript` admin console
- ingestion monitoring page
- stories review and filtering page
- article draft center and pre-publish review flow
- ops dashboard and drill-down views

### Content Strategy Features

- section-based story output
- section momentum feedback
- source governance feedback
- engagement-driven platform copy strategy
- weekly / monthly platform variants that also reflect section mix

## Key Docs

- Current implementation status: [docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)
- Architecture: [docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- Implementation roadmap: [docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- Master project plan: [docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)
- Project plan index: [docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- Getting started: [docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)
- Frontend style: [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- TypeScript style: [docs/typescript-style.md](/D:/Code/Project/FetchNews/docs/typescript-style.md)
- Content sources: [docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)

## Local Startup

Recommended startup path:

```bash
docker compose up api worker beat web redis
```

Then open:

- API: [http://localhost:8000](http://localhost:8000)
- Admin console: [http://localhost:5173](http://localhost:5173)
- Ingestion page: [http://localhost:5173/ingestion](http://localhost:5173/ingestion)

More details:

- [docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)

## Next High-Priority Work

- real external source connectors
- real publishing connectors for target platforms
- real LLM provider integration for summaries and long-form content
- pgvector / embedding-based similarity and retrieval
- Alembic migrations, auth, permissions, deployment, and monitoring hardening

## Encoding Rules

- all text files use `UTF-8` without `BOM`
- all text files use `LF` line endings
- enforced by [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) and [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes)
