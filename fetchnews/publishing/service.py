from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import MockPublisherConnector, PublisherConnector
from fetchnews.publishing.platform_errors import classify_publish_failure
from fetchnews.publishing.real_publishers import RealTelegramPublisher
from fetchnews.schemas import PublishDispatchResponse, PublishJobResponse, PublishPollResponse
from fetchnews.settings import Settings


PublisherRegistry = dict[str, PublisherConnector]


def build_default_publisher_registry(settings: Settings | None = None) -> PublisherRegistry:
    resolved_settings = settings or Settings()
    connector = MockPublisherConnector(completion_delay_seconds=resolved_settings.mock_publish_completion_seconds)
    telegram_connector: PublisherConnector
    if resolved_settings.publish_real_platform == "telegram" and resolved_settings.telegram_bot_token:
        telegram_connector = RealTelegramPublisher(bot_token=resolved_settings.telegram_bot_token)
    else:
        telegram_connector = connector
    return {
        "wechat": connector,
        "x": connector,
        "telegram": telegram_connector,
    }


def create_publish_jobs(session: Session, article: ArticleDraft, platforms: list[str], scheduled_for) -> list[PublishJobResponse]:
    jobs: list[PublishJobResponse] = []
    for platform in platforms:
        job = PublishJob(
            article_id=article.id,
            platform=platform,
            scheduled_for=scheduled_for,
            status=PublishJobStatus.SCHEDULED,
            retries=0,
            external_id=None,
            error_message=None,
            provider_job_id=None,
            provider_payload={},
        )
        session.add(job)
        session.flush()
        job.dispatch_key = _build_dispatch_key(job)
        jobs.append(publish_job_to_response(job))

    article.status = ArticleStatus.SCHEDULED
    session.flush()
    return jobs


def dispatch_due_publish_jobs(
    session: Session,
    publisher_registry: PublisherRegistry,
    *,
    now: datetime | None = None,
    limit: int = 50,
) -> PublishDispatchResponse:
    dispatch_time = now or datetime.now(UTC)
    jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.status == PublishJobStatus.SCHEDULED)
        .where(PublishJob.scheduled_for <= dispatch_time)
        .where(PublishJob.provider_job_id.is_(None))
        .order_by(PublishJob.scheduled_for.asc(), PublishJob.id.asc())
        .limit(limit)
    ).all()

    jobs_dispatched = 0
    jobs_failed = 0
    for job in jobs:
        article = session.get(ArticleDraft, job.article_id)
        variant = session.scalar(
            select(PostVariant)
            .where(PostVariant.article_id == job.article_id)
            .where(PostVariant.platform == job.platform)
        )
        connector = publisher_registry.get(job.platform)

        if article is None or variant is None or connector is None:
            jobs_failed += 1
            write_publish_job_result(
                session,
                job,
                status=PublishJobStatus.FAILED,
                error_message=_resolve_dispatch_error(article, variant, connector),
            )
            continue

        if not job.dispatch_key:
            job.dispatch_key = _build_dispatch_key(job)
        submission = connector.submit(job, article, variant)
        job.provider_job_id = submission.provider_job_id
        job.provider_payload = submission.provider_payload
        job.error_message = None
        job.failure_category = None
        job.last_provider_status = "submitted"
        session.flush()
        jobs_dispatched += 1

    return PublishDispatchResponse(jobs_dispatched=jobs_dispatched, jobs_failed=jobs_failed)


def poll_publish_jobs(
    session: Session,
    publisher_registry: PublisherRegistry,
    *,
    limit: int = 50,
) -> PublishPollResponse:
    jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.status == PublishJobStatus.SCHEDULED)
        .where(PublishJob.provider_job_id.is_not(None))
        .order_by(PublishJob.scheduled_for.asc(), PublishJob.id.asc())
        .limit(limit)
    ).all()

    jobs_polled = 0
    jobs_completed = 0
    jobs_failed = 0
    for job in jobs:
        connector = publisher_registry.get(job.platform)
        if connector is None:
            jobs_polled += 1
            jobs_completed += 1
            jobs_failed += 1
            write_publish_job_result(
                session,
                job,
                status=PublishJobStatus.FAILED,
                error_message="missing publisher connector",
            )
            continue

        poll_result = connector.poll(job)
        jobs_polled += 1
        if not poll_result.terminal:
            continue

        jobs_completed += 1
        if poll_result.status == PublishJobStatus.FAILED:
            jobs_failed += 1

        write_publish_job_result(
            session,
            job,
            status=poll_result.status or PublishJobStatus.FAILED,
            external_id=poll_result.external_id,
            error_message=poll_result.error_message,
        )

    return PublishPollResponse(
        jobs_polled=jobs_polled,
        jobs_completed=jobs_completed,
        jobs_failed=jobs_failed,
    )


def handle_publish_callback(
    session: Session,
    platform: str,
    payload: dict[str, object],
    publisher_registry: PublisherRegistry,
) -> PublishJobResponse:
    connector = publisher_registry.get(platform)
    if connector is None:
        raise ValueError("publisher connector not configured")

    provider_job_id = str(payload.get("provider_job_id") or "").strip()
    if not provider_job_id:
        raise ValueError("provider_job_id is required")

    job = session.scalar(select(PublishJob).where(PublishJob.provider_job_id == provider_job_id))
    if job is None:
        raise ValueError("publish job not found")

    callback_result = connector.handle_callback(job, payload)
    job.last_provider_status = str(payload.get("status") or job.last_provider_status or "")
    if not callback_result.terminal:
        session.flush()
        return publish_job_to_response(job)

    return write_publish_job_result(
        session,
        job,
        status=callback_result.status or PublishJobStatus.FAILED,
        external_id=callback_result.external_id,
        error_message=callback_result.error_message,
    )


def write_publish_job_result(
    session: Session,
    job: PublishJob,
    status: str,
    external_id: str | None = None,
    error_message: str | None = None,
) -> PublishJobResponse:
    job.status = status
    if status == PublishJobStatus.PUBLISHED:
        job.external_id = external_id
        job.error_message = None
        job.failure_category = None
    else:
        job.error_message = error_message or "unknown publish failure"
        job.failure_category = classify_publish_failure(job.error_message)
    _sync_article_status(session, job.article_id)
    session.flush()
    return publish_job_to_response(job)


def retry_publish_job(session: Session, job: PublishJob) -> PublishJobResponse:
    job.retries += 1
    job.status = PublishJobStatus.SCHEDULED
    job.external_id = None
    job.error_message = None
    job.provider_job_id = None
    job.failure_category = None
    job.last_provider_status = None
    job.provider_payload = {}
    _sync_article_status(session, job.article_id)
    session.flush()
    return publish_job_to_response(job)


def write_publish_job_feedback(
    session: Session,
    job: PublishJob,
    *,
    impressions: int | None = None,
    opens: int | None = None,
    clicks: int | None = None,
    interactions: int | None = None,
    metrics_recorded_at: datetime | None = None,
) -> PublishJobResponse:
    metrics: dict[str, int] = {}
    if impressions is not None:
        metrics["impressions"] = impressions
    if opens is not None:
        metrics["opens"] = opens
    if clicks is not None:
        metrics["clicks"] = clicks
    if interactions is not None:
        metrics["interactions"] = interactions

    job.performance_metrics = metrics
    job.metrics_recorded_at = metrics_recorded_at or datetime.now(UTC)
    session.flush()
    return publish_job_to_response(job)


def publish_job_to_response(job: PublishJob) -> PublishJobResponse:
    return PublishJobResponse(
        id=job.id,
        article_id=job.article_id,
        platform=job.platform,
        scheduled_for=job.scheduled_for,
        status=job.status,
        retries=job.retries,
        external_id=job.external_id,
        error_message=job.error_message,
        provider_job_id=job.provider_job_id,
        dispatch_key=job.dispatch_key,
        failure_category=job.failure_category,
        last_provider_status=job.last_provider_status,
        performance_metrics={str(key): int(value) for key, value in job.performance_metrics.items()},
        metrics_recorded_at=job.metrics_recorded_at,
        updated_at=job.updated_at,
    )


def _resolve_dispatch_error(
    article: ArticleDraft | None,
    variant: PostVariant | None,
    connector: PublisherConnector | None,
) -> str:
    if article is None:
        return "article draft not found"
    if variant is None:
        return "post variant not found"
    if connector is None:
        return "publisher connector not configured"
    return "unknown dispatch error"


def _build_dispatch_key(job: PublishJob) -> str:
    return f"dispatch-{job.platform}-{job.id}"


def _sync_article_status(session: Session, article_id: int) -> None:
    article = session.get(ArticleDraft, article_id)
    if article is None:
        return

    jobs = session.scalars(select(PublishJob).where(PublishJob.article_id == article_id)).all()
    if len(jobs) == 0:
        article.status = ArticleStatus.READY
        return

    statuses = {job.status for job in jobs}
    if statuses == {PublishJobStatus.PUBLISHED}:
        article.status = ArticleStatus.PUBLISHED
        return

    if PublishJobStatus.FAILED in statuses:
        article.status = ArticleStatus.FAILED
        return

    article.status = ArticleStatus.SCHEDULED
