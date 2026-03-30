from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import NormalizedItemRecord, RawItem, Source, Story
from fetchnews.pipeline.clustering import cluster_items
from fetchnews.pipeline.normalize import normalize_raw_item
from fetchnews.schemas import NormalizedItem, RawIngestedItem
from fetchnews.sources.catalog import get_source_specs
from fetchnews.sources.governance import annotate_source_specs, build_section_governance_feedback, build_source_governance_feedback


def run_story_pipeline(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(RawItem, Source)
        .join(Source, RawItem.source_id == Source.id)
        .order_by(RawItem.published_at.asc(), RawItem.id.asc())
    ).all()
    existing_normalized = {
        record.raw_item_id: record for record in session.scalars(select(NormalizedItemRecord)).all()
    }

    source_specs = annotate_source_specs(session, get_source_specs())
    source_spec_by_slug = {spec.slug: spec for spec in source_specs}
    source_feedback = build_source_governance_feedback(session, source_specs)
    section_feedback = build_section_governance_feedback(session)

    normalized_items: list[NormalizedItem] = []
    for raw_item, source in rows:
        spec = source_spec_by_slug.get(source.slug)
        source_config = dict(source.config)
        if spec is not None:
            source_config["trust_score"] = spec.effective_trust_score
            source_config["score_multiplier"] = spec.effective_score_multiplier

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
            source_config=source_config,
        ).model_copy(update={"raw_item_id": raw_item.id})
        normalized = _apply_source_governance_feedback(normalized, source_feedback.get(source.slug))
        normalized_items.append(normalized)
        _upsert_normalized_item(session, existing_normalized.get(raw_item.id), normalized)

    story_candidates = cluster_items(normalized_items, section_feedback=section_feedback)
    existing_stories = {story.story_key: story for story in session.scalars(select(Story)).all()}
    for candidate in story_candidates:
        _upsert_story(session, existing_stories.get(candidate.story_key), candidate)

    session.flush()
    return {"normalized_items": len(normalized_items), "stories": len(story_candidates)}


def _apply_source_governance_feedback(
    item: NormalizedItem,
    feedback,
) -> NormalizedItem:
    if feedback is None:
        return item

    metadata = dict(item.metadata)
    quality_flags = {str(flag) for flag in metadata.get("source_quality_flags", []) if str(flag)}
    if feedback.governance_flags:
        quality_flags.add("governance_feedback")
    metadata["source_quality_flags"] = sorted(quality_flags)
    metadata["source_governance_flags"] = list(feedback.governance_flags)
    metadata["source_feedback_signals"] = feedback.feedback_signals()
    metadata["source_trust_score"] = feedback.effective_trust_score
    metadata["source_score_multiplier"] = feedback.effective_score_multiplier
    return item.model_copy(update={"metadata": metadata})


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