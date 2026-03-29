from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from fetchnews.models import ArticleDraft, PostVariant, PublishJob, PublishJobStatus


@dataclass(slots=True)
class PublishSubmission:
    provider_job_id: str
    provider_payload: dict[str, str]


@dataclass(slots=True)
class PublishPollResult:
    terminal: bool
    status: str | None = None
    external_id: str | None = None
    error_message: str | None = None


class PublisherConnector(Protocol):
    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        ...

    def poll(self, job: PublishJob) -> PublishPollResult:
        ...


class MockPublisherConnector:
    def __init__(self, completion_delay_seconds: int = 0) -> None:
        self.completion_delay_seconds = max(completion_delay_seconds, 0)

    def submit(self, job: PublishJob, article: ArticleDraft, variant: PostVariant) -> PublishSubmission:
        ready_at = datetime.now(UTC) + timedelta(seconds=self.completion_delay_seconds)
        provider_job_id = f"mock-{job.platform}-{job.id}"
        external_id = f"{job.platform}-{article.id}-{job.id}"
        return PublishSubmission(
            provider_job_id=provider_job_id,
            provider_payload={
                "ready_at": ready_at.isoformat(),
                "result_status": PublishJobStatus.PUBLISHED,
                "external_id": external_id,
            },
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        provider_payload = job.provider_payload or {}
        ready_at_raw = provider_payload.get("ready_at")
        if ready_at_raw is None:
            return PublishPollResult(
                terminal=True,
                status=PublishJobStatus.FAILED,
                error_message="missing publish readiness marker",
            )

        ready_at = datetime.fromisoformat(ready_at_raw)
        if ready_at.tzinfo is None:
            ready_at = ready_at.replace(tzinfo=UTC)

        if datetime.now(UTC) < ready_at:
            return PublishPollResult(terminal=False)

        result_status = provider_payload.get("result_status", PublishJobStatus.PUBLISHED)
        if result_status == PublishJobStatus.FAILED:
            return PublishPollResult(
                terminal=True,
                status=PublishJobStatus.FAILED,
                error_message=provider_payload.get("error_message", "mock publisher failure"),
            )

        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.PUBLISHED,
            external_id=provider_payload.get("external_id"),
        )