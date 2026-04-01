# FetchNews Master Plan

## Overall Goal

Build an AI news production and distribution system for Chinese-speaking AI practitioners. The system should continuously ingest high-value sources, normalize and cluster content, generate daily / weekly / monthly drafts plus platform variants, support human review, and feed publish outcomes back into ranking, section strategy, and platform strategy.

## Current Program Status

Current status by phase:

- `Phase 00`: completed
- `Phase 01`: completed
- `Phase 02`: baseline completed
- `Phase 03`: baseline completed
- `Phase 04`: baseline completed
- `Phase 05`: baseline completed
- `Phase 06`: in progress

Detailed implementation status:

- [../current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)

## Phase Breakdown

### Phase 00: Docs and Decision Baseline

Goal:

- establish architecture, collaboration rules, and planning baseline

Status:

- completed

Doc:

- [phase-00-docs-and-decisions.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-00-docs-and-decisions.md)

### Phase 01: Foundation

Goal:

- backend skeleton
- frontend SPA skeleton
- local orchestration and verification baseline

Status:

- completed

Doc:

- [phase-01-foundation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-01-foundation.md)

### Phase 02: Ingestion

Goal:

- source catalog
- raw ingest persistence
- scheduling and monitoring

Status:

- baseline completed

Doc:

- [phase-02-ingestion.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-02-ingestion.md)

### Phase 03: Normalize and Cluster

Goal:

- normalization
- deduplication
- clustering
- scoring
- story review

Status:

- baseline completed

Doc:

- [phase-03-normalize-and-cluster.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-03-normalize-and-cluster.md)

### Phase 04: Content Generation

Goal:

- daily / weekly / monthly drafts
- platform variants
- section-based output

Status:

- baseline completed

Doc:

- [phase-04-content-generation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-04-content-generation.md)

### Phase 05: Review and Publishing

Goal:

- admin review flow
- publish jobs
- writeback, retries, feedback

Status:

- baseline completed

Note:

- the workflow is running internally, but real platform integrations are still pending

Doc:

- [phase-05-review-and-publishing.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-05-review-and-publishing.md)

### Phase 06: Optimization and Operations

Goal:

- source governance
- section momentum
- platform feedback loops
- ops diagnostics and optimization

Status:

- in progress

Already done in this phase:

- ops dashboard
- failure grouping
- platform metrics
- section momentum
- source governance feedback
- source engagement feedback in ranking
- weekly / monthly section mix
- engagement-driven platform copy strategy
- weekly / monthly variants that combine platform strategy and section mix

Doc:

- [phase-06-optimization-and-operations.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-06-optimization-and-operations.md)

## Milestones

Reached:

- milestone A: frontend and backend skeleton run locally
- milestone B: ingestion, persistence, and monitoring run locally
- milestone C: story clustering and draft generation run locally
- milestone D: review, publish orchestration, and feedback loop run locally

Still pending:

- milestone E: real source and real platform integrations are production-viable
- milestone F: LLM and vector capabilities enter the main workflow
- milestone G: deployment, security, migrations, and monitoring are production-ready

## Next Priorities

Recommended order:

1. real publishers
2. stronger real ingestion connectors
3. LLM and embedding integration
4. database migrations and deployment hardening
5. login, permissions, monitoring, and audit support
