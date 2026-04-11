from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

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
    provider_job_id: str | None = None,
    provider_payload: dict[str, object] | None = None,
) -> PublishSubmission:
    dispatch_key = job.dispatch_key or f"dispatch-{job.platform}-{job.id}"
    poll_deadline_at = datetime.now(UTC) + timedelta(seconds=max(poll_timeout_seconds, 0))
    payload: dict[str, object] = {
        "dispatch_key": dispatch_key,
        "platform": platform,
        "article_id": str(article.id),
        "preview": variant.content[:120],
        "auth_mode": auth_mode,
        "poll_deadline_at": poll_deadline_at.isoformat(),
    }
    if provider_payload:
        payload.update(provider_payload)
    return PublishSubmission(
        provider_job_id=provider_job_id or f"{dispatch_key}-{platform}",
        provider_payload=payload,
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
    chat_id: str
    api_base_url: str = "https://api.telegram.org"
    poll_timeout_seconds: int = 300
    request_timeout_seconds: float = 10.0

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        response = httpx.post(
            f"{self.api_base_url}/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": variant.content,
                "disable_web_page_preview": False,
            },
            timeout=self.request_timeout_seconds,
        )
        return self._build_submission_from_response(response, job=job, article=article, variant=variant)

    async def submit_async(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=self.request_timeout_seconds) as client:
            response = await client.post(
                f"/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": variant.content,
                    "disable_web_page_preview": False,
                },
            )
        return self._build_submission_from_response(response, job=job, article=article, variant=variant)

    def _build_submission_from_response(
        self,
        response: httpx.Response,
        *,
        job: PublishJob,
        article: ArticleDraft,
        variant: PostVariant,
    ) -> PublishSubmission:
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("telegram publish returned an invalid payload")
        if payload.get("ok") is False:
            raise RuntimeError(str(payload.get("description") or "telegram publish failed"))
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("telegram publish missing result payload")
        message_id = result.get("message_id")
        if message_id is None:
            raise RuntimeError("telegram publish missing message_id")
        external_id = str(message_id)
        return _build_submission(
            platform="telegram",
            job=job,
            article=article,
            variant=variant,
            auth_mode="bot_token",
            poll_timeout_seconds=self.poll_timeout_seconds,
            provider_job_id=f"telegram-message-{external_id}",
            provider_payload={
                "external_id": external_id,
                "provider_status": "accepted",
                "chat_id": self.chat_id,
                "telegram_result": result,
            },
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