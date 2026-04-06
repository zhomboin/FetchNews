from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, IngestRun, IngestRunStatus, PublishJob, PublishJobStatus, Story, StoryStatus
from fetchnews.pipeline.engagement import build_section_engagement_snapshots, resolve_story_primary_section
from fetchnews.publishing.platform_errors import classify_publish_failure
from fetchnews.schemas import (
    AlertRecordResponse,
    FailureGroupResponse,
    FeedbackRecommendationResponse,
    OpsSummaryResponse,
    PublishPlatformMetricResponse,
    SectionReviewMetricResponse,
)
from fetchnews.settings import Settings


def build_ops_summary(
    session: Session,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> OpsSummaryResponse:
    resolved_settings = settings or Settings()
    current_time = now or datetime.now(UTC)
    stories = session.scalars(select(Story).order_by(Story.score.desc(), Story.last_seen_at.desc(), Story.id.desc())).all()
    recent_failure_groups = _build_failure_groups(session)
    publish_platform_metrics = _build_publish_platform_metrics(session)
    section_engagement = build_section_engagement_snapshots(session)
    section_review_metrics = _build_section_review_metrics(stories, section_engagement)
    source_failure_alerts = _build_source_failure_alerts(
        session,
        threshold=resolved_settings.source_failure_alert_threshold,
    )

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

    engagement_impressions_total = sum(metric.engagement_impressions for metric in publish_platform_metrics)
    engagement_opens_total = sum(metric.engagement_opens for metric in publish_platform_metrics)
    engagement_clicks_total = sum(metric.engagement_clicks for metric in publish_platform_metrics)
    engagement_interactions_total = sum(metric.engagement_interactions for metric in publish_platform_metrics)

    feedback_recommendations = _build_feedback_recommendations(
        section_review_metrics=section_review_metrics,
        publish_platform_metrics=publish_platform_metrics,
        failure_groups=recent_failure_groups,
    )

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
        engagement_impressions_total=engagement_impressions_total,
        engagement_opens_total=engagement_opens_total,
        engagement_clicks_total=engagement_clicks_total,
        engagement_interactions_total=engagement_interactions_total,
        alerts=_build_alerts(
            ingest_runs_failed=ingest_runs_failed,
            publish_jobs_failed=publish_jobs_failed,
            due_publish_jobs=due_publish_jobs,
            stories_pending=stories_pending,
            recent_failure_groups=recent_failure_groups,
            source_failure_alerts=source_failure_alerts,
        ),
        recent_failure_groups=recent_failure_groups,
        publish_platform_metrics=publish_platform_metrics,
        section_review_metrics=section_review_metrics,
        feedback_recommendations=feedback_recommendations,
    )


def _build_alerts(
    *,
    ingest_runs_failed: int,
    publish_jobs_failed: int,
    due_publish_jobs: int,
    stories_pending: int,
    recent_failure_groups: list[FailureGroupResponse],
    source_failure_alerts: list[AlertRecordResponse],
) -> list[AlertRecordResponse]:
    alerts: list[AlertRecordResponse] = []

    if publish_jobs_failed > 0:
        alerts.append(
            AlertRecordResponse(
                severity="critical",
                category="publish",
                title="Publish failures need operator attention",
                summary=f"{publish_jobs_failed} publish jobs are currently in a failed state.",
                suggestion="Inspect the failed platform jobs first, verify credentials or moderation status, then retry only the affected jobs.",
                count=publish_jobs_failed,
            )
        )

    if ingest_runs_failed > 0:
        alerts.append(
            AlertRecordResponse(
                severity="warning",
                category="ingest",
                title="Source ingestion is unstable",
                summary=f"{ingest_runs_failed} ingest runs recently finished with errors.",
                suggestion="Review the failing connectors, confirm rate limits or feed health, and rerun only the affected sources.",
                count=ingest_runs_failed,
            )
        )

    if due_publish_jobs > 0:
        alerts.append(
            AlertRecordResponse(
                severity="warning",
                category="schedule",
                title="Scheduled jobs are overdue",
                summary=f"{due_publish_jobs} publish jobs are due but still not completed.",
                suggestion="Dispatch due jobs, poll terminal states, and check worker health before queuing more posts.",
                count=due_publish_jobs,
            )
        )

    if stories_pending > 0:
        alerts.append(
            AlertRecordResponse(
                severity="info",
                category="review",
                title="Editorial review backlog is building",
                summary=f"{stories_pending} stories are still pending manual review.",
                suggestion="Clear flagged stories first so digest generation stays biased toward approved, primary-source coverage.",
                count=stories_pending,
            )
        )

    alerts.extend(source_failure_alerts)

    for group in recent_failure_groups[:2]:
        if not group.targets:
            continue
        alerts.append(
            AlertRecordResponse(
                severity="warning" if group.category == "ingest" else "critical",
                category=group.category,
                title=f"Repeated {group.category} failure: {group.reason}",
                summary=f"The latest grouped failures affected {', '.join(group.targets[:3])}.",
                target=group.targets[0],
                suggestion=group.suggestion,
                count=group.count,
            )
        )

    alerts.sort(key=lambda alert: (_alert_severity_rank(alert.severity), -alert.count, alert.category, alert.title))
    return alerts[:8]


def _build_source_failure_alerts(
    session: Session,
    *,
    threshold: int,
) -> list[AlertRecordResponse]:
    if threshold <= 0:
        return []

    source_failures: dict[str, dict[str, object]] = {}
    recent_failed_runs = session.scalars(
        select(IngestRun)
        .where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
        .order_by(IngestRun.finished_at.desc(), IngestRun.id.desc())
        .limit(10)
    ).all()

    for run in recent_failed_runs:
        for error in run.errors:
            source_slug = str(error.get("source_slug") or "").strip()
            if not source_slug or source_slug == "pipeline":
                continue
            entry = source_failures.setdefault(
                source_slug,
                {
                    "count": 0,
                    "latest_reason": str(error.get("message") or "unknown ingest failure"),
                },
            )
            entry["count"] = int(entry["count"]) + 1

    alerts: list[AlertRecordResponse] = []
    for source_slug, entry in sorted(source_failures.items(), key=lambda item: (-int(item[1]["count"]), item[0])):
        count = int(entry["count"])
        if count < threshold:
            continue
        latest_reason = str(entry["latest_reason"])
        alerts.append(
            AlertRecordResponse(
                severity="warning",
                category="source",
                title=f"Repeated source failures: {source_slug}",
                summary=f"{source_slug} failed {count} times in recent ingest runs.",
                target=source_slug,
                suggestion=_suggest_ingest_retry(latest_reason),
                count=count,
            )
        )
    return alerts


def _alert_severity_rank(severity: str) -> int:
    if severity == "critical":
        return 0
    if severity == "warning":
        return 1
    return 2


def _build_failure_groups(session: Session) -> list[FailureGroupResponse]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}

    recent_failed_jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.status == PublishJobStatus.FAILED)
        .order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())
        .limit(20)
    ).all()
    for job in recent_failed_jobs:
        reason = (job.failure_category or classify_publish_failure(job.error_message or "unknown publish failure")).strip()
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
                "engagement_impressions": 0,
                "engagement_opens": 0,
                "engagement_clicks": 0,
                "engagement_interactions": 0,
                "last_error": None,
                "last_failure_category": None,
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
            if entry["last_failure_category"] is None:
                entry["last_failure_category"] = (
                    job.failure_category or classify_publish_failure(job.error_message or "unknown publish failure")
                )

        metrics = job.performance_metrics or {}
        entry["engagement_impressions"] = int(entry["engagement_impressions"]) + _read_metric(metrics, "impressions")
        entry["engagement_opens"] = int(entry["engagement_opens"]) + _read_metric(metrics, "opens")
        entry["engagement_clicks"] = int(entry["engagement_clicks"]) + _read_metric(metrics, "clicks")
        entry["engagement_interactions"] = int(entry["engagement_interactions"]) + _read_metric(metrics, "interactions")

    ordered_entries = sorted(grouped.values(), key=lambda entry: (-int(entry["total_jobs"]), str(entry["platform"])))
    metrics: list[PublishPlatformMetricResponse] = []
    for entry in ordered_entries:
        terminal_jobs = int(entry["published_jobs"]) + int(entry["failed_jobs"])
        success_rate = int(entry["published_jobs"]) / terminal_jobs if terminal_jobs else 0.0
        impressions = int(entry["engagement_impressions"])
        clicks = int(entry["engagement_clicks"])
        interactions = int(entry["engagement_interactions"])
        metrics.append(
            PublishPlatformMetricResponse(
                platform=str(entry["platform"]),
                total_jobs=int(entry["total_jobs"]),
                scheduled_jobs=int(entry["scheduled_jobs"]),
                published_jobs=int(entry["published_jobs"]),
                failed_jobs=int(entry["failed_jobs"]),
                success_rate=success_rate,
                engagement_impressions=impressions,
                engagement_opens=int(entry["engagement_opens"]),
                engagement_clicks=clicks,
                engagement_interactions=interactions,
                click_through_rate=(clicks / impressions) if impressions else 0.0,
                interaction_rate=(interactions / impressions) if impressions else 0.0,
                last_error=str(entry["last_error"]) if entry["last_error"] is not None else None,
                last_failure_category=(
                    str(entry["last_failure_category"]) if entry["last_failure_category"] is not None else None
                ),
            )
        )
    return metrics


def _build_section_review_metrics(
    stories: list[Story],
    section_engagement: dict[str, object],
) -> list[SectionReviewMetricResponse]:
    grouped: dict[str, dict[str, int]] = {}

    for story in stories:
        primary_section = resolve_story_primary_section(story)
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

    metrics: list[SectionReviewMetricResponse] = []
    for section in sorted(set(grouped) | set(section_engagement)):
        counts = grouped.get(
            section,
            {
                "total_stories": 0,
                "approved_stories": 0,
                "pending_stories": 0,
                "flagged_stories": 0,
            },
        )
        engagement_snapshot = section_engagement.get(section)
        metrics.append(
            SectionReviewMetricResponse(
                section=section,
                label=getattr(engagement_snapshot, "label", section.replace("_", " ")),
                total_stories=counts["total_stories"],
                approved_stories=counts["approved_stories"],
                pending_stories=counts["pending_stories"],
                flagged_stories=counts["flagged_stories"],
                engagement_impressions=int(getattr(engagement_snapshot, "engagement_impressions", 0)),
                engagement_opens=int(getattr(engagement_snapshot, "engagement_opens", 0)),
                engagement_clicks=int(getattr(engagement_snapshot, "engagement_clicks", 0)),
                engagement_interactions=int(getattr(engagement_snapshot, "engagement_interactions", 0)),
                click_through_rate=float(getattr(engagement_snapshot, "click_through_rate", 0.0)),
                interaction_rate=float(getattr(engagement_snapshot, "interaction_rate", 0.0)),
                momentum_tier=str(getattr(engagement_snapshot, "momentum_tier", "steady")),
            )
        )
    return sorted(
        metrics,
        key=lambda metric: (
            _section_momentum_rank(metric.momentum_tier),
            -metric.flagged_stories,
            -metric.pending_stories,
            -metric.engagement_clicks,
            -metric.total_stories,
            metric.section,
        ),
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
        if signal_count > 0:
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
            continue

        if metric.momentum_tier == "cooling":
            recommendations.append(
                FeedbackRecommendationResponse(
                    category="section",
                    target=metric.section,
                    title=f"Engagement cooled in {metric.label}",
                    summary=(
                        f"{metric.label} is still getting distribution, but only {metric.engagement_clicks} clicks "
                        f"from {metric.engagement_impressions} impressions."
                    ),
                    suggestion=(
                        "Review headline framing and the story mix in this section before giving it more digest "
                        "surface area. Prioritize stronger primary-source angles or fresher developments."
                    ),
                    signal_count=max(metric.engagement_impressions // 100, 1),
                )
            )

    for metric in publish_platform_metrics:
        if metric.failed_jobs > 0:
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
        elif metric.engagement_impressions >= 200 and metric.click_through_rate < 0.03:
            recommendations.append(
                FeedbackRecommendationResponse(
                    category="platform",
                    target=metric.platform,
                    title=f"Engagement is weak on {metric.platform}",
                    summary=(
                        f"{metric.platform} is delivering impressions but only {metric.engagement_clicks} clicks from "
                        f"{metric.engagement_impressions} impressions."
                    ),
                    suggestion=(
                        "Review headline framing, posting cadence, and platform-specific copy. Keep the source mix stable, "
                        "but test stronger hooks before expanding distribution volume."
                    ),
                    signal_count=max(metric.engagement_clicks, 1),
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


def _section_momentum_rank(momentum_tier: str) -> int:
    if momentum_tier == "hot":
        return 0
    if momentum_tier == "rising":
        return 1
    if momentum_tier == "steady":
        return 2
    return 3


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
