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
9. protect the console with login, roles, audit logs, alerts, and migrations

Current phase status:

- `Phase 00`: completed
- `Phase 01`: completed
- `Phase 02`: baseline completed
- `Phase 03`: baseline completed
- `Phase 04`: baseline completed
- `Phase 05`: baseline completed
- `Phase 06`: in progress

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

### Phase 03: Normalize, Deduplicate, Cluster

Implemented:

- `normalized_items` storage
- canonical URL normalization
- title normalization
- story clustering and scoring
- risk flags
- manual story approval
- pipeline rebuild endpoint

### Phase 04: Content Generation

Implemented:

- daily digest generation
- weekly digest generation
- monthly digest generation
- digest generation for selected story sets
- persisted `generation_note`
- section-based article output
- platform variants for `wechat`, `x`, and `telegram`

### Phase 05: Review and Publishing

Implemented:

- pre-publish review inside the draft center
- publish job creation
- publish result writeback
- retry flow
- mock publish executor
- due-job dispatch and poll flow
- publish feedback writeback

### Phase 06: Optimization, Ops, and Hardening

Implemented:

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
- Alembic migration baseline
- PostgreSQL-first local path
- login, role-based access control, and bootstrap admin setup
- audit log persistence for key mutations
- ops alerts surfaced in the SPA
- frontend test baseline with `Vitest`

## Current Admin Pages

The React admin console now covers:

- `/`: ops dashboard
- `/ingestion`: ingestion runs and source governance
- `/stories`: story review, filtering, and risk view
- `/articles`: draft center, variant preview, and publish review
- `/publishing`: publishing-centric ops view
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

- user management UI and credential rotation flow
- audit-log browsing UI
- external alert delivery channels
- production monitoring stack
- staged database migration workflow for shared environments

## Recommended Next Plan

### Highest Priority

1. implement real external publishing connectors
2. strengthen real source connectors
3. integrate a real LLM provider for summaries and draft generation
4. extend alerting and audit-log inspection beyond the current baseline

### Mid-Term Improvements

1. add embedding-based similarity and retrieval
2. improve story and article explainability
3. keep feeding engagement signals into ranking, section mix, and platform strategy
4. add configurable section quotas for weekly and monthly digests

### Platform and Ops Hardening

1. add audit-log inspection views and filters
2. add external alert delivery
3. add richer operator history and change tracking
4. add deployment, backup, and restore runbooks
