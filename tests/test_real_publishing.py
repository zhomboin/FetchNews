from datetime import UTC, datetime

from sqlalchemy import select

from fetchnews.main import create_app
from fetchnews.models import PublishJob, PublishJobStatus, Source
from fetchnews.publishing.service import publish_job_to_response
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