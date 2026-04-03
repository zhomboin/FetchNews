# FetchNews Editorial Workbench Design

## Goal

Extend the current draft center into a full editorial workbench that supports:

- finer weekly / monthly section quotas through reusable templates
- stronger platform copy strategy through selectable platform templates
- complete editorial history with paragraph-level locking, mixed rebuild, diff, and restore

This design keeps the current ingest, story, draft, publishing, and ops pipeline intact, while replacing the draft editing layer with a more structured editorial model.

## User Decisions

The design below is based on these confirmed choices:

- workbench structure: `B. three-column editorial workbench`
- rebuild policy: `mixed mode`
- edit granularity: `paragraph-level`
- weekly / monthly quota strategy: `template strategy`
- platform copy control: `selectable templates`

## Recommended Approach

Use a focused editorial model instead of stretching the current string-based draft model.

Introduce:

- digest templates for weekly / monthly section quotas
- block-level article editing for title, summary, intro, section blocks, and CTA blocks
- revision snapshots for every generate, edit, rebuild, restore, and template switch event
- editorial actions for audit-friendly human intervention history

This is the narrowest approach that can support paragraph-level locking, mixed rebuild, and restore without turning the current draft center into an unmaintainable string editor.

## Workbench Layout

The admin UI should adopt a three-column workbench:

### Left Rail: Strategy

Responsibilities:

- choose digest template
- preview section quotas and section order
- choose platform copy templates for `wechat`, `x`, and `telegram`
- configure rebuild scope
- trigger rebuild

This rail owns generation policy, not content editing.

### Center Rail: Paragraph Composer

Responsibilities:

- edit article blocks
- lock and unlock blocks
- reorder blocks
- review section composition
- inspect stale references before rebuild

This rail is the canonical content editing surface.

### Right Rail: History and Channels

Responsibilities:

- inspect revision history
- view revision diffs
- restore a previous revision into a new active revision
- preview and edit platform-specific blocks
- review publish readiness

This rail owns traceability and channel-specific content, not the main article flow.

## Data Model

### Existing Models to Keep

Keep these models as the stable backbone:

- `Story`
- `ArticleDraft`
- `PostVariant`
- `PublishJob`
- `AuditLog`

`ArticleDraft` remains the top-level draft record and publish target.

### New Models

#### `DigestTemplate`

Purpose:

- store reusable weekly / monthly editorial templates

Suggested fields:

- `id`
- `name`
- `period_type`
- `description`
- `section_quotas`
- `section_order`
- `default_platform_templates`
- `is_default`
- `created_at`
- `updated_at`

`section_quotas` should be stored as JSON, for example:

```json
{
  "research": 0.35,
  "open_source": 0.25,
  "product": 0.20,
  "signals": 0.20
}
```

#### `ArticleRevision`

Purpose:

- version every meaningful draft state

Suggested fields:

- `id`
- `article_id`
- `version_number`
- `change_type`
- `change_note`
- `template_id`
- `snapshot`
- `created_by_user_id`
- `created_at`

`snapshot` stores the serialized block state and selected platform templates for reliable restore.

#### `ArticleBlock`

Purpose:

- replace monolithic body editing with structured, paragraph-level editing

Suggested fields:

- `id`
- `article_id`
- `revision_id`
- `block_key`
- `block_type`
- `section_key`
- `platform_scope`
- `story_id`
- `title`
- `content`
- `sort_order`
- `is_locked`
- `is_manual`
- `metadata`
- `created_at`
- `updated_at`

Supported block types should include at least:

- `title`
- `summary`
- `intro`
- `section_heading`
- `story_paragraph`
- `section_wrapup`
- `cta`
- `platform_hook`
- `platform_body`
- `platform_cta`

#### `EditorialAction`

Purpose:

- record fine-grained human intervention history

Suggested fields:

- `id`
- `article_id`
- `revision_id`
- `actor_user_id`
- `action_type`
- `target_type`
- `target_id`
- `detail`
- `created_at`

Typical actions:

- `lock_block`
- `unlock_block`
- `edit_block`
- `move_block`
- `switch_digest_template`
- `switch_platform_template`
- `rebuild_article`
- `restore_revision`

## Generation and Rebuild Flow

### 1. Baseline Generation

When a draft is generated:

1. resolve the target `period_type`
2. resolve the selected or default digest template
3. rank candidate stories
4. apply section quotas and section ordering
5. emit article blocks
6. emit platform blocks from the selected platform templates
7. create `ArticleRevision(version 1)` or a new rebuild revision

### 2. Manual Editing

Editors do not edit a single `body` string directly.

Editors update `ArticleBlock` records:

- rewrite content
- lock or unlock a block
- move block order
- mark a block as manual override

The backend reassembles the full `body` and `PostVariant.content` from blocks when returning article detail and before publishing.

### 3. Mixed Rebuild

Mixed rebuild follows these rules:

- locked article blocks are preserved
- unlocked article blocks are regenerated
- locked platform blocks are preserved
- unlocked platform blocks are regenerated
- section quotas are reapplied only to unlocked content groups
- stale locked blocks that depend on removed stories are preserved but flagged with `stale_reference`

There should also be an explicit dangerous action for full rebuild:

- `force_full_rebuild`

This action ignores locks, but still creates a new revision instead of mutating history in place.

### 4. Restore

Restoring a revision should not overwrite history.

Instead:

1. copy the chosen revision snapshot
2. create a new revision with `change_type=restore`
3. make that new revision the active article state

This preserves a linear and auditable history.

## Template Strategy

### Digest Templates

Templates should be configurable for `weekly` and `monthly`.

Each template controls:

- section quotas
- preferred section order
- default platform templates
- optional notes for editors

Daily digests do not need the full quota system. They can keep using ranking-first behavior.

### Platform Templates

Editors choose a template per platform instead of free-form strategy text.

Suggested first template families:

- `wechat`
  - `editorial_summary`
  - `actionable_roundup`
- `x`
  - `tracking_hook`
  - `headline_push`
- `telegram`
  - `quick_bulletin`
  - `discussion_brief`

Templates define content structure, opening style, and CTA style, but still consume the same editorial block data.

## API Design

### Template APIs

- `GET /templates/digests`
- `POST /templates/digests`
- `PATCH /templates/digests/{id}`

### Draft Generation APIs

- `POST /articles/generate`
  - supports `period_type`, `target_date`, `story_ids`, `template_id`, `generation_note`
- `POST /articles/{id}/rebuild`
  - supports rebuild mode and optional block scopes

### Block Editing APIs

- `GET /articles/{id}/blocks`
- `PATCH /articles/{id}/blocks/{block_id}`
- `POST /articles/{id}/blocks/reorder`

### Revision APIs

- `GET /articles/{id}/revisions`
- `GET /articles/{id}/revisions/{revision_id}`
- `POST /articles/{id}/revisions/{revision_id}/restore`

### Editorial Audit APIs

- `GET /articles/{id}/editorial-actions`

## Frontend Design

The current `/articles` page should evolve into the editorial workbench instead of spawning a disconnected new tool.

Recommended UI composition:

- left rail: strategy controls and rebuild actions
- center rail: block editor
- right rail: revision history, diff preview, and platform blocks

Key interactions:

- click block to edit
- toggle lock inline
- drag or move block order
- switch digest template and preview quota impact
- switch platform template per channel
- compare revisions
- restore previous revision

The UI should preserve the existing `warm white metallic minimal` visual baseline.

## Error Handling

### Rebuild Safety

If a rebuild encounters blocks tied to removed stories:

- keep locked content
- mark the block as stale
- show a warning in the workbench
- require editor review before publishing

### Template Safety

If quotas do not sum cleanly:

- normalize quotas server-side
- return the normalized result in the response
- log an editorial action if the template was corrected automatically

### Revision Safety

Revision restore must fail safely when:

- target revision does not exist
- target article does not match
- snapshot is malformed

The current active revision must stay untouched in those cases.

## Testing Strategy

### Backend Tests

Add tests for:

- digest template validation and default selection
- weekly / monthly section quota application
- block generation from approved stories
- mixed rebuild preserving locked blocks
- force rebuild replacing locked blocks
- restore flow creating a new revision instead of mutating history
- article body and variant content assembly from blocks
- editorial action logging

### Frontend Tests

Add tests for:

- template selection and quota preview
- block lock and unlock interactions
- block edit and save flows
- revision list and restore action
- platform template switching
- mixed rebuild confirmation behavior

### Integration Tests

Add end-to-end API coverage for:

1. generate weekly digest from a template
2. lock intro and title blocks
3. edit one paragraph manually
4. rebuild draft
5. confirm locked blocks survive and unlocked blocks change
6. restore a previous revision
7. publish the restored current revision

## Risks

### Migration Complexity

The current `ArticleDraft.body` model is too coarse for paragraph-level editing. Moving to blocks will require:

- new tables
- backfill strategy for existing drafts
- careful API compatibility during transition

### UI Density

The workbench can become overloaded if every action is surfaced at once. The UI should keep the rails stable and progressively disclose advanced revision tools.

### Content Drift

Locked blocks may become semantically stale if stories are re-ranked or removed. This is why stale reference warnings must exist before publish.

### Restore Misuse

Editors may treat restore like destructive rollback. The system must preserve history by making restore additive.

## Phased Implementation

### Phase A: Data and Migration

- add `DigestTemplate`
- add `ArticleRevision`
- add `ArticleBlock`
- add `EditorialAction`
- add Alembic migrations
- backfill existing article drafts into an initial revision model

### Phase B: Template Engine

- build weekly / monthly template selection
- enforce section quota allocation
- expose template CRUD APIs
- keep current daily flow compatible

### Phase C: Block Editor and Mixed Rebuild

- generate article blocks
- edit and lock blocks
- rebuild unlocked blocks only
- reassemble article body and post variants from blocks

### Phase D: Revision History and Restore

- add revision list API
- add revision detail and diff API
- add restore flow
- add editorial action log browsing

### Phase E: UI Integration

- convert `/articles` into the three-column workbench
- add template rail
- add paragraph editor
- add revision and channel rail

## Recommendation

Proceed with the editorial model in this order:

1. data model and migrations
2. template strategy for weekly / monthly digests
3. block-based draft assembly
4. mixed rebuild
5. revision diff and restore
6. full workbench UI

That order delivers usable value early while keeping migration risk controlled.
