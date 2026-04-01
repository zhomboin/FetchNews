# FetchNews Current Implementation Status

Updated: `2026-04-01`

## Overview

FetchNews is now a working internal prototype instead of a documentation-only repository. The core pipeline is available end to end:

1. ingest source content
2. persist raw items
3. normalize, deduplicate, cluster, and score
4. generate daily / weekly / monthly drafts
5. generate multi-platform variants
6. review content in the admin console
7. schedule publishing jobs, write back results, retry failures, and record feedback
8. feed source, section, and platform feedback back into ranking and copy strategy

Current phase status:

- `Phase 00`: completed
- `Phase 01`: completed
- `Phase 02`: baseline completed
- `Phase 03`: baseline completed
- `Phase 04`: baseline completed
- `Phase 05`: baseline completed
- `Phase 06`: in progress

Here, "baseline completed" means the internal workflow runs, but not every production-grade or external integration requirement is done.

## What Is Already Implemented

### Phase 00: Docs and Decisions

Implemented:

- architecture and planning documents
- frontend style baseline
- TypeScript conventions
- startup and validation guide
- collaboration and encoding rules

### Phase 01: Foundation

Implemented:

- `FastAPI` app entry
- database session and core models
- `React SPA` admin shell
- `Docker Compose` local orchestration
- backend and frontend verification baseline

### Phase 02: Ingestion

Implemented:

- source catalog
- ingest run persistence
- raw item persistence
- manual ingest trigger
- ingest monitoring page
- default `Celery beat` ingest schedule

Key endpoints:

- `GET /sources`
- `POST /ingest/run`
- `GET /ingest/runs`
- `GET /ingest/runs/{id}`

### Phase 03: Normalize, Deduplicate, Cluster

Implemented:

- `normalized_items` storage
- canonical URL normalization
- title normalization
- story clustering and scoring
- risk flags
- manual story approval
- pipeline rebuild endpoint

Key endpoints:

- `GET /normalized-items`
- `POST /pipeline/stories/rebuild`
- `GET /stories`
- `POST /stories/{id}/approve`

Frontend coverage:

- story list
- filtering by keyword and review state
- risk visualization
- review action

### Phase 04: Content Generation

Implemented:

- daily digest generation
- weekly digest generation
- monthly digest generation
- digest generation for selected story sets
- persisted `generation_note`
- section-based article output
- platform variants for `wechat`, `x`, and `telegram`

Key endpoints:

- `POST /articles/generate/daily`
- `POST /articles/generate/weekly`
- `POST /articles/generate/monthly`
- `GET /articles`
- `GET /articles/{id}`
- `GET /articles/{id}/variants`

Frontend coverage:

- draft list
- draft detail view
- long-form preview
- platform variant preview
- generation controls

### Phase 05: Review and Publishing

Implemented:

- pre-publish review inside the draft center
- publish job creation
- publish result writeback
- retry flow
- mock publish executor
- due-job dispatch and poll flow
- publish feedback writeback

Key endpoints:

- `POST /articles/{id}/publish`
- `GET /publish-jobs`
- `POST /publish-jobs/dispatch-due`
- `POST /publish-jobs/poll`
- `POST /publish-jobs/{id}/result`
- `POST /publish-jobs/{id}/retry`
- `POST /publish-jobs/{id}/feedback`

Note:

- the execution and polling workflow is in place
- real platform connectors are still pending

### Phase 06: Optimization and Operations

Already implemented in this phase:

- unified ops summary
- recent failure grouping
- retry suggestions
- section review metrics
- publish platform metrics
- ops drill-down views
- section momentum model
- source governance feedback
- engagement feedback flowing back into source ranking
- weekly / monthly section mix
- platform copy strategy driven by historical engagement
- weekly / monthly variants that combine platform strategy with section mix

Key endpoint:

- `GET /ops/summary`

Frontend coverage:

- ops dashboard
- platform / section / failure-source drill-down
- ingestion page governance indicators

## Current Admin Pages

The React admin console now covers:

- `/`: ops dashboard
- `/ingestion`: ingestion runs and source governance
- `/stories`: story review, filtering, and risk view
- `/articles`: draft center, variant preview, and publish review
- `/ops/details`: drill-down for sections, platforms, and failures

## Current Limitations

### Source Ingestion

Still missing or incomplete:

- robust real connectors for `arXiv`, `Hugging Face`, `Papers with Code`, `Reddit`, and `Hacker News`
- full credential and rate-limit handling
- stronger structure-change resilience and replay tools

### Content Understanding

Still missing or incomplete:

- real LLM provider integration
- `pgvector` / embedding-based clustering and recall
- stronger citation and explainability views
- richer ranking controls and editor-facing explanations

### Publishing

Still missing or incomplete:

- real `wechat`, `x`, and `telegram` publishing connectors
- webhook or callback integration for provider-side status sync
- production-grade external publish hardening

### Product and Engineering Foundation

Still missing or incomplete:

- authentication and permission control
- Alembic migrations
- production-first PostgreSQL setup as the main path
- dedicated frontend test baseline
- fuller monitoring, alerting, and audit support

## Recommended Next Plan

### Highest Priority

1. implement real external publishing connectors
2. strengthen real source connectors
3. integrate a real LLM provider for summaries and draft generation
4. formalize database migrations and deployment setup

### Mid-Term Improvements

1. add embedding-based similarity and retrieval
2. improve story and article explainability
3. keep feeding engagement signals into ranking, section mix, and platform strategy
4. add configurable section quotas for weekly and monthly digests

### Platform and Ops Hardening

1. add login and permissions
2. add frontend tests
3. add more alerting and diagnostics
4. add richer edit history and audit support
