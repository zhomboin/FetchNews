from __future__ import annotations

from dataclasses import dataclass

from fetchnews.models import ArticleDraft, PostVariant, PublishJob, PublishJobStatus
from fetchnews.publishing.connectors import PublishPollResult, PublishSubmission


@dataclass(slots=True)
class RealTelegramPublisher:
    bot_token: str
    api_base_url: str = "https://api.telegram.org"

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        dispatch_key = job.dispatch_key or f"dispatch-{job.platform}-{job.id}"
        provider_job_id = f"{dispatch_key}-telegram"
        return PublishSubmission(
            provider_job_id=provider_job_id,
            provider_payload={
                "dispatch_key": dispatch_key,
                "platform": "telegram",
                "article_id": str(article.id),
                "preview": variant.content[:120],
            },
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        provider_payload = job.provider_payload or {}
        external_id = provider_payload.get("external_id")
        if external_id:
            return PublishPollResult(
                terminal=True,
                status=PublishJobStatus.PUBLISHED,
                external_id=str(external_id),
            )
        return PublishPollResult(terminal=False)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
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
            error_message=str(payload.get("error_message") or "telegram publish failed"),
        )
