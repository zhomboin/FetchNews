from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import IngestRun, IngestRunStatus, Story, StoryStatus
from fetchnews.pipeline.engagement import build_section_engagement_snapshots
from fetchnews.pipeline.sections import infer_sections_from_signals
from fetchnews.schemas import SourceSpec


@dataclass(slots=True)
class SourceGovernanceFeedback:
    failed_ingest_runs: int = 0
    pending_stories: int = 0
    flagged_stories: int = 0
    effective_trust_score: float | None = None
    effective_score_multiplier: float = 1.0
    governance_flags: list[str] = field(default_factory=list)
    ranking_penalty: float = 0.0

    def feedback_signals(self) -> dict[str, int | float]:
        return {
            "failed_ingest_runs": self.failed_ingest_runs,
            "pending_stories": self.pending_stories,
            "flagged_stories": self.flagged_stories,
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
    enriched_specs: list[SourceSpec] = []

    for spec in source_specs:
        feedback = feedback_by_slug[spec.slug]
        enriched_specs.append(
            spec.model_copy(
                update={
                    "effective_trust_score": feedback.effective_trust_score,
                    "effective_score_multiplier": feedback.effective_score_multiplier,
                    "feedback_signals": feedback.feedback_signals(),
                    "governance_flags": feedback.governance_flags,
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
    for story in stories:
        related_source_slugs = {tag for tag in story.tags if tag in source_slug_set}
        for slug in related_source_slugs:
            if story.status == StoryStatus.PENDING:
                pending_stories[slug] += 1
            if story.risk_flags:
                flagged_stories[slug] += 1

    feedback_by_slug: dict[str, SourceGovernanceFeedback] = {}
    for spec in source_specs:
        base_trust_score = _coerce_float(spec.config.get("trust_score"), DEFAULT_TRUST_SCORE)
        base_score_multiplier = _coerce_float(spec.config.get("score_multiplier"), DEFAULT_SCORE_MULTIPLIER)
        failed_count = failed_ingest_runs[spec.slug]
        pending_count = pending_stories[spec.slug]
        flagged_count = flagged_stories[spec.slug]

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

        feedback_by_slug[spec.slug] = SourceGovernanceFeedback(
            failed_ingest_runs=failed_count,
            pending_stories=pending_count,
            flagged_stories=flagged_count,
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


def _coerce_float(value: object, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback