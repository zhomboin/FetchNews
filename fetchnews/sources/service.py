from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import IngestRun, IngestRunStatus, RawItem, Source
from fetchnews.pipeline.service import run_story_pipeline
from fetchnews.schemas import IngestRunError, IngestRunResponse, RawIngestedItem, SourceSpec
from fetchnews.sources.catalog import get_source_specs
from fetchnews.sources.connectors import SourceConnector, build_default_connector_registry
from fetchnews.sources.real_connectors import FetchedSourceBatch


def execute_ingest_run(
    session: Session,
    source_slugs: list[str] | None = None,
    connector_registry: dict[str, SourceConnector] | None = None,
) -> IngestRun:
    source_specs = get_source_specs(source_slugs)
    registry = connector_registry or build_default_connector_registry()
    sources = _sync_sources(session, source_specs)

    run = IngestRun(
        requested_source_slugs=[spec.slug for spec in source_specs],
        status=IngestRunStatus.RUNNING,
        sources_total=len(source_specs),
        started_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()

    errors: list[dict[str, str]] = []
    succeeded = 0
    failed = 0
    items_ingested = 0

    for spec in source_specs:
        source = sources[spec.slug]
        connector = _resolve_connector(source, registry)
        if connector is None:
            failed += 1
            errors.append({"source_slug": spec.slug, "message": f"No connector configured for {source.platform}/{source.kind}"})
            continue

        try:
            fetched_batch = _normalize_fetched_batch(connector.fetch(source))
            items_ingested += _persist_raw_items(session, source, run, fetched_batch.items)
            if fetched_batch.next_cursor is not None:
                source.incremental_cursor = fetched_batch.next_cursor
            source.last_success_at = datetime.now(UTC)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append({"source_slug": spec.slug, "message": str(exc)})

    try:
        run_story_pipeline(session)
    except Exception as exc:
        errors.append({"source_slug": "pipeline", "message": str(exc)})

    run.sources_succeeded = succeeded
    run.sources_failed = failed
    run.items_ingested = items_ingested
    run.errors = errors
    run.finished_at = datetime.now(UTC)
    if not errors:
        run.status = IngestRunStatus.COMPLETED
    elif succeeded == 0:
        run.status = IngestRunStatus.FAILED
    else:
        run.status = IngestRunStatus.COMPLETED_WITH_ERRORS

    session.commit()
    session.refresh(run)
    return run


def ingest_run_to_response(run: IngestRun) -> IngestRunResponse:
    return IngestRunResponse(
        id=run.id,
        source_slugs=list(run.requested_source_slugs),
        status=run.status,
        sources_total=run.sources_total,
        sources_succeeded=run.sources_succeeded,
        sources_failed=run.sources_failed,
        items_ingested=run.items_ingested,
        errors=[IngestRunError(**error) for error in run.errors],
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _sync_sources(session: Session, source_specs: list[SourceSpec]) -> dict[str, Source]:
    existing_sources = {
        source.slug: source
        for source in session.scalars(select(Source).where(Source.slug.in_([spec.slug for spec in source_specs]))).all()
    }
    synced: dict[str, Source] = {}

    for spec in source_specs:
        source = existing_sources.get(spec.slug)
        if source is None:
            source = Source(
                slug=spec.slug,
                label=spec.label,
                platform=spec.platform,
                priority=spec.priority,
                kind=spec.kind,
                enabled=spec.enabled,
                config=dict(spec.config),
            )
            session.add(source)
        else:
            source.label = spec.label
            source.platform = spec.platform
            source.priority = spec.priority
            source.kind = spec.kind
            source.enabled = spec.enabled
            source.config = dict(spec.config)
        synced[spec.slug] = source

    session.flush()
    return synced


def _resolve_connector(source: Source, registry: dict[str, SourceConnector]) -> SourceConnector | None:
    return registry.get(source.slug) or registry.get(source.platform) or registry.get(source.kind)


def _normalize_fetched_batch(result: object) -> FetchedSourceBatch:
    if isinstance(result, FetchedSourceBatch):
        return result
    if isinstance(result, list):
        return FetchedSourceBatch(items=result)
    raise RuntimeError("Connector returned an unsupported fetch result")


def _persist_raw_items(session: Session, source: Source, run: IngestRun, items: list[RawIngestedItem]) -> int:
    now = datetime.now(UTC)
    for item in items:
        existing = session.scalar(
            select(RawItem).where(RawItem.source_id == source.id, RawItem.external_id == item.external_id)
        )
        if existing is None:
            session.add(
                RawItem(
                    source_id=source.id,
                    ingest_run_id=run.id,
                    external_id=item.external_id,
                    title=item.title,
                    url=item.url,
                    author=item.author,
                    published_at=item.published_at,
                    content=item.content,
                    payload=dict(item.metadata),
                    first_ingested_at=now,
                    last_ingested_at=now,
                )
            )
        else:
            existing.ingest_run_id = run.id
            existing.title = item.title
            existing.url = item.url
            existing.author = item.author
            existing.published_at = item.published_at
            existing.content = item.content
            existing.payload = dict(item.metadata)
            existing.last_ingested_at = now
    session.flush()
    return len(items)
