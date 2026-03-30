from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, IngestRun, IngestRunStatus, PublishJob, PublishJobStatus, Story, StoryStatus
from fetchnews.pipeline.sections import get_section_label, infer_sections_from_signals
from fetchnews.schemas import (
    FailureGroupResponse,
    FeedbackRecommendationResponse,
    OpsSummaryResponse,
    PublishPlatformMetricResponse,
    SectionReviewMetricResponse,
)


def build_ops_summary(session: Session, now: datetime | None = None) -> OpsSummaryResponse:
    current_time = now or datetime.now(UTC)
    stories = session.scalars(select(Story).order_by(Story.score.desc(), Story.last_seen_at.desc(), Story.id.desc())).all()
    recent_failure_groups = _build_failure_groups(session)
    publish_platform_metrics = _build_publish_platform_metrics(session)
    section_review_metrics = _build_section_review_metrics(stories)

    ingest_runs_total = session.scalar(select(func.count()).select_from(IngestRun)) or 0
    ingest_runs_failed = session.scalar(
        select(func.count())
        .select_from(IngestRun)
        .where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
    ) or 0
    items_ingested_total = session.scalar(select(func.coalesce(func.sum(IngestRun.items_ingested), 0))) or 0
    stories_total = len(stories)
    stories_approved = sum(1 for story in stories if story.status == StoryStatus.APPROVED)
    stories_pending = sum(1 for story in stories if story.status == StoryStatus.PENDING)
    articles_total = session.scalar(select(func.count()).select_from(ArticleDraft)) or 0
    articles_ready = session.scalar(
        select(func.count())
        .select_from(ArticleDraft)
        .where(ArticleDraft.status.in_([ArticleStatus.READY, ArticleStatus.SCHEDULED]))
    ) or 0
    articles_published = session.scalar(
        select(func.count()).select_from(ArticleDraft).where(ArticleDraft.status == ArticleStatus.PUBLISHED)
    ) or 0
    articles_failed = session.scalar(
        select(func.count()).select_from(ArticleDraft).where(ArticleDraft.status == ArticleStatus.FAILED)
    ) or 0
    publish_jobs_total = session.scalar(select(func.count()).select_from(PublishJob)) or 0
    publish_jobs_scheduled = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.SCHEDULED)
    ) or 0
    publish_jobs_published = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.PUBLISHED)
    ) or 0
    publish_jobs_failed = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.FAILED)
    ) or 0
    terminal_jobs = publish_jobs_published + publish_jobs_failed
    publish_success_rate = publish_jobs_published / terminal_jobs if terminal_jobs else 0.0
    due_publish_jobs = session.scalar(
        select(func.count())
        .select_from(PublishJob)
        .where(PublishJob.status == PublishJobStatus.SCHEDULED)
        .where(PublishJob.scheduled_for <= current_time)
    ) or 0

    return OpsSummaryResponse(
        ingest_runs_total=ingest_runs_total,
        ingest_runs_failed=ingest_runs_failed,
        items_ingested_total=items_ingested_total,
        stories_total=stories_total,
        stories_approved=stories_approved,
        stories_pending=stories_pending,
        articles_total=articles_total,
        articles_ready=articles_ready,
        articles_published=articles_published,
        articles_failed=articles_failed,
        publish_jobs_total=publish_jobs_total,
        publish_jobs_scheduled=publish_jobs_scheduled,
        publish_jobs_published=publish_jobs_published,
        publish_jobs_failed=publish_jobs_failed,
        publish_success_rate=publish_success_rate,
        due_publish_jobs=due_publish_jobs,
        recent_failure_groups=recent_failure_groups,
        publish_platform_metrics=publish_platform_metrics,
        section_review_metrics=section_review_metrics,
        feedback_recommendations=_build_feedback_recommendations(
            section_review_metrics=section_review_metrics,
            publish_platform_metrics=publish_platform_metrics,
            failure_groups=recent_failure_groups,
        ),
    )


def _build_failure_groups(session: Session) -> list[FailureGroupResponse]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}

    recent_failed_jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.status == PublishJobStatus.FAILED)
        .order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())
        .limit(20)
    ).all()
    for job in recent_failed_jobs:
        reason = (job.error_message or "unknown publish failure").strip()
        key = ("publish", reason)
        entry = grouped.setdefault(
            key,
            {
                "category": "publish",
                "reason": reason,
                "count": 0,
                "targets": set(),
                "suggestion": _suggest_publish_retry(reason),
            },
        )
        entry["count"] = int(entry["count"]) + 1
        targets = entry["targets"]
        assert isinstance(targets, set)
        targets.add(job.platform)

    recent_failed_runs = session.scalars(
        select(IngestRun)
        .where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
        .order_by(IngestRun.finished_at.desc(), IngestRun.id.desc())
        .limit(10)
    ).all()
    for run in recent_failed_runs:
        for error in run.errors:
            reason = error.get("message", "unknown ingest failure").strip()
            key = ("ingest", reason)
            entry = grouped.setdefault(
                key,
                {
                    "category": "ingest",
                    "reason": reason,
                    "count": 0,
                    "targets": set(),
                    "suggestion": _suggest_ingest_retry(reason),
                },
            )
            entry["count"] = int(entry["count"]) + 1
            targets = entry["targets"]
            assert isinstance(targets, set)
            targets.add(error.get("source_slug", "unknown"))

    ordered_groups = sorted(
        grouped.values(),
        key=lambda entry: (-int(entry["count"]), str(entry["category"]), str(entry["reason"])),
    )
    return [
        FailureGroupResponse(
            category=str(entry["category"]),
            reason=str(entry["reason"]),
            count=int(entry["count"]),
            targets=sorted(str(target) for target in entry["targets"]),
            suggestion=str(entry["suggestion"]),
        )
        for entry in ordered_groups
    ]


def _build_publish_platform_metrics(session: Session) -> list[PublishPlatformMetricResponse]:
    jobs = session.scalars(select(PublishJob).order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())).all()
    grouped: dict[str, dict[str, object]] = {}

    for job in jobs:
        entry = grouped.setdefault(
            job.platform,
            {
                "platform": job.platform,
                "total_jobs": 0,
                "scheduled_jobs": 0,
                "published_jobs": 0,
                "failed_jobs": 0,
                "last_error": None,
            },
        )
        entry["total_jobs"] = int(entry["total_jobs"]) + 1
        if job.status == PublishJobStatus.SCHEDULED:
            entry["scheduled_jobs"] = int(entry["scheduled_jobs"]) + 1
        elif job.status == PublishJobStatus.PUBLISHED:
            entry["published_jobs"] = int(entry["published_jobs"]) + 1
        elif job.status == PublishJobStatus.FAILED:
            entry["failed_jobs"] = int(entry["failed_jobs"]) + 1
            if entry["last_error"] is None and job.error_message:
                entry["last_error"] = job.error_message

    ordered_entries = sorted(grouped.values(), key=lambda entry: (-int(entry["total_jobs"]), str(entry["platform"])))
    metrics: list[PublishPlatformMetricResponse] = []
    for entry in ordered_entries:
        terminal_jobs = int(entry["published_jobs"]) + int(entry["failed_jobs"])
        success_rate = int(entry["published_jobs"]) / terminal_jobs if terminal_jobs else 0.0
        metrics.append(
            PublishPlatformMetricResponse(
                platform=str(entry["platform"]),
                total_jobs=int(entry["total_jobs"]),
                scheduled_jobs=int(entry["scheduled_jobs"]),
                published_jobs=int(entry["published_jobs"]),
                failed_jobs=int(entry["failed_jobs"]),
                success_rate=success_rate,
                last_error=str(entry["last_error"]) if entry["last_error"] is not None else None,
            )
        )
    return metrics


def _build_section_review_metrics(stories: list[Story]) -> list[SectionReviewMetricResponse]:
    grouped: dict[str, dict[str, int]] = {}

    for story in stories:
        primary_section, _ = infer_sections_from_signals(
            title=story.cluster_title,
            summary=story.summary,
            tags=story.tags,
            source_hints=story.source_links,
        )
        entry = grouped.setdefault(
            primary_section,
            {
                "total_stories": 0,
                "approved_stories": 0,
                "pending_stories": 0,
                "flagged_stories": 0,
            },
        )
        entry["total_stories"] += 1
        if story.status == StoryStatus.APPROVED:
            entry["approved_stories"] += 1
        elif story.status == StoryStatus.PENDING:
            entry["pending_stories"] += 1
        if story.risk_flags:
            entry["flagged_stories"] += 1

    metrics = [
        SectionReviewMetricResponse(
            section=section,
            label=get_section_label(section),
            total_stories=counts["total_stories"],
            approved_stories=counts["approved_stories"],
            pending_stories=counts["pending_stories"],
            flagged_stories=counts["flagged_stories"],
        )
        for section, counts in grouped.items()
    ]
    return sorted(
        metrics,
        key=lambda metric: (-metric.flagged_stories, -metric.pending_stories, -metric.total_stories, metric.section),
    )


def _build_feedback_recommendations(
    *,
    section_review_metrics: list[SectionReviewMetricResponse],
    publish_platform_metrics: list[PublishPlatformMetricResponse],
    failure_groups: list[FailureGroupResponse],
) -> list[FeedbackRecommendationResponse]:
    recommendations: list[FeedbackRecommendationResponse] = []

    for metric in section_review_metrics:
        signal_count = metric.flagged_stories * 2 + metric.pending_stories
        if signal_count == 0:
            continue
        recommendations.append(
            FeedbackRecommendationResponse(
                category="section",
                target=metric.section,
                title=f"Review backlog in {metric.label}",
                summary=(
                    f"{metric.label} has {metric.pending_stories} pending stories and "
                    f"{metric.flagged_stories} flagged stories awaiting manual confirmation."
                ),
                suggestion=(
                    "Tighten source confirmation for this section, review risk flags first, and only promote "
                    "stories with strong primary-source coverage into digest generation."
                ),
                signal_count=signal_count,
            )
        )

    for metric in publish_platform_metrics:
        if metric.failed_jobs == 0:
            continue
        recommendations.append(
            FeedbackRecommendationResponse(
                category="platform",
                target=metric.platform,
                title=f"Publishing quality needs attention on {metric.platform}",
                summary=(
                    f"{metric.platform} recorded {metric.failed_jobs} failed jobs out of {metric.total_jobs} recent jobs."
                ),
                suggestion=(
                    f"Investigate the latest platform error ({metric.last_error or 'unknown error'}), retry only the "
                    "affected jobs, and reduce scheduling density if failures cluster in a short window."
                ),
                signal_count=metric.failed_jobs,
            )
        )

    for group in failure_groups:
        if group.category != "ingest" or not group.targets:
            continue
        target = group.targets[0]
        recommendations.append(
            FeedbackRecommendationResponse(
                category="source",
                target=target,
                title=f"Source connector instability: {target}",
                summary=f"Recent ingest failures were grouped under '{group.reason}'.",
                suggestion=group.suggestion,
                signal_count=group.count,
            )
        )

    return sorted(
        recommendations,
        key=lambda recommendation: (-recommendation.signal_count, recommendation.category, recommendation.target),
    )[:8]


def _suggest_publish_retry(reason: str) -> str:
    lowered = reason.lower()
    if "rate limit" in lowered or "limit" in lowered:
        return "Wait for the platform rate-limit window to recover, then retry the failed jobs in smaller batches."
    if "rejected" in lowered or "moderation" in lowered:
        return "Review moderation policy, account health, and post copy before re-queuing the job."
    if "credential" in lowered or "auth" in lowered or "token" in lowered:
        return "Repair platform credentials or authorization first, then retry the affected jobs."
    return "Inspect the publish logs, verify connector health, and retry only after the root cause is clear."


def _suggest_ingest_retry(reason: str) -> str:
    lowered = reason.lower()
    if "rate limit" in lowered or "limit" in lowered:
        return "Reduce ingest frequency, wait for source rate limits to clear, then rerun the source."
    if "timeout" in lowered or "timed out" in lowered:
        return "Check source availability and network stability, then rerun the connector after recovery."
    if "parse" in lowered or "schema" in lowered:
        return "Inspect connector parsing rules and field mappings before retrying the source."
    return "Inspect source configuration and connector logs, then retry after confirming the failure cause."