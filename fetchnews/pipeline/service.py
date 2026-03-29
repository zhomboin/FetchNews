from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import NormalizedItemRecord, RawItem, Source, Story
from fetchnews.pipeline.clustering import cluster_items
from fetchnews.pipeline.normalize import normalize_raw_item
from fetchnews.schemas import NormalizedItem, RawIngestedItem


def run_story_pipeline(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(RawItem, Source)
        .join(Source, RawItem.source_id == Source.id)
        .order_by(RawItem.published_at.asc(), RawItem.id.asc())
    ).all()
    existing_normalized = {
        record.raw_item_id: record for record in session.scalars(select(NormalizedItemRecord)).all()
    }

    normalized_items: list[NormalizedItem] = []
    for raw_item, source in rows:
        normalized = normalize_raw_item(
            RawIngestedItem(
                source_slug=source.slug,
                external_id=raw_item.external_id,
                title=raw_item.title,
                url=raw_item.url,
                author=raw_item.author,
                published_at=raw_item.published_at,
                content=raw_item.content,
                metadata=raw_item.payload,
            ),
            source_priority=source.priority,
            source_config=source.config,
        ).model_copy(update={"raw_item_id": raw_item.id})
        normalized_items.append(normalized)
        _upsert_normalized_item(session, existing_normalized.get(raw_item.id), normalized)

    story_candidates = cluster_items(normalized_items)
    existing_stories = {story.story_key: story for story in session.scalars(select(Story)).all()}
    for candidate in story_candidates:
        _upsert_story(session, existing_stories.get(candidate.story_key), candidate)

    session.flush()
    return {"normalized_items": len(normalized_items), "stories": len(story_candidates)}


def _upsert_normalized_item(
    session: Session,
    existing: NormalizedItemRecord | None,
    item: NormalizedItem,
) -> None:
    if item.raw_item_id is None:
        raise ValueError("Normalized item is missing raw_item_id")

    if existing is None:
        session.add(
            NormalizedItemRecord(
                raw_item_id=item.raw_item_id,
                source_slug=item.source_slug,
                source_priority=item.source_priority,
                external_id=item.external_id,
                canonical_url=item.canonical_url,
                title=item.title,
                normalized_title=item.normalized_title,
                author=item.author,
                published_at=item.published_at,
                summary=item.summary,
                content=item.content,
                language=item.language,
                tags=item.tags,
                keywords=item.keywords,
                payload=item.metadata,
                updated_at=datetime.now(UTC),
            )
        )
        return

    existing.source_slug = item.source_slug
    existing.source_priority = item.source_priority
    existing.external_id = item.external_id
    existing.canonical_url = item.canonical_url
    existing.title = item.title
    existing.normalized_title = item.normalized_title
    existing.author = item.author
    existing.published_at = item.published_at
    existing.summary = item.summary
    existing.content = item.content
    existing.language = item.language
    existing.tags = item.tags
    existing.keywords = item.keywords
    existing.payload = item.metadata
    existing.updated_at = datetime.now(UTC)


def _upsert_story(session: Session, existing: Story | None, candidate) -> None:
    if existing is None:
        session.add(
            Story(
                story_key=candidate.story_key,
                cluster_title=candidate.cluster_title,
                summary=candidate.summary,
                highlights=candidate.highlights,
                source_links=candidate.source_links,
                tags=candidate.tags,
                risk_flags=candidate.risk_flags,
                score=candidate.score,
                item_count=candidate.item_count,
                first_seen_at=candidate.first_seen_at,
                last_seen_at=candidate.last_seen_at,
            )
        )
        return

    existing.cluster_title = candidate.cluster_title
    existing.summary = candidate.summary
    existing.highlights = candidate.highlights
    existing.source_links = candidate.source_links
    existing.tags = candidate.tags
    existing.risk_flags = candidate.risk_flags
    existing.score = candidate.score
    existing.item_count = candidate.item_count
    existing.first_seen_at = candidate.first_seen_at
    existing.last_seen_at = candidate.last_seen_at