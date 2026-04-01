# FetchNews Implementation Roadmap

## Phase Status Snapshot

As of `2026-04-01`, the implementation status is:

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| Phase 00 | Docs and Decisions | Completed | Planning, style, and collaboration baseline are in place |
| Phase 01 | Foundation | Completed | FastAPI, React SPA, Compose, and test baseline are in place |
| Phase 02 | Ingestion | Baseline completed | Source catalog, ingest runs, and raw item flow work |
| Phase 03 | Normalize and Cluster | Baseline completed | `normalized_items`, `stories`, rebuild, and review work |
| Phase 04 | Content Generation | Baseline completed | Daily / weekly / monthly drafts and variants work |
| Phase 05 | Review and Publishing | Baseline completed | Review flow, publish orchestration, retry, and feedback work |
| Phase 06 | Optimization and Operations | In progress | Governance, engagement feedback, and ops diagnostics are expanding |

## Phase 00: Docs and Decisions

Completed:

- architecture docs
- frontend style baseline
- TypeScript style guide
- project plan docs
- getting-started guide

## Phase 01: Foundation

Completed:

- backend package skeleton
- frontend SPA skeleton
- Docker Compose setup
- basic APIs
- verification baseline

## Phase 02: Ingestion

Baseline completed:

- source catalog
- ingest runs
- raw item persistence
- manual ingest trigger
- ingestion monitoring page
- default `Celery beat` schedule

Still to improve:

- more real source connectors
- stronger credential and rate-limit handling
- better source stability and recovery

## Phase 03: Normalize and Cluster

Baseline completed:

- normalized item storage
- URL normalization
- story clustering
- baseline scoring
- risk flags
- story approval flow

Still to improve:

- embedding-based similarity and recall
- better clustering explainability
- deeper source-risk explanations

## Phase 04: Content Generation

Baseline completed:

- daily / weekly / monthly digests
- generation for selected story scopes
- multi-platform variants
- section-based output
- platform strategy-driven copy templates

Still to improve:

- real LLM provider integration
- stronger citation traceability
- richer title, intro, tag, and cover generation

## Phase 05: Review and Publishing

Baseline completed:

- story review
- draft review
- publish jobs
- result writeback
- retries
- mock executor
- dispatch / poll workflow
- feedback recording

Still to improve:

- real platform publishers
- richer edit history and audit support
- webhook and callback style sync

## Phase 06: Optimization and Operations

Already implemented:

- ops dashboard
- failure grouping
- drill-down views
- source governance feedback
- section momentum feedback
- platform engagement feedback
- weekly / monthly section mix
- weekly / monthly variants that reflect both platform strategy and section mix

Next major goals:

1. real external connectors and publishers
2. LLM and embedding integration
3. production database migration and deployment setup
4. auth, permissions, alerting, and audit hardening

## Recommended Execution Order From Here

1. real `telegram / x / wechat` publishers
2. stronger `arXiv / RSS / community` ingestion connectors
3. `LLM provider + pgvector`
4. `Alembic + PostgreSQL + production deployment`
5. `auth / permissions / alerts / audit`

## Related Status Doc

For the full implementation snapshot, see:

- [docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)
