from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fetchnews.main import create_app
from fetchnews.models import StoryStatus
from fetchnews.schemas import RawIngestedItem, StoryCreatePayload
from fetchnews.settings import Settings


class StubConnector:
    def __init__(self, items: list[RawIngestedItem] | None = None) -> None:
        self.items = items or []

    def fetch(self, _source) -> list[RawIngestedItem]:
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


def test_story_review_and_publish_flow() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_fetchnews.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        create_response = client.post(
            "/stories",
            json=StoryCreatePayload(
                story_key="story-api-1",
                cluster_title="Mistral ships a new inference stack",
                summary="Mistral 发布了新的推理栈更新。",
                highlights=["聚焦推理效率"],
                source_links=["https://mistral.ai/news"],
                tags=["release"],
                risk_flags=[],
                score=8.6,
                item_count=1,
                first_seen_at=datetime(2026, 3, 25, 10, 0, tzinfo=UTC).isoformat(),
                last_seen_at=datetime(2026, 3, 25, 10, 0, tzinfo=UTC).isoformat(),
            ).model_dump(mode="json"),
        )
        assert create_response.status_code == 201
        story_id = create_response.json()["id"]

        approve_response = client.post(f"/stories/{story_id}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == StoryStatus.APPROVED

        generate_response = client.post("/articles/generate/daily", params={"target_date": "2026-03-25"})
        assert generate_response.status_code == 200
        article_id = generate_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x"], "scheduled_for": "2026-03-25T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        assert len(publish_response.json()["jobs"]) == 2

        jobs_response = client.get("/publish-jobs")
        assert jobs_response.status_code == 200
        assert len(jobs_response.json()) >= 2


def test_daily_digest_generation_persists_article_and_variants() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase04_api.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        create_response = client.post(
            "/stories",
            json=StoryCreatePayload(
                story_key="story-phase04-1",
                cluster_title="OpenAI updates agent evaluation stack",
                summary="OpenAI 更新了 agent 评测链路，强调真实工作流验证。",
                highlights=["聚焦真实工作流", "强调评测一致性"],
                source_links=["https://openai.com/blog/agent-evals"],
                tags=["agent", "evaluation"],
                risk_flags=[],
                score=9.4,
                item_count=2,
                first_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC).isoformat(),
                last_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC).isoformat(),
            ).model_dump(mode="json"),
        )
        assert create_response.status_code == 201
        story_id = create_response.json()["id"]

        approve_response = client.post(f"/stories/{story_id}/approve")
        assert approve_response.status_code == 200

        generate_response = client.post("/articles/generate/daily", params={"target_date": "2026-03-28"})
        assert generate_response.status_code == 200
        article_payload = generate_response.json()
        assert article_payload["status"] == "ready"
        assert article_payload["story_count"] == 1
        assert article_payload["variant_count"] == 3
        article_id = article_payload["id"]

        articles_response = client.get("/articles")
        assert articles_response.status_code == 200
        articles_payload = articles_response.json()
        assert len(articles_payload) == 1
        assert articles_payload[0]["id"] == article_id
        assert articles_payload[0]["variant_count"] == 3

        article_detail_response = client.get(f"/articles/{article_id}")
        assert article_detail_response.status_code == 200
        assert article_detail_response.json()["title"].startswith("AI 资讯日报")

        variants_response = client.get(f"/articles/{article_id}/variants")
        assert variants_response.status_code == 200
        variants_payload = variants_response.json()
        assert {variant["platform"] for variant in variants_payload} == {"wechat", "x", "telegram"}
        assert all(variant["content"] for variant in variants_payload)
def test_pipeline_debug_endpoints_expose_normalized_items_and_rebuild() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase03_api.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        ),
        connector_overrides={
            "github": StubConnector(items=[_github_item()]),
            "rss": StubConnector(items=[_openai_blog_item()]),
        },
    )

    with TestClient(app) as client:
        ingest_response = client.post("/ingest/run", json={"source_slugs": ["github-trending", "openai-blog"]})
        assert ingest_response.status_code == 200

        normalized_response = client.get("/normalized-items")
        assert normalized_response.status_code == 200
        normalized_items = normalized_response.json()
        assert len(normalized_items) == 2
        assert normalized_items[0]["canonical_url"].startswith("https://")
        assert normalized_items[0]["language"] == "en"

        rebuild_response = client.post("/pipeline/stories/rebuild")
        assert rebuild_response.status_code == 200
        rebuild_payload = rebuild_response.json()
        assert rebuild_payload["normalized_items"] == 2
        assert rebuild_payload["stories"] == 1

        stories_response = client.get("/stories")
        assert stories_response.status_code == 200
        story_id = stories_response.json()[0]["id"]

        approve_response = client.post(f"/stories/{story_id}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == StoryStatus.APPROVED
