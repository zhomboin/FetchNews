from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import MockPublisherConnector, PublisherConnector
from fetchnews.schemas import PublishDispatchResponse, PublishJobResponse, PublishPollResponse
from fetchnews.settings import Settings


PublisherRegistry = dict[str, PublisherConnector]


def build_default_publisher_registry(settings: Settings | None = None) -> PublisherRegistry:
    resolved_settings = settings or Settings()
    connector = MockPublisherConnector(completion_delay_seconds=resolved_settings.mock_publish_completion_seconds)
    return {
        "wechat": connector,
        "x": connector,
        "telegram": connector,
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

        submission = connector.submit(job, article, variant)
        job.provider_job_id = submission.provider_job_id
        job.provider_payload = submission.provider_payload
        job.error_message = None
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
    else:
        job.error_message = error_message or "unknown publish failure"
    _sync_article_status(session, job.article_id)
    session.flush()
    return publish_job_to_response(job)


def retry_publish_job(session: Session, job: PublishJob) -> PublishJobResponse:
    job.retries += 1
    job.status = PublishJobStatus.SCHEDULED
    job.external_id = None
    job.error_message = None
    job.provider_job_id = None
    job.provider_payload = {}
    _sync_article_status(session, job.article_id)
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