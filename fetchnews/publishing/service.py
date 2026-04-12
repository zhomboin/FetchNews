from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import MockPublisherConnector, PublisherConnector
from fetchnews.publishing.platform_errors import classify_publish_failure
from fetchnews.publishing.real_publishers import RealTelegramPublisher, RealWeChatPublisher, RealXPublisher
from fetchnews.schemas import PublishDispatchResponse, PublishJobResponse, PublishPollResponse
from fetchnews.settings import Settings


logger = logging.getLogger(__name__)

PLACEHOLDER_REAL_PLATFORMS: frozenset[str] = frozenset({"wechat", "x"})


PublisherRegistry = dict[str, PublisherConnector]


def build_default_publisher_registry(settings: Settings | None = None) -> PublisherRegistry:
    resolved_settings = settings or Settings()
    mock_connector = MockPublisherConnector(completion_delay_seconds=resolved_settings.mock_publish_completion_seconds)
    selected_platform = resolved_settings.publish_real_platform

    def uses_selected_platform(platform: str) -> bool:
        return selected_platform in (None, "", platform)

    telegram_connector: PublisherConnector = mock_connector
    if resolved_settings.telegram_bot_token and resolved_settings.telegram_chat_id and uses_selected_platform("telegram"):
        telegram_connector = RealTelegramPublisher(
            bot_token=resolved_settings.telegram_bot_token,
            chat_id=resolved_settings.telegram_chat_id,
        )

    wechat_connector: PublisherConnector = mock_connector
    if resolved_settings.wechat_app_id and uses_selected_platform("wechat"):
        wechat_connector = RealWeChatPublisher(app_id=resolved_settings.wechat_app_id)
        _warn_placeholder_real_publisher("wechat")

    x_connector: PublisherConnector = mock_connector
    if resolved_settings.x_bearer_token and uses_selected_platform("x"):
        x_connector = RealXPublisher(bearer_token=resolved_settings.x_bearer_token)
        _warn_placeholder_real_publisher("x")

    return {
        "wechat": wechat_connector,
        "x": x_connector,
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
    settings: Settings | None = None,
    now: datetime | None = None,
    limit: int = 50,
) -> PublishDispatchResponse:
    resolved_settings = settings or Settings()
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
    rate_limited_platforms: set[str] = set()
    for job in jobs:
        if job.platform in rate_limited_platforms or _platform_rate_limit_window_open(
            session,
            platform=job.platform,
            now=dispatch_time,
            cooldown_seconds=resolved_settings.publish_rate_limit_window_seconds,
        ):
            rate_limited_platforms.add(job.platform)
            job.last_provider_status = "rate_limited"
            session.flush()
            continue

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
        try:
            submission = connector.submit(job, article, variant)
        except Exception as exc:
            jobs_failed += 1
            job.last_provider_status = "submit_failed"
            write_publish_job_result(
                session,
                job,
                status=PublishJobStatus.FAILED,
                error_message=str(exc) or "publish submit failed",
            )
            continue
        job.provider_job_id = submission.provider_job_id
        job.provider_payload = _merge_dispatch_provider_payload(
            previous=job.provider_payload,
            submitted=submission.provider_payload,
        )
        job.error_message = None
        job.failure_category = None
        job.last_provider_status = str(submission.provider_payload.get("provider_status") or "submitted")
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

    job = session.scalar(
        select(PublishJob)
        .where(PublishJob.provider_job_id == provider_job_id)
        .where(PublishJob.platform == platform)
    )
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
        _clear_failure_window_state(job)
    else:
        job.error_message = error_message or "unknown publish failure"
        job.failure_category = classify_publish_failure(job.error_message)
        _record_failure_window_state(job)
    _sync_article_status(session, job.article_id)
    session.flush()
    return publish_job_to_response(job)


OPERATIONAL_PROVIDER_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "external_id",
        "provider_status",
        "poll_deadline_at",
    }
)


def retry_publish_job(session: Session, job: PublishJob) -> PublishJobResponse:
    preserved_failure_window_state = _extract_failure_window_state(job)
    archived_payload = _archive_provider_payload_for_retry(job)
    job.retries += 1
    job.status = PublishJobStatus.SCHEDULED
    job.external_id = None
    job.error_message = None
    job.provider_job_id = None
    job.failure_category = None
    job.last_provider_status = None
    job.provider_payload = {
        **archived_payload,
        **preserved_failure_window_state,
    }
    _sync_article_status(session, job.article_id)
    session.flush()
    return publish_job_to_response(job)


def _warn_placeholder_real_publisher(platform: str) -> None:
    """Emit a loud warning when a placeholder "real" publisher is wired in.

    ``RealWeChatPublisher`` / ``RealXPublisher`` today are skeletons: they do
    not call the actual external API. Operators that set
    ``APP_WECHAT_APP_ID`` / ``APP_X_BEARER_TOKEN`` need to know they are
    switching from a mock connector to a connector that *looks* real but
    still short-circuits submission. Without this log the switch is silent.
    """

    logger.warning(
        "using placeholder real publisher for %s: "
        "RealWeChatPublisher / RealXPublisher are skeletons and do not yet "
        "call the actual external API",
        platform,
    )


def _merge_dispatch_provider_payload(
    *,
    previous: dict[str, object] | None,
    submitted: dict[str, object],
) -> dict[str, object]:
    """Merge the freshly submitted payload with history from previous attempts.

    The freshly submitted payload from the connector is the source of truth for
    operational state (``dispatch_key``, ``poll_deadline_at``, ``external_id``,
    etc.). However we must not drop ``retry_history`` accumulated across retry
    attempts — otherwise an operator can't see what was tried before.
    """

    merged = dict(submitted)
    previous_payload = dict(previous or {})
    retry_history = previous_payload.get("retry_history")
    if isinstance(retry_history, list) and retry_history:
        merged["retry_history"] = [
            dict(entry) for entry in retry_history if isinstance(entry, dict)
        ]
    return merged


def _archive_provider_payload_for_retry(job: PublishJob) -> dict[str, object]:
    """Snapshot the current provider_payload into a history list before retry.

    The returned dict preserves the historical snapshot (under ``retry_history``)
    and drops only the operational keys that will be repopulated on the next
    dispatch. This keeps audit / debug visibility into prior attempts while
    ensuring the next ``dispatch_due_publish_jobs`` call starts from a clean
    operational state.
    """

    current_payload = dict(job.provider_payload or {})
    if not current_payload:
        return {}

    retry_history_raw = current_payload.pop("retry_history", None)
    retry_history: list[dict[str, object]] = []
    if isinstance(retry_history_raw, list):
        retry_history = [dict(entry) for entry in retry_history_raw if isinstance(entry, dict)]

    snapshot = {
        key: value
        for key, value in current_payload.items()
        if key not in {"last_failure_category", "last_failure_at"}
    }
    snapshot_entry: dict[str, object] = {
        "retries_before": job.retries,
        "provider_job_id": job.provider_job_id,
        "failure_category": job.failure_category,
        "error_message": job.error_message,
        "last_provider_status": job.last_provider_status,
        "payload": snapshot,
    }
    retry_history.append(snapshot_entry)

    cleaned = {
        key: value
        for key, value in current_payload.items()
        if key not in OPERATIONAL_PROVIDER_PAYLOAD_KEYS
    }
    cleaned["retry_history"] = retry_history
    return cleaned


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


def _platform_rate_limit_window_open(
    session: Session,
    *,
    platform: str,
    now: datetime,
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    window_opened_at = now - timedelta(seconds=cooldown_seconds)
    recent_jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.platform == platform)
        .order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())
        .limit(20)
    ).all()
    return any(_job_has_open_rate_limit_window(job, window_opened_at) for job in recent_jobs)


def _job_has_open_rate_limit_window(job: PublishJob, window_opened_at: datetime) -> bool:
    updated_at = _coerce_datetime(job.updated_at)
    if (
        job.status == PublishJobStatus.FAILED
        and job.failure_category == "rate_limit"
        and updated_at is not None
        and updated_at >= window_opened_at
    ):
        return True
    preserved_state = _extract_failure_window_state(job)
    failure_category = str(preserved_state.get("last_failure_category") or "").strip()
    failure_at = _coerce_datetime(preserved_state.get("last_failure_at"))
    return failure_category == "rate_limit" and failure_at is not None and failure_at >= window_opened_at


def _record_failure_window_state(job: PublishJob) -> None:
    preserved_state = _extract_failure_window_state(job)
    preserved_state["last_failure_category"] = job.failure_category
    preserved_state["last_failure_at"] = datetime.now(UTC).isoformat()
    job.provider_payload = {**dict(job.provider_payload or {}), **preserved_state}


def _clear_failure_window_state(job: PublishJob) -> None:
    provider_payload = dict(job.provider_payload or {})
    provider_payload.pop("last_failure_category", None)
    provider_payload.pop("last_failure_at", None)
    job.provider_payload = provider_payload


def _extract_failure_window_state(job: PublishJob) -> dict[str, object]:
    provider_payload = dict(job.provider_payload or {})
    preserved_state: dict[str, object] = {}
    if job.failure_category:
        preserved_state["last_failure_category"] = job.failure_category
        preserved_state["last_failure_at"] = job.updated_at.isoformat()
    elif provider_payload.get("last_failure_category") and provider_payload.get("last_failure_at"):
        preserved_state["last_failure_category"] = provider_payload["last_failure_category"]
        preserved_state["last_failure_at"] = provider_payload["last_failure_at"]
    return preserved_state


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


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

    # All jobs have reached a terminal state (PUBLISHED or FAILED) with a mix
    # of both — the article was partially published. We expose this as a
    # distinct state so the workbench can show "some platforms succeeded" and
    # operators can retry only the failed ones.
    terminal_statuses = {PublishJobStatus.PUBLISHED, PublishJobStatus.FAILED}
    if statuses <= terminal_statuses and PublishJobStatus.PUBLISHED in statuses:
        article.status = ArticleStatus.PARTIALLY_PUBLISHED
        return

    # Only downgrade to FAILED when every job has failed terminally.
    if statuses == {PublishJobStatus.FAILED}:
        article.status = ArticleStatus.FAILED
        return

    article.status = ArticleStatus.SCHEDULED
