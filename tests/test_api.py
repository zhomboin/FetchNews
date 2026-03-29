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


def _story_payload(
    story_key: str,
    cluster_title: str,
    summary: str,
    score: float,
    tags: list[str],
    source_links: list[str],
) -> dict:
    return StoryCreatePayload(
        story_key=story_key,
        cluster_title=cluster_title,
        summary=summary,
        highlights=["聚焦真实工作流", "强调评测一致性"],
        source_links=source_links,
        tags=tags,
        risk_flags=[],
        score=score,
        item_count=2,
        first_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC).isoformat(),
        last_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC).isoformat(),
    ).model_dump(mode="json")


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
            json=_story_payload(
                story_key="story-api-1",
                cluster_title="Mistral ships a new inference stack",
                summary="Mistral 发布了新的推理栈更新。",
                score=8.6,
                tags=["release"],
                source_links=["https://mistral.ai/news"],
            ),
        )
        assert create_response.status_code == 201
        story_id = create_response.json()["id"]

        approve_response = client.post(f"/stories/{story_id}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == StoryStatus.APPROVED

        generate_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-03-25"},
        )
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


def test_daily_digest_generation_can_scope_stories_and_store_note() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase04_scope.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        first_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase04-1",
                cluster_title="OpenAI updates agent evaluation stack",
                summary="OpenAI 更新了 agent 评测链路，强调真实工作流验证。",
                score=9.4,
                tags=["agent", "evaluation"],
                source_links=["https://openai.com/blog/agent-evals"],
            ),
        )
        second_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase04-2",
                cluster_title="Anthropic improves coding workflow tooling",
                summary="Anthropic 发布了新的 coding workflow 工具说明。",
                score=8.9,
                tags=["coding", "workflow"],
                source_links=["https://anthropic.com/news/coding-workflow"],
            ),
        )
        assert first_story_response.status_code == 201
        assert second_story_response.status_code == 201
        first_story_id = first_story_response.json()["id"]
        second_story_id = second_story_response.json()["id"]

        assert client.post(f"/stories/{first_story_id}/approve").status_code == 200
        assert client.post(f"/stories/{second_story_id}/approve").status_code == 200

        generate_response = client.post(
            "/articles/generate/daily",
            json={
                "target_date": "2026-03-28",
                "story_ids": [first_story_id],
                "generation_note": "优先突出 agent 工作流与评测方向。",
            },
        )
        assert generate_response.status_code == 200
        article_payload = generate_response.json()
        assert article_payload["status"] == "ready"
        assert article_payload["story_count"] == 1
        assert article_payload["variant_count"] == 3
        assert article_payload["generation_note"] == "优先突出 agent 工作流与评测方向。"
        article_id = article_payload["id"]

        articles_response = client.get("/articles")
        assert articles_response.status_code == 200
        articles_payload = articles_response.json()
        assert len(articles_payload) == 1
        assert articles_payload[0]["id"] == article_id
        assert articles_payload[0]["variant_count"] == 3
        assert articles_payload[0]["story_count"] == 1

        article_detail_response = client.get(f"/articles/{article_id}")
        assert article_detail_response.status_code == 200
        detail_payload = article_detail_response.json()
        assert detail_payload["title"].startswith("AI 资讯日报")
        assert detail_payload["story_ids"] == [first_story_id]
        assert detail_payload["story_keys"] == ["story-phase04-1"]
        assert detail_payload["generation_note"] == "优先突出 agent 工作流与评测方向。"

        variants_response = client.get(f"/articles/{article_id}/variants")
        assert variants_response.status_code == 200
        variants_payload = variants_response.json()
        assert {variant["platform"] for variant in variants_payload} == {"wechat", "x", "telegram"}
        assert all(variant["content"] for variant in variants_payload)
        assert "OpenAI updates agent evaluation stack" in variants_payload[0]["content"] or "OpenAI updates agent evaluation stack" in variants_payload[1]["content"]



def test_publish_job_result_writeback_and_retry_updates_article_status() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase05_publish.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase05-1",
                cluster_title="OpenAI ships a new agent runtime",
                summary="OpenAI 发布了新的 agent runtime。",
                score=9.1,
                tags=["agent", "runtime"],
                source_links=["https://openai.com/blog/agent-runtime"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        generate_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-03-29"},
        )
        assert generate_response.status_code == 200
        article_id = generate_response.json()["id"]
        assert generate_response.json()["status"] == "ready"

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x"], "scheduled_for": "2026-03-29T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs_payload = publish_response.json()["jobs"]
        assert len(jobs_payload) == 2
        first_job_id = jobs_payload[0]["id"]
        second_job_id = jobs_payload[1]["id"]

        article_after_schedule = client.get(f"/articles/{article_id}")
        assert article_after_schedule.status_code == 200
        assert article_after_schedule.json()["status"] == "scheduled"

        first_result_response = client.post(
            f"/publish-jobs/{first_job_id}/result",
            json={"status": "published", "external_id": "wx-001"},
        )
        assert first_result_response.status_code == 200
        assert first_result_response.json()["status"] == "published"

        article_during_publish = client.get(f"/articles/{article_id}")
        assert article_during_publish.status_code == 200
        assert article_during_publish.json()["status"] == "scheduled"

        failed_result_response = client.post(
            f"/publish-jobs/{second_job_id}/result",
            json={"status": "failed", "error_message": "rate limit"},
        )
        assert failed_result_response.status_code == 200
        assert failed_result_response.json()["status"] == "failed"
        assert failed_result_response.json()["error_message"] == "rate limit"

        article_failed = client.get(f"/articles/{article_id}")
        assert article_failed.status_code == 200
        assert article_failed.json()["status"] == "failed"

        retry_response = client.post(f"/publish-jobs/{second_job_id}/retry")
        assert retry_response.status_code == 200
        assert retry_response.json()["status"] == "scheduled"
        assert retry_response.json()["retries"] == 1

        article_after_retry = client.get(f"/articles/{article_id}")
        assert article_after_retry.status_code == 200
        assert article_after_retry.json()["status"] == "scheduled"

        final_result_response = client.post(
            f"/publish-jobs/{second_job_id}/result",
            json={"status": "published", "external_id": "x-002"},
        )
        assert final_result_response.status_code == 200
        assert final_result_response.json()["status"] == "published"

        article_published = client.get(f"/articles/{article_id}")
        assert article_published.status_code == 200
        assert article_published.json()["status"] == "published"

        jobs_response = client.get("/publish-jobs")
        assert jobs_response.status_code == 200
        job_statuses = {job["id"]: job["status"] for job in jobs_response.json()}
        assert job_statuses[first_job_id] == "published"
        assert job_statuses[second_job_id] == "published"
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
