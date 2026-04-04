from __future__ import annotations

from dataclasses import dataclass

from fetchnews.models import ArticleDraft, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import PublishPollResult, PublishSubmission


def _build_submission(
    *,
    platform: str,
    job: PublishJob,
    article: ArticleDraft,
    variant: PostVariant,
    auth_mode: str,
) -> PublishSubmission:
    dispatch_key = job.dispatch_key or f"dispatch-{job.platform}-{job.id}"
    provider_job_id = f"{dispatch_key}-{platform}"
    return PublishSubmission(
        provider_job_id=provider_job_id,
        provider_payload={
            "dispatch_key": dispatch_key,
            "platform": platform,
            "article_id": str(article.id),
            "preview": variant.content[:120],
            "auth_mode": auth_mode,
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

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="telegram",
            job=job,
            article=article,
            variant=variant,
            auth_mode="bot_token",
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "telegram publish failed")


@dataclass(slots=True)
class RealWeChatPublisher:
    app_id: str
    api_base_url: str = "https://api.weixin.qq.com"

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="wechat",
            job=job,
            article=article,
            variant=variant,
            auth_mode="app_id",
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "wechat publish failed")


@dataclass(slots=True)
class RealXPublisher:
    bearer_token: str
    api_base_url: str = "https://api.x.com"

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        return _build_submission(
            platform="x",
            job=job,
            article=article,
            variant=variant,
            auth_mode="bearer_token",
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return _poll_submission(job)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return _handle_callback(job, payload, "x publish failed")
