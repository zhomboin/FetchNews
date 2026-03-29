from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, PublishJob, PublishJobStatus
from fetchnews.schemas import PublishJobResponse


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
        )
        session.add(job)
        session.flush()
        jobs.append(publish_job_to_response(job))

    article.status = ArticleStatus.SCHEDULED
    session.flush()
    return jobs


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
        updated_at=job.updated_at,
    )


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