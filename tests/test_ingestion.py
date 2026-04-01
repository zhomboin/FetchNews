from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from fetchnews.main import create_app
from fetchnews.models import IngestRun, IngestRunStatus, NormalizedItemRecord, RawItem, Source, Story, StoryStatus
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
        title="OpenAI releases agent benchmark toolkit",
        url="https://github.com/openai/agent-bench",
        author="openai",
        published_at=datetime(2026, 3, 26, 8, 0, tzinfo=UTC),
        content="A new agent benchmark toolkit reached trending.",
        metadata={"stars": 1200},
    )


def _openai_blog_item() -> RawIngestedItem:
    return RawIngestedItem(
        source_slug="openai-blog",
        external_id="blog-1",
        title="OpenAI releases an agent benchmark toolkit",
        url="https://openai.com/blog/agent-benchmark-toolkit?utm_source=x",
        author="OpenAI",
        published_at=datetime(2026, 3, 26, 8, 5, tzinfo=UTC),
        content="The post introduces a toolkit for evaluating agent workflows.",
        metadata={"category": "blog"},
    )


def test_ingest_run_persists_pipeline_outputs_and_clusters_similar_items() -> None:
    settings = Settings(
        database_url="sqlite:///./test_ingestion.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    connector_overrides = {
        "github": StubConnector(items=[_github_item()]),
        "rss": StubConnector(items=[_openai_blog_item()]),
    }
    app = create_app(settings, connector_overrides=connector_overrides)

    with TestClient(app) as client:
        response = client.post("/ingest/run", json={"source_slugs": ["github-trending", "openai-blog"]})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == IngestRunStatus.COMPLETED
        assert payload["sources_total"] == 2
        assert payload["sources_succeeded"] == 2
        assert payload["sources_failed"] == 0
        assert payload["items_ingested"] == 2

        stories_response = client.get("/stories")
        assert stories_response.status_code == 200
        stories = stories_response.json()
        assert len(stories) == 1
        assert stories[0]["item_count"] == 2
        assert len(stories[0]["source_links"]) == 2

        with app.state.container.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Source)) == 2
            assert session.scalar(select(func.count()).select_from(IngestRun)) == 1
            assert session.scalar(select(func.count()).select_from(RawItem)) == 2
            assert session.scalar(select(func.count()).select_from(NormalizedItemRecord)) == 2
            assert session.scalar(select(func.count()).select_from(Story)) == 1


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
            assert session.scalar(select(func.count()).select_from(NormalizedItemRecord)) == 1
            assert session.scalar(select(func.count()).select_from(Story)) == 1
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

def _arxiv_item() -> RawIngestedItem:
    return RawIngestedItem(
        source_slug="arxiv-cs-ai",
        external_id="paper-1",
        title="Fresh arXiv benchmark release",
        url="https://arxiv.org/abs/2603.12345",
        author="Research Team",
        published_at=datetime(2026, 3, 26, 9, 0, tzinfo=UTC),
        content="A new benchmark paper introduces a research evaluation dataset.",
        metadata={"category": "paper", "tags": ["research", "benchmark"]},
    )


def test_source_catalog_endpoint_includes_governance_feedback() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_source_feedback.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        ),
        connector_overrides={"rss": StubConnector(error="feed timeout")},
    )

    with TestClient(app) as client:
        ingest_response = client.post("/ingest/run", json={"source_slugs": ["openai-blog"]})
        assert ingest_response.status_code == 200

        with app.state.container.session_factory() as session:
            session.add(
                Story(
                    story_key="source-feedback-openai-blog",
                    cluster_title="OpenAI blog item still needs confirmation",
                    summary="An item from the OpenAI blog is still pending review.",
                    highlights=["Needs manual confirmation"],
                    source_links=["https://openai.com/news/verification-needed"],
                    tags=["openai-blog", "blog", "verification"],
                    risk_flags=["secondary_sources_only"],
                    score=5.1,
                    item_count=1,
                    status=StoryStatus.PENDING,
                    first_seen_at=datetime(2026, 3, 26, 10, 0, tzinfo=UTC),
                    last_seen_at=datetime(2026, 3, 26, 10, 0, tzinfo=UTC),
                )
            )
            session.commit()

        response = client.get("/sources")
        assert response.status_code == 200
        payload = response.json()
        openai_blog = next(item for item in payload if item["slug"] == "openai-blog")

        assert openai_blog["feedback_signals"]["failed_ingest_runs"] == 1
        assert openai_blog["feedback_signals"]["pending_stories"] == 1
        assert openai_blog["feedback_signals"]["flagged_stories"] == 1
        assert openai_blog["effective_score_multiplier"] < openai_blog["config"]["score_multiplier"]
        assert "ingest_failures" in openai_blog["governance_flags"]
        assert "review_backlog" in openai_blog["governance_flags"]


def test_ingest_pipeline_applies_section_feedback_to_story_ranking() -> None:
    settings = Settings(
        database_url="sqlite:///./test_story_feedback_ranking.db",
        redis_url="redis://localhost:6379/0",
        environment="test",
    )
    connector_overrides = {
        "github": StubConnector(items=[_github_item()]),
        "arxiv": StubConnector(items=[_arxiv_item()]),
    }
    app = create_app(settings, connector_overrides=connector_overrides)

    with app.state.container.session_factory() as session:
        session.add(
            Story(
                story_key="existing-research-backlog",
                cluster_title="Existing research item awaiting review",
                summary="A research story is still pending review and source verification.",
                highlights=["Pending manual review"],
                source_links=["https://arxiv.org/abs/2501.00001"],
                tags=["arxiv-cs-ai", "paper", "research"],
                risk_flags=["secondary_sources_only"],
                score=4.9,
                item_count=1,
                status=StoryStatus.PENDING,
                first_seen_at=datetime(2026, 3, 25, 9, 0, tzinfo=UTC),
                last_seen_at=datetime(2026, 3, 25, 9, 0, tzinfo=UTC),
            )
        )
        session.commit()

    with TestClient(app) as client:
        ingest_response = client.post("/ingest/run", json={"source_slugs": ["github-trending", "arxiv-cs-ai"]})
        assert ingest_response.status_code == 200

        stories_response = client.get("/stories")
        assert stories_response.status_code == 200
        stories = stories_response.json()

        research_story = next(story for story in stories if story["cluster_title"] == "Fresh arXiv benchmark release")
        github_story = next(story for story in stories if story["cluster_title"] == "OpenAI releases agent benchmark toolkit")

        assert "section_feedback_watch" in research_story["risk_flags"]
        assert research_story["score"] < github_story["score"]


def test_source_catalog_endpoint_applies_engagement_feedback_to_effective_weights() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_source_engagement_feedback.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        openai_story_response = client.post(
            "/stories",
            json={
                "story_key": "source-engagement-openai-blog",
                "cluster_title": "OpenAI blog release drives strong distribution clicks",
                "summary": "A post from the OpenAI blog is driving strong downstream engagement.",
                "highlights": ["Strong source signal"],
                "source_links": ["https://openai.com/news/strong-distribution"],
                "tags": ["openai-blog", "blog", "distribution"],
                "risk_flags": [],
                "score": 8.4,
                "item_count": 1,
                "first_seen_at": "2026-05-07T09:00:00Z",
                "last_seen_at": "2026-05-07T09:00:00Z",
            },
        )
        reddit_story_response = client.post(
            "/stories",
            json={
                "story_key": "source-engagement-reddit-ml",
                "cluster_title": "Reddit recap struggles to convert distribution",
                "summary": "A community repost from Reddit receives impressions but weak click-through.",
                "highlights": ["Needs source quality review"],
                "source_links": ["https://reddit.com/r/MachineLearning/comments/example"],
                "tags": ["reddit-ml", "community", "recap"],
                "risk_flags": [],
                "score": 6.3,
                "item_count": 1,
                "first_seen_at": "2026-05-08T09:00:00Z",
                "last_seen_at": "2026-05-08T09:00:00Z",
            },
        )
        assert openai_story_response.status_code == 201
        assert reddit_story_response.status_code == 201

        openai_story_id = openai_story_response.json()["id"]
        reddit_story_id = reddit_story_response.json()["id"]
        assert client.post(f"/stories/{openai_story_id}/approve").status_code == 200
        assert client.post(f"/stories/{reddit_story_id}/approve").status_code == 200

        openai_article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-07", "story_ids": [openai_story_id]},
        )
        assert openai_article_response.status_code == 200
        openai_article_id = openai_article_response.json()["id"]
        openai_publish_response = client.post(
            f"/articles/{openai_article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": "2026-05-07T18:00:00Z"},
        )
        assert openai_publish_response.status_code == 200
        openai_job_id = openai_publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{openai_job_id}/result",
            json={"status": "published", "external_id": "wx-openai-source-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{openai_job_id}/feedback",
            json={"impressions": 1600, "clicks": 208, "interactions": 92},
        ).status_code == 200

        reddit_article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-08", "story_ids": [reddit_story_id]},
        )
        assert reddit_article_response.status_code == 200
        reddit_article_id = reddit_article_response.json()["id"]
        reddit_publish_response = client.post(
            f"/articles/{reddit_article_id}/publish",
            json={"platforms": ["x"], "scheduled_for": "2026-05-08T18:00:00Z"},
        )
        assert reddit_publish_response.status_code == 200
        reddit_job_id = reddit_publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{reddit_job_id}/result",
            json={"status": "published", "external_id": "x-reddit-source-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{reddit_job_id}/feedback",
            json={"impressions": 700, "clicks": 10, "interactions": 6},
        ).status_code == 200

        response = client.get("/sources")
        assert response.status_code == 200
        payload = response.json()

        openai_blog = next(item for item in payload if item["slug"] == "openai-blog")
        reddit_ml = next(item for item in payload if item["slug"] == "reddit-ml")

        assert openai_blog["feedback_signals"]["engagement_impressions"] == 1600
        assert openai_blog["feedback_signals"]["engagement_clicks"] == 208
        assert openai_blog["effective_score_multiplier"] > openai_blog["config"]["score_multiplier"]
        assert openai_blog["effective_trust_score"] > openai_blog["config"]["trust_score"]
        assert reddit_ml["feedback_signals"]["engagement_impressions"] == 700
        assert reddit_ml["feedback_signals"]["engagement_clicks"] == 10
        assert reddit_ml["effective_score_multiplier"] < reddit_ml["config"]["score_multiplier"]
        assert "low_engagement" in reddit_ml["governance_flags"]