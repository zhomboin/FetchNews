import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from fetchnews.main import create_app
from fetchnews.models import ArticleDraft, PostVariant, PublishJob, PublishJobStatus, Source, StoryStatus
from fetchnews.publishing.connectors import PublishPollResult, PublishSubmission
from fetchnews.publishing.service import (
    build_default_publisher_registry,
    dispatch_due_publish_jobs,
    publish_job_to_response,
    retry_publish_job,
    write_publish_job_result,
)
from fetchnews.publishing.real_publishers import RealTelegramPublisher, RealWeChatPublisher, RealXPublisher
from fetchnews.schemas import RawIngestedItem, StoryCreatePayload
from fetchnews.settings import Settings


def test_settings_expose_phase07_platform_credentials() -> None:
    settings = Settings(
        publish_real_platform="telegram",
        telegram_bot_token="telegram-token",
        telegram_chat_id="-100123",
        github_token="gh-token",
        x_bearer_token="x-token",
        wechat_app_id="wechat-app-id",
    )

    assert settings.publish_real_platform == "telegram"
    assert settings.telegram_bot_token == "telegram-token"
    assert settings.telegram_chat_id == "-100123"
    assert settings.github_token == "gh-token"
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
        publish_callback_secret="phase07-secret",
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
            headers={"X-FetchNews-Callback-Secret": "phase07-secret"},
        )
        assert callback_response.status_code == 200
        payload = callback_response.json()
        assert payload["status"] == "published"
        assert payload["external_id"] == "telegram-message-42"
        assert publisher.submit_calls == 1
        assert publisher.callback_calls == 1

        with app.state.container.session_factory() as session:
            audit_log_model = app.state.container.model_registry["audit_log"]
            callback_logs = [
                record
                for record in session.scalars(select(audit_log_model).order_by(audit_log_model.id.asc())).all()
                if record.action == "publish.callback"
            ]
            assert len(callback_logs) == 1
            assert callback_logs[0].resource_type == "publish_job"
            assert callback_logs[0].detail["platform"] == "telegram"
            assert callback_logs[0].detail["provider_status"] == "published"


def test_publish_callback_requires_callback_secret() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_callback_secret.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
        publish_callback_secret="phase07-secret",
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-callback-secret", target_date="2026-04-05")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        dispatch_response = client.post("/publish-jobs/dispatch-due")
        assert dispatch_response.status_code == 200

        callback_payload = {
            "provider_job_id": f"dispatch-telegram-{job_id}-submission-1",
            "status": "published",
            "external_id": "telegram-message-43",
        }
        unauthorized_response = client.post(
            "/publish-jobs/callback/telegram",
            json=callback_payload,
        )
        assert unauthorized_response.status_code == 401

        authorized_response = client.post(
            "/publish-jobs/callback/telegram",
            json=callback_payload,
            headers={"X-FetchNews-Callback-Secret": "phase07-secret"},
        )
        assert authorized_response.status_code == 200
        assert authorized_response.json()["status"] == "published"


def test_publish_callback_rate_limits_repeated_ip_and_surfaces_security_alert() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_callback_ip_limit.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
        publish_callback_secret="phase07-secret",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        responses = [
            client.post(
                "/publish-jobs/callback/telegram",
                json={"provider_job_id": "missing-job", "status": "published"},
                headers={
                    "X-FetchNews-Callback-Secret": "wrong-secret",
                    "X-Forwarded-For": "203.0.113.9",
                },
            )
            for _ in range(4)
        ]

        assert [response.status_code for response in responses[:3]] == [401, 401, 401]
        assert responses[3].status_code == 429
        assert responses[3].headers["Retry-After"] == "300"

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        alerts = summary_response.json()["alerts"]
        security_alert = next(alert for alert in alerts if alert["category"] == "security")
        assert security_alert["target"] == "203.0.113.9"
        assert security_alert["count"] == 4


def test_development_environment_uses_stable_default_callback_secret() -> None:
    app = create_app(
        Settings(
            database_url=f"sqlite:///./test_phase07_default_callback_secret_{uuid4().hex}.db",
            redis_url="redis://localhost:6379/0",
            environment="development",
        )
    )
    publisher = TrackingPublisher()
    app.state.container.publisher_registry["telegram"] = publisher

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-default-callback-secret", target_date="2026-04-05")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        dispatch_response = client.post("/publish-jobs/dispatch-due")
        assert dispatch_response.status_code == 200

        callback_response = client.post(
            "/publish-jobs/callback/telegram",
            json={
                "provider_job_id": f"dispatch-telegram-{job_id}-submission-1",
                "status": "published",
                "external_id": "telegram-message-default-secret",
            },
            headers={"X-FetchNews-Callback-Secret": "fetchnews-dev-callback-secret"},
        )
        assert callback_response.status_code == 200
        assert callback_response.json()["status"] == "published"


def test_create_app_requires_explicit_callback_secret_outside_development_and_test() -> None:
    with pytest.raises(RuntimeError, match="APP_PUBLISH_CALLBACK_SECRET"):
        create_app(
            Settings(
                database_url="sqlite:///./test_phase07_missing_callback_secret.db",
                redis_url="redis://localhost:6379/0",
                environment="production",
                auth_enabled=False,
            )
        )


def test_publish_callback_rejects_platform_mismatch() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_callback_platform_mismatch.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
        publish_callback_secret="phase07-secret",
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-callback-platform", target_date="2026-04-05")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        dispatch_response = client.post("/publish-jobs/dispatch-due")
        assert dispatch_response.status_code == 200

        mismatch_response = client.post(
            "/publish-jobs/callback/x",
            json={
                "provider_job_id": f"dispatch-telegram-{job_id}-submission-1",
                "status": "published",
                "external_id": "telegram-message-44",
            },
            headers={"X-FetchNews-Callback-Secret": "phase07-secret"},
        )
        assert mismatch_response.status_code == 404


def test_registry_uses_real_telegram_publisher_when_configured() -> None:
    registry = build_default_publisher_registry(
        Settings(
            publish_real_platform="telegram",
            telegram_bot_token="telegram-token",
            telegram_chat_id="-100123",
        )
    )

    assert isinstance(registry["telegram"], RealTelegramPublisher)
    assert registry["telegram"].chat_id == "-100123"


def test_auth_backed_platforms_use_placeholder_real_publishers_when_selected() -> None:
    wechat_registry = build_default_publisher_registry(
        Settings(
            publish_real_platform="wechat",
            wechat_app_id="wechat-app-id",
        )
    )
    x_registry = build_default_publisher_registry(
        Settings(
            publish_real_platform="x",
            x_bearer_token="x-token",
        )
    )

    assert isinstance(wechat_registry["wechat"], RealWeChatPublisher)
    assert isinstance(x_registry["x"], RealXPublisher)


@pytest.mark.parametrize(
    ("error_message", "expected_category"),
    [
        ("platform rate limit exceeded", "rate_limit"),
        ("content rejected by moderation", "moderation"),
        ("wechat auth token expired", "auth"),
    ],
    ids=["rate_limit", "moderation", "auth"],
)
def test_write_publish_job_result_classifies_platform_failure_categories(
    error_message: str,
    expected_category: str,
) -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_failure_categories.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key=f"phase07-{expected_category}", target_date="2026-04-06")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": "2026-04-06T10:00:00Z"},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        with app.state.container.session_factory() as session:
            job = session.get(PublishJob, job_id)
            assert job is not None
            write_publish_job_result(
                session,
                job,
                status=PublishJobStatus.FAILED,
                error_message=error_message,
            )
            session.commit()

            failed_job = session.get(PublishJob, job_id)
            assert failed_job is not None
            assert failed_job.failure_category == expected_category


class FailingSubmitPublisher:
    def submit(self, job: PublishJob, article, variant) -> PublishSubmission:
        raise RuntimeError("telegram auth token expired")

    def poll(self, job: PublishJob) -> PublishPollResult:
        return PublishPollResult(terminal=False)

    def handle_callback(self, job: PublishJob, payload: dict[str, object]) -> PublishPollResult:
        return PublishPollResult(
            terminal=True,
            status=PublishJobStatus.FAILED,
            error_message="telegram auth token expired",
        )


def test_real_telegram_publisher_submit_calls_send_message_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "ok": True,
                "result": {
                    "message_id": 42,
                    "chat": {"id": "-100123"},
                    "text": "Phase 07 Telegram publish",
                },
            }

    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> StubResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("fetchnews.publishing.real_publishers.httpx.post", fake_post)

    publisher = RealTelegramPublisher(bot_token="telegram-token", chat_id="-100123")
    article = ArticleDraft(
        id=9,
        target_date=date(2026, 4, 6),
        title="Phase 07 title",
        summary="Phase 07 summary",
        body="Phase 07 body",
        story_ids=[1],
        story_keys=["phase07-story"],
    )
    variant = PostVariant(article_id=9, platform="telegram", content="Phase 07 Telegram publish")
    job = PublishJob(
        id=31,
        article_id=9,
        platform="telegram",
        scheduled_for=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
        status=PublishJobStatus.SCHEDULED,
        retries=0,
        dispatch_key="dispatch-telegram-31",
        provider_payload={},
        performance_metrics={},
    )

    submission = publisher.submit(job, article, variant)

    assert captured["url"] == "https://api.telegram.org/bottelegram-token/sendMessage"
    assert captured["json"] == {
        "chat_id": "-100123",
        "text": "Phase 07 Telegram publish",
        "disable_web_page_preview": False,
    }
    assert captured["timeout"] == 10.0
    assert submission.provider_job_id == "telegram-message-42"
    assert submission.provider_payload["external_id"] == "42"
    assert submission.provider_payload["provider_status"] == "accepted"
    assert submission.provider_payload["telegram_result"] == {
        "message_id": 42,
        "chat": {"id": "-100123"},
        "text": "Phase 07 Telegram publish",
    }


def test_real_telegram_publisher_exposes_async_submit_for_non_blocking_callers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class StubAsyncResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "ok": True,
                "result": {
                    "message_id": 43,
                    "chat": {"id": "-100123"},
                    "text": "Phase 07 async Telegram publish",
                },
            }

    class StubAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            captured["base_url"] = base_url
            captured["timeout"] = timeout

        async def __aenter__(self) -> "StubAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, path: str, json: dict[str, object]) -> StubAsyncResponse:
            captured["path"] = path
            captured["json"] = json
            return StubAsyncResponse()

    monkeypatch.setattr("fetchnews.publishing.real_publishers.httpx.AsyncClient", StubAsyncClient)

    publisher = RealTelegramPublisher(bot_token="telegram-token", chat_id="-100123")
    article = ArticleDraft(
        id=9,
        target_date=date(2026, 4, 6),
        title="Phase 07 title",
        summary="Phase 07 summary",
        body="Phase 07 body",
        story_ids=[1],
        story_keys=["phase07-story"],
    )
    variant = PostVariant(article_id=9, platform="telegram", content="Phase 07 async Telegram publish")
    job = PublishJob(
        id=32,
        article_id=9,
        platform="telegram",
        scheduled_for=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
        status=PublishJobStatus.SCHEDULED,
        retries=0,
        dispatch_key="dispatch-telegram-32",
        provider_payload={},
        performance_metrics={},
    )

    submission = asyncio.run(publisher.submit_async(job, article, variant))

    assert captured["base_url"] == "https://api.telegram.org"
    assert captured["timeout"] == 10.0
    assert captured["path"] == "/bottelegram-token/sendMessage"
    assert captured["json"] == {
        "chat_id": "-100123",
        "text": "Phase 07 async Telegram publish",
        "disable_web_page_preview": False,
    }
    assert submission.provider_job_id == "telegram-message-43"
    assert submission.provider_payload["external_id"] == "43"


def test_dispatch_due_publish_jobs_marks_job_failed_when_submit_raises() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_dispatch_submit_failure.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    publisher = FailingSubmitPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-dispatch-submit-failure", target_date="2026-04-06")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        with app.state.container.session_factory() as session:
            dispatch_result = dispatch_due_publish_jobs(session, {"telegram": publisher})
            assert dispatch_result.jobs_dispatched == 0
            assert dispatch_result.jobs_failed == 1
            failed_job = session.get(PublishJob, job_id)
            assert failed_job is not None
            assert failed_job.status == PublishJobStatus.FAILED
            assert failed_job.error_message == "telegram auth token expired"
            assert failed_job.failure_category == "auth"
            assert failed_job.last_provider_status == "submit_failed"


def test_dispatch_due_publish_jobs_skips_platform_when_rate_limit_window_open() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_dispatch_rate_limit_window.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
        publish_rate_limit_window_seconds=300,
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        blocked_article_id = _create_ready_article(
            client,
            story_key="phase07-dispatch-rate-limit-blocked",
            target_date="2026-04-06",
        )
        allowed_article_id = _create_ready_article(
            client,
            story_key="phase07-dispatch-rate-limit-pending",
            target_date="2026-04-06",
        )
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")

        blocked_publish_response = client.post(
            f"/articles/{blocked_article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert blocked_publish_response.status_code == 200
        blocked_job_id = blocked_publish_response.json()["jobs"][0]["id"]

        blocked_result_response = client.post(
            f"/publish-jobs/{blocked_job_id}/result",
            json={"status": "failed", "error_message": "platform rate limit exceeded"},
        )
        assert blocked_result_response.status_code == 200

        pending_publish_response = client.post(
            f"/articles/{allowed_article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert pending_publish_response.status_code == 200
        pending_job_id = pending_publish_response.json()["jobs"][0]["id"]

        with app.state.container.session_factory() as session:
            dispatch_result = dispatch_due_publish_jobs(
                session,
                {"telegram": publisher},
                settings=settings,
            )
            assert dispatch_result.jobs_dispatched == 0
            assert dispatch_result.jobs_failed == 0

            pending_job = session.get(PublishJob, pending_job_id)
            assert pending_job is not None
            assert pending_job.status == PublishJobStatus.SCHEDULED
            assert pending_job.provider_job_id is None
            assert pending_job.last_provider_status == "rate_limited"

        assert publisher.submit_calls == 0


def test_retry_publish_job_preserves_rate_limit_cooldown_window() -> None:
    settings = Settings(
        database_url="sqlite:///./test_phase07_retry_rate_limit_window.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
        publish_rate_limit_window_seconds=300,
    )
    publisher = TrackingPublisher()
    app = create_app(settings, publisher_overrides={"telegram": publisher})

    with TestClient(app) as client:
        article_id = _create_ready_article(client, story_key="phase07-rate-limit-retry", target_date="2026-04-06")
        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["telegram"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        with app.state.container.session_factory() as session:
            job = session.get(PublishJob, job_id)
            assert job is not None
            write_publish_job_result(
                session,
                job,
                status=PublishJobStatus.FAILED,
                error_message="platform rate limit exceeded",
            )
            retry_publish_job(session, job)

            dispatch_result = dispatch_due_publish_jobs(
                session,
                {"telegram": publisher},
                settings=settings,
            )
            assert dispatch_result.jobs_dispatched == 0

            retried_job = session.get(PublishJob, job_id)
            assert retried_job is not None
            assert retried_job.status == PublishJobStatus.SCHEDULED
            assert retried_job.provider_job_id is None
            assert retried_job.last_provider_status == "rate_limited"

        assert publisher.submit_calls == 0


def test_env_example_includes_phase07_hardening_runtime_variables() -> None:
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")

    assert "APP_TELEGRAM_CHAT_ID=" in env_example
    assert "APP_PUBLISH_RATE_LIMIT_WINDOW_SECONDS=" in env_example
    assert "APP_SOURCE_RETRY_ATTEMPTS=" in env_example
    assert "APP_SOURCE_FAILURE_ALERT_THRESHOLD=" in env_example
    assert "APP_GITHUB_TOKEN=" in env_example
    assert "\nGITHUB_TOKEN=" not in env_example
    assert "WECHAT_APP_SECRET=" not in env_example


def test_real_telegram_publisher_poll_fails_after_deadline_without_callback() -> None:
    publisher = RealTelegramPublisher(bot_token="telegram-token", chat_id="-100123")
    job = PublishJob(
        id=31,
        article_id=9,
        platform="telegram",
        scheduled_for=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
        status=PublishJobStatus.SCHEDULED,
        retries=0,
        provider_job_id="dispatch-telegram-31-telegram",
        provider_payload={
            "poll_deadline_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
        performance_metrics={},
    )

    poll_result = publisher.poll(job)

    assert poll_result.terminal is True
    assert poll_result.status == PublishJobStatus.FAILED
    assert poll_result.error_message == "telegram publish callback timed out"
