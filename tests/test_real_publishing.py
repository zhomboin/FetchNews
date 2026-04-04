from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from fetchnews.main import create_app
from fetchnews.models import PublishJob, PublishJobStatus, Source, StoryStatus
from fetchnews.publishing.connectors import PublishPollResult, PublishSubmission
from fetchnews.publishing.service import build_default_publisher_registry, dispatch_due_publish_jobs, publish_job_to_response, retry_publish_job
from fetchnews.publishing.real_publishers import RealTelegramPublisher
from fetchnews.schemas import RawIngestedItem, StoryCreatePayload
from fetchnews.settings import Settings


def test_settings_expose_phase07_platform_credentials() -> None:
    settings = Settings(
        publish_real_platform="telegram",
        telegram_bot_token="telegram-token",
        x_bearer_token="x-token",
        wechat_app_id="wechat-app-id",
    )

    assert settings.publish_real_platform == "telegram"
    assert settings.telegram_bot_token == "telegram-token"
    assert settings.x_bearer_token == "x-token"
    assert settings.wechat_app_id == "wechat-app-id"


def test_publish_job_response_exposes_external_dispatch_contract() -> None:
    scheduled_for = datetime(2026, 4, 4, 9, 0, tzinfo=UTC)
    job = PublishJob(
        id=11,
        article_id=7,
        platform="telegram",
        scheduled_for=scheduled_for,
        status=PublishJobStatus.SCHEDULED,
        retries=1,
        provider_job_id="provider-123",
        dispatch_key="article-7-telegram-20260404090000",
        failure_category="rate_limit",
        last_provider_status="queued",
        provider_payload={},
        performance_metrics={},
        updated_at=scheduled_for,
    )

    response = publish_job_to_response(job)

    assert response.provider_job_id == "provider-123"
    assert response.dispatch_key == "article-7-telegram-20260404090000"
    assert response.failure_category == "rate_limit"
    assert response.last_provider_status == "queued"


def test_source_persists_incremental_sync_state() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase07_source_state.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )
    last_success_at = datetime(2026, 4, 4, 8, 30, tzinfo=UTC)

    with app.state.container.session_factory() as session:
        source = Source(
            slug="phase07-github-releases",
            label="Phase 07 GitHub Releases",
            platform="github",
            priority="P0",
            kind="api",
            enabled=True,
            config={"url": "https://api.github.com/repos/openai/openai-python/releases"},
            incremental_cursor="next-page-token",
            last_success_at=last_success_at,
        )
        session.add(source)
        session.commit()

        stored = session.scalar(select(Source).where(Source.slug == "phase07-github-releases"))
        assert stored is not None
        assert stored.incremental_cursor == "next-page-token"
        assert stored.last_success_at == last_success_at


class TrackingPublisher:
    def __init__(self) -> None:
        self.submit_calls = 0
        self.callback_calls = 0

    def submit(self, job: PublishJob, article, variant) -> PublishSubmission:
        self.submit_calls += 1
        dispatch_key = job.dispatch_key or f"dispatch-{job.platform}-{job.id}"
        return PublishSubmission(
            provider_job_id=f"{dispatch_key}-submission-{self.submit_calls}",
            provider_payload={
                "dispatch_key": dispatch_key,
                "submitted_variant": variant.content,
            },
        )

    def poll(self, job: PublishJob) -> PublishPollResult:
        return PublishPollResult(terminal=False)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        self.callback_calls += 1
        status = str(payload.get("status") or "")
        if status == "published":
            return PublishPollResult(
                terminal=True,
                status=PublishJobStatus.PUBLISHED,
                external_id=str(payload.get("external_id") or "callback-external-id"),
            )
        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.FAILED,
            error_message=str(payload.get("error_message") or "callback failure"),
        )


def _story_payload(story_key: str) -> dict:
    return StoryCreatePayload(
        story_key=story_key,
        cluster_title="Phase 07 callback flow is ready",
        summary="A story used to verify Phase 07 publishing callbacks.",
        highlights=["Tracks callback writeback"],
        source_links=["https://example.com/phase07/callback"],
        tags=["phase07", "publishing"],
        risk_flags=[],
        score=8.3,
        item_count=1,
        first_seen_at=datetime(2026, 4, 4, 9, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 4, 4, 9, 0, tzinfo=UTC),
        status=StoryStatus.APPROVED,
    ).model_dump(mode="json")


def _create_ready_article(client: TestClient, *, story_key: str, target_date: str) -> int:
    story_response = client.post("/stories", json=_story_payload(story_key))
    assert story_response.status_code == 201
    story_id = story_response.json()["id"]
    approve_response = client.post(f"/stories/{story_id}/approve")
    assert approve_response.status_code == 200

    article_response = client.post(
        "/articles/generate/daily",
        json={"target_date": target_date, "story_ids": [story_id]},
    )
    assert article_response.status_code == 200
    return article_response.json()["id"]


def test_dispatch_due_publish_jobs_preserves_dispatch_key_on_retry() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_dispatch_retry.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-dispatch-retry", target_date="2026-04-04")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        with app.state.container.session_factory() as session:
            first_result = dispatch_due_publish_jobs(session, {"telegram": publisher})
            assert first_result.jobs_dispatched == 1
            job = session.get(PublishJob, job_id)
            assert job is not None
            first_dispatch_key = job.dispatch_key
            first_provider_job_id = job.provider_job_id
            assert first_dispatch_key is not None

            retry_publish_job(session, job)
            second_result = dispatch_due_publish_jobs(session, {"telegram": publisher})
            assert second_result.jobs_dispatched == 1
            session.commit()

            retried_job = session.get(PublishJob, job_id)
            assert retried_job is not None
            assert retried_job.dispatch_key == first_dispatch_key
            assert retried_job.provider_job_id != first_provider_job_id
            assert retried_job.provider_job_id == f"{first_dispatch_key}-submission-2"


def test_publish_callback_marks_job_published_without_duplicate_submit() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_publish_callback.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-callback", target_date="2026-04-05")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        dispatch_response = client.post("/publish-jobs/dispatch-due")
        assert dispatch_response.status_code == 200
        assert publisher.submit_calls == 1

        callback_response = client.post(
            "/publish-jobs/callback/telegram",
            json={
                "provider_job_id": f"dispatch-telegram-{job_id}-submission-1",
                "status": "published",
                "external_id": "telegram-message-42",
            },
        )
        assert callback_response.status_code == 200
        payload = callback_response.json()
        assert payload["status"] == "published"
        assert payload["external_id"] == "telegram-message-42"
        assert publisher.submit_calls == 1
        assert publisher.callback_calls == 1


def test_registry_uses_real_telegram_publisher_when_configured() -> None:
    registry = build_default_publisher_registry(
        Settings(
            publish_real_platform="telegram",
            telegram_bot_token="telegram-token",
        )
    )

    assert isinstance(registry["telegram"], RealTelegramPublisher)
