from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fetchnews.models import ArticleDraft, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import PublishPollResult, PublishSubmission


def _build_submission(
    *,
    platform: str,
    job: PublishJob,
    article: ArticleDraft,
    variant: PostVariant,
    auth_mode: str,
    poll_timeout_seconds: int,
) -> PublishSubmission:
    dispatch_key = job.dispatch_key or f"dispatch-{job.platform}-{job.id}"
    provider_job_id = f"{dispatch_key}-{platform}"
    poll_deadline_at = datetime.now(UTC) + timedelta(seconds=max(poll_timeout_seconds, 0))
    return PublishSubmission(
        provider_job_id=provider_job_id,
        provider_payload={
            "dispatch_key": dispatch_key,
            "platform": platform,
            "article_id": str(article.id),
            "preview": variant.content[:120],
            "auth_mode": auth_mode,
            "poll_deadline_at": poll_deadline_at.isoformat(),
        },
    )


def _poll_submission(job: PublishJob) -> PublishPollResult:
    provider_payload = job.provider_payload or {}
    external_id = provider_payload.get("external_id")
    if external_id:
        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.PUBLISHED,
            external_id=str(external_id),
        )
    poll_deadline_at = _coerce_datetime(job.provider_payload.get("poll_deadline_at"))
    if poll_deadline_at is not None and datetime.now(UTC) >= poll_deadline_at:
        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.FAILED,
            error_message=f"{job.platform} publish callback timed out",
        )
    return PublishPollResult(terminal=False)


def _handle_callback(job: PublishJob, payload: dict[str, object], failure_message: str) -> PublishPollResult:
    status = str(payload.get("status") or "")
    if status == PublishJobStatus.PUBLISHED:
        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.PUBLISHED,
            external_id=str(payload.get("external_id") or job.external_id or ""),
        )
    return PublishPollResult(
        terminal=True,
        status=PublishJobStatus.FAILED,
        error_message=str(payload.get("error_message") or failure_message),
    )


@dataclass(slots=True)
class RealTelegramPublisher:
    bot_token: str
    api_base_url: str = "https://api.telegram.org"
    poll_timeout_seconds: int = 300

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="telegram",
            job=job,
            article=article,
            variant=variant,
            auth_mode="bot_token",
            poll_timeout_seconds=self.poll_timeout_seconds,
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "telegram publish failed")


@dataclass(slots=True)
class RealWeChatPublisher:
    app_id: str
    api_base_url: str = "https://api.weixin.qq.com"
    poll_timeout_seconds: int = 300

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="wechat",
            job=job,
            article=article,
            variant=variant,
            auth_mode="app_id",
            poll_timeout_seconds=self.poll_timeout_seconds,
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "wechat publish failed")


@dataclass(slots=True)
class RealXPublisher:
    bearer_token: str
    api_base_url: str = "https://api.x.com"
    poll_timeout_seconds: int = 300

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="x",
            job=job,
            article=article,
            variant=variant,
            auth_mode="bearer_token",
            poll_timeout_seconds=self.poll_timeout_seconds,
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "x publish failed")


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
