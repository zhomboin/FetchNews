from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from fetchnews.main import create_app
from fetchnews.models import IngestRun, IngestRunStatus, RawItem, Source
from fetchnews.schemas import RawIngestedItem
from fetchnews.settings import Settings
from fetchnews.tasks.worker import run_ingestion_job


class StubConnector:
    def __init__(self, items: list[RawIngestedItem] | None = None, error: str | None = None) -> None:
        self.items = items or []
        self.error = error

    def fetch(self, source: Source) -> list[RawIngestedItem]:
        if self.error is not None:
            raise RuntimeError(self.error)
        return self.items


def _github_item() -> RawIngestedItem:
    return RawIngestedItem(
        source_slug="github-trending",
        external_id="repo-1",
        title="OpenAI ships a new agent toolkit",
        url="https://github.com/openai/agents",
        author="openai",
        published_at=datetime(2026, 3, 26, 8, 0, tzinfo=UTC),
        content="A new agent toolkit reached trending.",
        metadata={"stars": 1200},
    )


def test_ingest_run_persists_sources_runs_and_raw_items() -> None:
    settings = Settings(
        database_url="sqlite:///./test_ingestion.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    connector_overrides = {"github": StubConnector(items=[_github_item()])}
    app = create_app(settings, connector_overrides=connector_overrides)

    with TestClient(app) as client:
        response = client.post("/ingest/run", json={"source_slugs": ["github-trending"]})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == IngestRunStatus.COMPLETED
        assert payload["sources_total"] == 1
        assert payload["sources_succeeded"] == 1
        assert payload["sources_failed"] == 0
        assert payload["items_ingested"] == 1

        with app.state.container.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Source)) == 1
            assert session.scalar(select(func.count()).select_from(IngestRun)) == 1
            assert session.scalar(select(func.count()).select_from(RawItem)) == 1


def test_ingest_run_is_idempotent_and_isolates_failures() -> None:
    settings = Settings(
        database_url="sqlite:///./test_ingestion_errors.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    connector_overrides = {
        "github": StubConnector(items=[_github_item()]),
        "rss": StubConnector(error="feed timeout"),
    }
    app = create_app(settings, connector_overrides=connector_overrides)

    with TestClient(app) as client:
        first = client.post("/ingest/run", json={"source_slugs": ["github-trending", "openai-blog"]})
        second = client.post("/ingest/run", json={"source_slugs": ["github-trending", "openai-blog"]})

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["status"] == IngestRunStatus.COMPLETED_WITH_ERRORS
        assert second.json()["sources_failed"] == 1
        assert second.json()["items_ingested"] == 1
        assert second.json()["errors"] == [{"source_slug": "openai-blog", "message": "feed timeout"}]

        with app.state.container.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(RawItem)) == 1
            assert session.scalar(select(func.count()).select_from(IngestRun)) == 2


def test_ingest_runs_can_be_listed_and_fetched_by_id() -> None:
    settings = Settings(
        database_url="sqlite:///./test_ingestion_query.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    connector_overrides = {"github": StubConnector(items=[_github_item()])}
    app = create_app(settings, connector_overrides=connector_overrides)

    with TestClient(app) as client:
        created = client.post("/ingest/run", json={"source_slugs": ["github-trending"]})
        run_id = created.json()["id"]

        list_response = client.get("/ingest/runs")
        detail_response = client.get(f"/ingest/runs/{run_id}")

        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        assert list_response.json()[0]["id"] == run_id

        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == run_id
        assert detail_response.json()["source_slugs"] == ["github-trending"]


def test_worker_can_run_ingestion_job_with_overrides() -> None:
    settings = Settings(
        database_url="sqlite:///./test_ingestion_worker.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    result = run_ingestion_job(
        source_slugs=["github-trending"],
        settings=settings,
        connector_overrides={"github": StubConnector(items=[_github_item()])},
    )

    assert result["status"] == IngestRunStatus.COMPLETED
    assert result["sources_total"] == 1
    assert result["items_ingested"] == 1

def test_worker_registers_periodic_ingestion_schedule() -> None:
    from fetchnews.tasks.worker import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "ingest-default-sources" in schedule
    assert schedule["ingest-default-sources"]["task"] == "fetchnews.ingest.run"

def test_source_catalog_endpoint_returns_enabled_specs() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_source_catalog.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        response = client.get("/sources")

        assert response.status_code == 200
        payload = response.json()
        assert payload[0]["priority"] == "P0"
        assert {item["slug"] for item in payload}.issuperset({"github-trending", "openai-blog", "x-allowlist"})
