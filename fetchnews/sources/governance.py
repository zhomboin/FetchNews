from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, IngestRun, IngestRunStatus, PublishJob, PublishJobStatus, Source, Story, StoryStatus
from fetchnews.pipeline.engagement import build_section_engagement_snapshots
from fetchnews.pipeline.sections import infer_sections_from_signals
from fetchnews.schemas import SourceSpec


@dataclass(slots=True)
class SourceGovernanceFeedback:
    failed_ingest_runs: int = 0
    pending_stories: int = 0
    flagged_stories: int = 0
    engagement_impressions: int = 0
    engagement_clicks: int = 0
    engagement_interactions: int = 0
    effective_trust_score: float | None = None
    effective_score_multiplier: float = 1.0
    governance_flags: list[str] = field(default_factory=list)
    ranking_penalty: float = 0.0

    def feedback_signals(self) -> dict[str, int | float]:
        impressions = max(self.engagement_impressions, 0)
        click_through_rate = self.engagement_clicks / impressions if impressions else 0.0
        interaction_rate = self.engagement_interactions / impressions if impressions else 0.0
        return {
            "failed_ingest_runs": self.failed_ingest_runs,
            "pending_stories": self.pending_stories,
            "flagged_stories": self.flagged_stories,
            "engagement_impressions": self.engagement_impressions,
            "engagement_clicks": self.engagement_clicks,
            "engagement_interactions": self.engagement_interactions,
            "click_through_rate": round(click_through_rate, 4),
            "interaction_rate": round(interaction_rate, 4),
            "ranking_penalty": round(self.ranking_penalty, 2),
        }


@dataclass(slots=True)
class SectionGovernanceFeedback:
    score_penalty: float = 0.0
    score_boost: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    momentum_tier: str = "steady"


DEFAULT_TRUST_SCORE = 1.5
DEFAULT_SCORE_MULTIPLIER = 1.0


def annotate_source_specs(session: Session, source_specs: list[SourceSpec]) -> list[SourceSpec]:
    feedback_by_slug = build_source_governance_feedback(session, source_specs)
    persisted_sources = {
        source.slug: source
        for source in session.scalars(select(Source).where(Source.slug.in_([spec.slug for spec in source_specs]))).all()
    }
    enriched_specs: list[SourceSpec] = []

    for spec in source_specs:
        feedback = feedback_by_slug[spec.slug]
        persisted_source = persisted_sources.get(spec.slug)
        enriched_specs.append(
            spec.model_copy(
                update={
                    "effective_trust_score": feedback.effective_trust_score,
                    "effective_score_multiplier": feedback.effective_score_multiplier,
                    "feedback_signals": feedback.feedback_signals(),
                    "governance_flags": feedback.governance_flags,
                    "incremental_cursor": persisted_source.incremental_cursor if persisted_source is not None else None,
                    "last_success_at": persisted_source.last_success_at if persisted_source is not None else None,
                }
            )
        )
    return enriched_specs


def build_source_governance_feedback(
    session: Session,
    source_specs: list[SourceSpec],
) -> dict[str, SourceGovernanceFeedback]:
    source_slugs = [spec.slug for spec in source_specs]
    source_slug_set = set(source_slugs)
    failed_ingest_runs = {slug: 0 for slug in source_slugs}
    pending_stories = {slug: 0 for slug in source_slugs}
    flagged_stories = {slug: 0 for slug in source_slugs}
    engagement_impressions = {slug: 0.0 for slug in source_slugs}
    engagement_clicks = {slug: 0.0 for slug in source_slugs}
    engagement_interactions = {slug: 0.0 for slug in source_slugs}

    failed_runs = session.scalars(
        select(IngestRun).where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
    ).all()
    for run in failed_runs:
        seen_in_run: set[str] = set()
        for error in run.errors:
            slug = str(error.get("source_slug", "")).strip()
            if slug not in source_slug_set or slug in seen_in_run:
                continue
            failed_ingest_runs[slug] += 1
            seen_in_run.add(slug)

    stories = session.scalars(select(Story)).all()
    stories_by_id = {story.id: story for story in stories}
    for story in stories:
        related_source_slugs = {tag for tag in story.tags if tag in source_slug_set}
        for slug in related_source_slugs:
            if story.status == StoryStatus.PENDING:
                pending_stories[slug] += 1
            if story.risk_flags:
                flagged_stories[slug] += 1

    article_sources = _build_article_source_lookup(session, source_slug_set, stories_by_id)
    published_jobs = session.scalars(select(PublishJob).where(PublishJob.status == PublishJobStatus.PUBLISHED)).all()
    for job in published_jobs:
        related_source_slugs = article_sources.get(job.article_id, set())
        if not related_source_slugs:
            continue
        share_count = len(related_source_slugs)
        if share_count <= 0:
            continue

        metrics = job.performance_metrics or {}
        impressions_share = _read_metric(metrics, "impressions") / share_count
        clicks_share = _read_metric(metrics, "clicks") / share_count
        interactions_share = _read_metric(metrics, "interactions") / share_count
        for slug in related_source_slugs:
            engagement_impressions[slug] += impressions_share
            engagement_clicks[slug] += clicks_share
            engagement_interactions[slug] += interactions_share

    feedback_by_slug: dict[str, SourceGovernanceFeedback] = {}
    for spec in source_specs:
        base_trust_score = _coerce_float(spec.config.get("trust_score"), DEFAULT_TRUST_SCORE)
        base_score_multiplier = _coerce_float(spec.config.get("score_multiplier"), DEFAULT_SCORE_MULTIPLIER)
        failed_count = failed_ingest_runs[spec.slug]
        pending_count = pending_stories[spec.slug]
        flagged_count = flagged_stories[spec.slug]
        impressions = int(round(engagement_impressions[spec.slug]))
        clicks = int(round(engagement_clicks[spec.slug]))
        interactions = int(round(engagement_interactions[spec.slug]))

        governance_flags: list[str] = []
        if failed_count > 0:
            governance_flags.append("ingest_failures")
        if pending_count > 0 or flagged_count > 0:
            governance_flags.append("review_backlog")
        if flagged_count > 0:
            governance_flags.append("flagged_stories")

        ranking_penalty = failed_count * 1.4 + pending_count * 0.7 + flagged_count * 1.1
        effective_score_multiplier = max(
            base_score_multiplier - (failed_count * 0.08) - (pending_count * 0.05) - (flagged_count * 0.08),
            0.55,
        )
        effective_trust_score = max(base_trust_score - (failed_count * 0.6) - (pending_count * 0.25) - (flagged_count * 0.35), 0.0)

        engagement_multiplier_delta, engagement_trust_delta, engagement_penalty, engagement_flag = _classify_source_engagement(
            impressions=impressions,
            clicks=clicks,
            interactions=interactions,
        )
        effective_score_multiplier = max(min(effective_score_multiplier + engagement_multiplier_delta, 1.45), 0.55)
        effective_trust_score = max(effective_trust_score + engagement_trust_delta, 0.0)
        ranking_penalty = max(ranking_penalty + engagement_penalty, 0.0)
        if engagement_flag is not None and engagement_flag not in governance_flags:
            governance_flags.append(engagement_flag)

        feedback_by_slug[spec.slug] = SourceGovernanceFeedback(
            failed_ingest_runs=failed_count,
            pending_stories=pending_count,
            flagged_stories=flagged_count,
            engagement_impressions=impressions,
            engagement_clicks=clicks,
            engagement_interactions=interactions,
            effective_trust_score=round(effective_trust_score, 2),
            effective_score_multiplier=round(effective_score_multiplier, 2),
            governance_flags=governance_flags,
            ranking_penalty=round(ranking_penalty, 2),
        )

    return feedback_by_slug


def build_section_governance_feedback(session: Session) -> dict[str, SectionGovernanceFeedback]:
    section_counts: dict[str, dict[str, int]] = {}
    stories = session.scalars(select(Story)).all()

    for story in stories:
        section, _sections = infer_sections_from_signals(
            title=story.cluster_title,
            summary=story.summary,
            tags=story.tags,
            source_hints=story.source_links,
        )
        entry = section_counts.setdefault(section, {"pending": 0, "flagged": 0})
        if story.status == StoryStatus.PENDING:
            entry["pending"] += 1
        if story.risk_flags:
            entry["flagged"] += 1

    engagement_snapshots = build_section_engagement_snapshots(session)
    feedback: dict[str, SectionGovernanceFeedback] = {}
    for section in sorted(set(section_counts) | set(engagement_snapshots)):
        counts = section_counts.get(section, {"pending": 0, "flagged": 0})
        governance_penalty = counts["pending"] * 1.1 + counts["flagged"] * 1.6
        engagement_snapshot = engagement_snapshots.get(section)
        score_boost = engagement_snapshot.score_boost if engagement_snapshot is not None else 0.0
        score_penalty = governance_penalty + (engagement_snapshot.score_penalty if engagement_snapshot is not None else 0.0)

        risk_flags: list[str] = []
        if governance_penalty > 0:
            risk_flags.append("section_feedback_watch")
        if engagement_snapshot is not None and engagement_snapshot.score_penalty > 0:
            risk_flags.append("section_engagement_watch")

        highlights: list[str] = []
        if engagement_snapshot is not None and engagement_snapshot.score_boost > 0:
            highlights.append(
                f"Section momentum {engagement_snapshot.momentum_tier}: +{engagement_snapshot.score_boost:.1f}"
            )
        if engagement_snapshot is not None and engagement_snapshot.score_penalty > 0:
            highlights.append(
                f"Section engagement cooling: -{engagement_snapshot.score_penalty:.1f}"
            )

        if score_penalty <= 0 and score_boost <= 0 and not risk_flags and not highlights:
            continue

        feedback[section] = SectionGovernanceFeedback(
            score_penalty=round(score_penalty, 2),
            score_boost=round(score_boost, 2),
            risk_flags=risk_flags,
            highlights=highlights,
            momentum_tier=engagement_snapshot.momentum_tier if engagement_snapshot is not None else "steady",
        )

    return feedback


def _build_article_source_lookup(
    session: Session,
    source_slug_set: set[str],
    stories_by_id: dict[int, Story],
) -> dict[int, set[str]]:
    articles = session.scalars(select(ArticleDraft).order_by(ArticleDraft.id.asc())).all()
    article_sources: dict[int, set[str]] = {}
    for article in articles:
        related_sources: set[str] = set()
        for story_id in article.story_ids:
            story = stories_by_id.get(story_id)
            if story is None:
                continue
            related_sources.update(tag for tag in story.tags if tag in source_slug_set)
        if related_sources:
            article_sources[article.id] = related_sources
    return article_sources


def _classify_source_engagement(*, impressions: int, clicks: int, interactions: int) -> tuple[float, float, float, str | None]:
    if impressions <= 0:
        return 0.0, 0.0, 0.0, None

    click_through_rate = clicks / impressions
    interaction_rate = interactions / impressions
    if impressions >= 600 and (click_through_rate >= 0.08 or interaction_rate >= 0.05):
        return 0.08, 0.35, -0.5, "high_engagement"
    if impressions >= 250 and (click_through_rate >= 0.045 or interaction_rate >= 0.03):
        return 0.04, 0.2, -0.2, "steady_engagement"
    if impressions >= 250 and click_through_rate < 0.025 and interaction_rate < 0.02:
        return -0.06, -0.25, 0.9, "low_engagement"
    return 0.0, 0.0, 0.0, None


def _read_metric(metrics: dict[str, object], key: str) -> int:
    value = metrics.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _coerce_float(value: object, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback
