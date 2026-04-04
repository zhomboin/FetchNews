from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from fetchnews.db.session import session_scope
from fetchnews.main import create_app
from fetchnews.models import Story, StoryStatus
from fetchnews.schemas import RawIngestedItem, StoryCreatePayload
from fetchnews.settings import Settings


class StubConnector:
    def __init__(self, items: list[RawIngestedItem] | None = None) -> None:
        self.items = items or []

    def fetch(self, _source) -> list[RawIngestedItem]:
        return self.items


class FailingConnector:
    def fetch(self, _source) -> list[RawIngestedItem]:
        raise RuntimeError("rate limit from source")


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
        highlights=["Focuses on production workflow", "Emphasizes evaluation consistency"],
        source_links=source_links,
        tags=tags,
        risk_flags=[],
        score=score,
        item_count=2,
        first_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 3, 28, 9, 0, tzinfo=UTC),
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
                summary="Mistral expands its inference stack for production deployment.",
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
                summary="OpenAI refreshed its agent evaluation stack for production teams.",
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
                summary="Anthropic improved coding workflow tooling for internal developers.",
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

        generation_note = "Prioritize agent evaluation updates and keep the digest narrowly scoped."
        generate_response = client.post(
            "/articles/generate/daily",
            json={
                "target_date": "2026-03-28",
                "story_ids": [first_story_id],
                "generation_note": generation_note,
            },
        )
        assert generate_response.status_code == 200
        article_payload = generate_response.json()
        assert article_payload["status"] == "ready"
        assert article_payload["story_count"] == 1
        assert article_payload["variant_count"] == 3
        assert article_payload["generation_note"] == generation_note
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
        assert detail_payload["title"].startswith("AI ")
        assert detail_payload["title"].endswith("2026-03-28")
        assert detail_payload["story_ids"] == [first_story_id]
        assert detail_payload["story_keys"] == ["story-phase04-1"]
        assert detail_payload["generation_note"] == generation_note

        variants_response = client.get(f"/articles/{article_id}/variants")
        assert variants_response.status_code == 200
        variants_payload = variants_response.json()
        assert {variant["platform"] for variant in variants_payload} == {"wechat", "x", "telegram"}
        assert all(variant["content"] for variant in variants_payload)
        assert any("OpenAI updates agent evaluation stack" in variant["content"] for variant in variants_payload)


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
                summary="OpenAI released a new agent runtime for production orchestration.",
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


def test_publish_dispatch_and_poll_complete_jobs() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase05_executor.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase05-executor-1",
                cluster_title="OpenAI ships an async publish flow",
                summary="Async publishing is now wired through the review console.",
                score=9.0,
                tags=["publishing"],
                source_links=["https://openai.com/blog/publish-flow"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-03-30"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        scheduled_for = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": scheduled_for},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        dispatch_response = client.post("/publish-jobs/dispatch-due")
        assert dispatch_response.status_code == 200
        assert dispatch_response.json()["jobs_dispatched"] == 1

        jobs_after_dispatch = client.get("/publish-jobs")
        assert jobs_after_dispatch.status_code == 200
        dispatched_job = next(job for job in jobs_after_dispatch.json() if job["id"] == job_id)
        assert dispatched_job["status"] == "scheduled"
        assert dispatched_job["provider_job_id"] is not None
        assert dispatched_job["external_id"] is None

        poll_response = client.post("/publish-jobs/poll")
        assert poll_response.status_code == 200
        assert poll_response.json()["jobs_polled"] == 1
        assert poll_response.json()["jobs_completed"] == 1

        final_jobs = client.get("/publish-jobs")
        assert final_jobs.status_code == 200
        final_job = next(job for job in final_jobs.json() if job["id"] == job_id)
        assert final_job["status"] == "published"
        assert final_job["external_id"] is not None

        article_detail = client.get(f"/articles/{article_id}")
        assert article_detail.status_code == 200
        assert article_detail.json()["status"] == "published"


def test_ops_summary_reports_ingest_and_publish_metrics() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_ops.db",
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

        approved_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-1",
                cluster_title="OpenAI publishes new evaluation workflow",
                summary="Evaluation workflow update.",
                score=9.2,
                tags=["evaluation"],
                source_links=["https://openai.com/blog/evals"],
            ),
        )
        pending_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-2",
                cluster_title="Community benchmark discussion trends upward",
                summary="Community benchmark discussion.",
                score=7.2,
                tags=["community"],
                source_links=["https://example.com/community-benchmark"],
            ),
        )
        assert approved_story_response.status_code == 201
        assert pending_story_response.status_code == 201

        approved_story_id = approved_story_response.json()["id"]
        assert client.post(f"/stories/{approved_story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-03-31"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x"], "scheduled_for": "2026-03-31T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs = publish_response.json()["jobs"]
        first_job_id = jobs[0]["id"]
        second_job_id = jobs[1]["id"]

        assert client.post(
            f"/publish-jobs/{first_job_id}/result",
            json={"status": "published", "external_id": "wx-metric-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{second_job_id}/result",
            json={"status": "failed", "error_message": "platform rejected"},
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()
        assert summary_payload["ingest_runs_total"] == 1
        assert summary_payload["items_ingested_total"] == 2
        assert summary_payload["stories_total"] == 3
        assert summary_payload["stories_approved"] >= 1
        assert summary_payload["stories_pending"] >= 1
        assert summary_payload["articles_total"] == 1
        assert summary_payload["articles_failed"] == 1
        assert summary_payload["publish_jobs_total"] == 2
        assert summary_payload["publish_jobs_published"] == 1
        assert summary_payload["publish_jobs_failed"] == 1
        assert summary_payload["publish_success_rate"] == 0.5


def test_ops_summary_includes_failure_groups_and_retry_suggestions() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_diagnostics.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        ),
        connector_overrides={
            "rss": FailingConnector(),
        },
    )

    with TestClient(app) as client:
        ingest_response = client.post("/ingest/run", json={"source_slugs": ["openai-blog"]})
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] in {"failed", "completed_with_errors"}

        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-failure-1",
                cluster_title="Platform moderation rejects one post",
                summary="A platform rejected one publish task.",
                score=8.4,
                tags=["publishing"],
                source_links=["https://example.com/platform-rejected"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-04-01"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["x"], "scheduled_for": "2026-04-01T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{job_id}/result",
            json={"status": "failed", "error_message": "platform rejected"},
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        failure_groups = summary_response.json()["recent_failure_groups"]

        publish_group = next(group for group in failure_groups if group["category"] == "publish")
        ingest_group = next(group for group in failure_groups if group["category"] == "ingest")

        assert publish_group["reason"] == "moderation"
        assert publish_group["count"] == 1
        assert "moderation policy" in publish_group["suggestion"]

        assert ingest_group["reason"] == "rate limit from source"
        assert ingest_group["count"] == 1
        assert "Reduce ingest frequency" in ingest_group["suggestion"]


def test_generate_weekly_and_monthly_digests_can_coexist_with_daily() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_periodic.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-periodic-1",
                cluster_title="OpenAI ships a weekly recap-worthy release",
                summary="A high-priority release suitable for daily and weekly recap.",
                score=9.3,
                tags=["release", "agent"],
                source_links=["https://openai.com/blog/weekly-release"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        daily_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-04-30"},
        )
        assert daily_response.status_code == 200
        assert daily_response.json()["period_type"] == "daily"
        assert daily_response.json()["title"].startswith("AI ")
        assert daily_response.json()["title"].endswith("2026-04-30")

        weekly_response = client.post(
            "/articles/generate/weekly",
            json={"target_date": "2026-04-30"},
        )
        assert weekly_response.status_code == 200
        assert weekly_response.json()["period_type"] == "weekly"
        assert weekly_response.json()["title"].startswith("AI ")
        assert weekly_response.json()["title"].endswith("2026-W18")

        monthly_response = client.post(
            "/articles/generate/monthly",
            json={"target_date": "2026-04-30"},
        )
        assert monthly_response.status_code == 200
        assert monthly_response.json()["period_type"] == "monthly"
        assert monthly_response.json()["title"].startswith("AI ")
        assert monthly_response.json()["title"].endswith("2026-04")

        articles_response = client.get("/articles")
        assert articles_response.status_code == 200
        articles_payload = articles_response.json()
        assert len(articles_payload) == 3
        assert {article["period_type"] for article in articles_payload} == {"daily", "weekly", "monthly"}


def test_ops_summary_includes_publish_platform_metrics() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_platform_metrics.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-platform-1",
                cluster_title="Platform metrics need per-channel visibility",
                summary="Publishing results should be grouped by platform.",
                score=8.8,
                tags=["publishing", "ops"],
                source_links=["https://example.com/platform-metrics"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-01"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x", "telegram"], "scheduled_for": "2026-05-01T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs = publish_response.json()["jobs"]
        jobs_by_platform = {job["platform"]: job["id"] for job in jobs}

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/result",
            json={"status": "published", "external_id": "wx-platform-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/result",
            json={"status": "published", "external_id": "tg-platform-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/result",
            json={"status": "failed", "error_message": "platform rejected"},
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        platform_metrics = {
            metric["platform"]: metric for metric in summary_response.json()["publish_platform_metrics"]
        }

        assert platform_metrics["wechat"]["total_jobs"] == 1
        assert platform_metrics["wechat"]["published_jobs"] == 1
        assert platform_metrics["wechat"]["success_rate"] == 1.0
        assert platform_metrics["telegram"]["published_jobs"] == 1
        assert platform_metrics["x"]["failed_jobs"] == 1
        assert platform_metrics["x"]["success_rate"] == 0.0
        assert platform_metrics["x"]["last_error"] == "platform rejected"


def test_ops_summary_includes_section_metrics_and_feedback_recommendations() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_feedback_loop.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        approved_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-feedback-1",
                cluster_title="Open-source agent runtime ships on GitHub",
                summary="An open-source agent runtime is now available on GitHub.",
                score=9.1,
                tags=["github", "agent", "runtime"],
                source_links=["https://github.com/example/agent-runtime"],
            ),
        )
        pending_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-feedback-2",
                cluster_title="New arXiv benchmark needs manual review",
                summary="A new benchmark paper still needs source confirmation.",
                score=7.4,
                tags=["paper", "benchmark", "research"],
                source_links=["https://arxiv.org/abs/1234.5678"],
            ),
        )
        assert approved_story_response.status_code == 201
        assert pending_story_response.status_code == 201

        approved_story_id = approved_story_response.json()["id"]
        pending_story_id = pending_story_response.json()["id"]
        assert client.post(f"/stories/{approved_story_id}/approve").status_code == 200

        with session_scope(app.state.container.session_factory) as session:
            pending_story = session.get(Story, pending_story_id)
            assert pending_story is not None
            pending_story.risk_flags = ["secondary_sources_only"]
            session.commit()

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-02"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["x"], "scheduled_for": "2026-05-02T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        publish_job_id = publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{publish_job_id}/result",
            json={"status": "failed", "error_message": "platform rejected"},
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()

        section_metrics = {
            metric["section"]: metric for metric in summary_payload["section_review_metrics"]
        }
        assert section_metrics["open_source"]["approved_stories"] == 1
        assert section_metrics["research"]["pending_stories"] == 1
        assert section_metrics["research"]["flagged_stories"] == 1

        recommendations = summary_payload["feedback_recommendations"]
        assert any(
            recommendation["category"] == "section" and recommendation["target"] == "research"
            for recommendation in recommendations
        )
        assert any(
            recommendation["category"] == "platform" and recommendation["target"] == "x"
            for recommendation in recommendations
        )
def test_publish_job_feedback_writeback_and_ops_engagement_metrics() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_publish_feedback.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-feedback-metrics-1",
                cluster_title="OpenAI ships a distribution analytics update",
                summary="Distribution analytics should track clicks and interactions after publishing.",
                score=9.0,
                tags=["publishing", "analytics"],
                source_links=["https://openai.com/blog/distribution-analytics"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-03"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x"], "scheduled_for": "2026-05-03T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs = publish_response.json()["jobs"]
        wechat_job_id = next(job["id"] for job in jobs if job["platform"] == "wechat")
        x_job_id = next(job["id"] for job in jobs if job["platform"] == "x")

        assert client.post(
            f"/publish-jobs/{wechat_job_id}/result",
            json={"status": "published", "external_id": "wx-feedback-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{x_job_id}/result",
            json={"status": "published", "external_id": "x-feedback-1"},
        ).status_code == 200

        feedback_response = client.post(
            f"/publish-jobs/{wechat_job_id}/feedback",
            json={
                "impressions": 1200,
                "opens": 460,
                "clicks": 125,
                "interactions": 54,
            },
        )
        assert feedback_response.status_code == 200
        feedback_payload = feedback_response.json()
        assert feedback_payload["performance_metrics"] == {
            "impressions": 1200,
            "opens": 460,
            "clicks": 125,
            "interactions": 54,
        }
        assert feedback_payload["metrics_recorded_at"] is not None

        second_feedback_response = client.post(
            f"/publish-jobs/{x_job_id}/feedback",
            json={
                "impressions": 800,
                "clicks": 64,
                "interactions": 20,
            },
        )
        assert second_feedback_response.status_code == 200

        jobs_response = client.get("/publish-jobs")
        assert jobs_response.status_code == 200
        jobs_payload = {job["id"]: job for job in jobs_response.json()}
        assert jobs_payload[wechat_job_id]["performance_metrics"]["clicks"] == 125
        assert jobs_payload[x_job_id]["performance_metrics"]["interactions"] == 20

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()
        assert summary_payload["engagement_impressions_total"] == 2000
        assert summary_payload["engagement_opens_total"] == 460
        assert summary_payload["engagement_clicks_total"] == 189
        assert summary_payload["engagement_interactions_total"] == 74

        platform_metrics = {
            metric["platform"]: metric for metric in summary_payload["publish_platform_metrics"]
        }
        assert platform_metrics["wechat"]["engagement_impressions"] == 1200
        assert platform_metrics["wechat"]["engagement_opens"] == 460
        assert platform_metrics["wechat"]["engagement_clicks"] == 125
        assert platform_metrics["wechat"]["engagement_interactions"] == 54
        assert platform_metrics["wechat"]["click_through_rate"] == 125 / 1200
        assert platform_metrics["wechat"]["interaction_rate"] == 54 / 1200
        assert platform_metrics["x"]["engagement_clicks"] == 64
        assert platform_metrics["x"]["interaction_rate"] == 20 / 800


def test_digest_generation_prioritizes_high_engagement_sections() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_section_engagement_ranking.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        open_source_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-section-open-source",
                cluster_title="Open-source agent runtime ships on GitHub",
                summary="A new agent runtime has been published as an open-source project.",
                score=9.2,
                tags=["github", "agent", "runtime"],
                source_links=["https://github.com/example/agent-runtime"],
            ),
        )
        research_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-section-research",
                cluster_title="New arXiv reasoning benchmark improves evaluation",
                summary="A reasoning benchmark paper improves evaluation quality.",
                score=8.8,
                tags=["paper", "benchmark", "reasoning"],
                source_links=["https://arxiv.org/abs/5678.1234"],
            ),
        )
        assert open_source_story_response.status_code == 201
        assert research_story_response.status_code == 201

        open_source_story_id = open_source_story_response.json()["id"]
        research_story_id = research_story_response.json()["id"]
        assert client.post(f"/stories/{open_source_story_id}/approve").status_code == 200
        assert client.post(f"/stories/{research_story_id}/approve").status_code == 200

        seed_article_response = client.post(
            "/articles/generate/daily",
            json={
                "target_date": "2026-05-04",
                "story_ids": [research_story_id],
                "generation_note": "Seed engagement history for research.",
            },
        )
        assert seed_article_response.status_code == 200
        seed_article_id = seed_article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{seed_article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": "2026-05-04T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        publish_job_id = publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{publish_job_id}/result",
            json={"status": "published", "external_id": "wx-section-ranking-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{publish_job_id}/feedback",
            json={
                "impressions": 1500,
                "opens": 520,
                "clicks": 180,
                "interactions": 96,
            },
        ).status_code == 200

        digest_response = client.post(
            "/articles/generate/daily",
            json={
                "target_date": "2026-05-05",
                "story_ids": [open_source_story_id, research_story_id],
                "generation_note": "Validate section momentum ordering.",
            },
        )
        assert digest_response.status_code == 200
        digest_payload = digest_response.json()

        assert digest_payload["sections"][0] == "research"
        assert digest_payload["story_keys"][0] == "story-phase06-section-research"


def test_ops_summary_exposes_high_performing_section_metrics() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_section_engagement_metrics.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="story-phase06-section-metrics",
                cluster_title="Reasoning benchmark paper keeps momentum",
                summary="A research paper continues to drive strong clicks after publishing.",
                score=8.6,
                tags=["paper", "benchmark", "reasoning"],
                source_links=["https://arxiv.org/abs/2468.1357"],
            ),
        )
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-06"},
        )
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": "2026-05-06T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        publish_job_id = publish_response.json()["jobs"][0]["id"]

        assert client.post(
            f"/publish-jobs/{publish_job_id}/result",
            json={"status": "published", "external_id": "wx-section-metrics-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{publish_job_id}/feedback",
            json={
                "impressions": 900,
                "clicks": 117,
                "interactions": 55,
            },
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()

        section_metrics = {
            metric["section"]: metric for metric in summary_payload["section_review_metrics"]
        }
        assert section_metrics["research"]["engagement_impressions"] == 900
        assert section_metrics["research"]["engagement_clicks"] == 117
        assert section_metrics["research"]["click_through_rate"] == 117 / 900
        assert section_metrics["research"]["momentum_tier"] == "hot"

def test_periodic_digests_balance_section_mix_using_engagement_feedback() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_periodic_section_mix.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_payloads = [
            _story_payload(
                story_key="periodic-mix-research-1",
                cluster_title="Reasoning benchmark paper sets the weekly agenda",
                summary="A research benchmark is drawing strong downstream attention.",
                score=8.8,
                tags=["paper", "benchmark", "reasoning"],
                source_links=["https://arxiv.org/abs/7000.0001"],
            ),
            _story_payload(
                story_key="periodic-mix-research-2",
                cluster_title="Another research paper strengthens evaluation coverage",
                summary="A second research paper belongs in the same recap window.",
                score=8.6,
                tags=["paper", "evaluation", "reasoning"],
                source_links=["https://arxiv.org/abs/7000.0002"],
            ),
            _story_payload(
                story_key="periodic-mix-open-source-1",
                cluster_title="Open-source agent runtime lands on GitHub",
                summary="A new open-source runtime deserves recap coverage.",
                score=8.1,
                tags=["github", "agent", "runtime"],
                source_links=["https://github.com/example/runtime-1"],
            ),
            _story_payload(
                story_key="periodic-mix-open-source-2",
                cluster_title="Open-source toolkit expands deployment support",
                summary="A second open-source release belongs in the same recap.",
                score=7.9,
                tags=["github", "deployment", "toolkit"],
                source_links=["https://github.com/example/runtime-2"],
            ),
        ]

        story_ids: list[int] = []
        for payload in story_payloads:
            story_response = client.post("/stories", json=payload)
            assert story_response.status_code == 201
            story_id = story_response.json()["id"]
            story_ids.append(story_id)
            assert client.post(f"/stories/{story_id}/approve").status_code == 200

        research_seed_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-09", "story_ids": story_ids[:2]},
        )
        assert research_seed_response.status_code == 200
        research_seed_article_id = research_seed_response.json()["id"]
        publish_response = client.post(
            f"/articles/{research_seed_article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": "2026-05-09T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        publish_job_id = publish_response.json()["jobs"][0]["id"]
        assert client.post(
            f"/publish-jobs/{publish_job_id}/result",
            json={"status": "published", "external_id": "wx-periodic-mix-1"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{publish_job_id}/feedback",
            json={"impressions": 1800, "clicks": 230, "interactions": 104},
        ).status_code == 200

        weekly_response = client.post(
            "/articles/generate/weekly",
            json={"target_date": "2026-05-10", "story_ids": story_ids},
        )
        assert weekly_response.status_code == 200
        weekly_payload = weekly_response.json()

        monthly_response = client.post(
            "/articles/generate/monthly",
            json={"target_date": "2026-05-31", "story_ids": story_ids},
        )
        assert monthly_response.status_code == 200
        monthly_payload = monthly_response.json()

        assert weekly_payload["sections"][0] == "research"
        assert weekly_payload["story_keys"][0] == "periodic-mix-research-1"
        assert weekly_payload["story_keys"][1] == "periodic-mix-open-source-1"
        assert monthly_payload["sections"][0] == "research"
        assert monthly_payload["story_keys"][0] == "periodic-mix-research-1"
        assert monthly_payload["story_keys"][1] == "periodic-mix-open-source-1"

def test_generate_digest_adapts_platform_variants_from_engagement_history() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_platform_copy_strategy.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        seed_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="platform-copy-seed-story",
                cluster_title="Seed article establishes platform engagement history",
                summary="A seed article exists only to create platform-specific performance signals.",
                score=8.7,
                tags=["analysis", "agent"],
                source_links=["https://openai.com/blog/platform-seed"],
            ),
        )
        next_story_response = client.post(
            "/stories",
            json=_story_payload(
                story_key="platform-copy-next-story",
                cluster_title="Follow-up digest should adapt platform copy",
                summary="The next digest should change its platform variants based on recorded engagement.",
                score=8.9,
                tags=["release", "workflow"],
                source_links=["https://openai.com/blog/platform-follow-up"],
            ),
        )
        assert seed_story_response.status_code == 201
        assert next_story_response.status_code == 201
        seed_story_id = seed_story_response.json()["id"]
        next_story_id = next_story_response.json()["id"]
        assert client.post(f"/stories/{seed_story_id}/approve").status_code == 200
        assert client.post(f"/stories/{next_story_id}/approve").status_code == 200

        seed_article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-11", "story_ids": [seed_story_id]},
        )
        assert seed_article_response.status_code == 200
        seed_article_id = seed_article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{seed_article_id}/publish",
            json={"platforms": ["wechat", "x", "telegram"], "scheduled_for": "2026-05-11T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs_by_platform = {job["platform"]: job["id"] for job in publish_response.json()["jobs"]}

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/result",
            json={"status": "published", "external_id": "wx-platform-copy-seed"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/result",
            json={"status": "published", "external_id": "x-platform-copy-seed"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/result",
            json={"status": "published", "external_id": "tg-platform-copy-seed"},
        ).status_code == 200

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/feedback",
            json={"impressions": 1400, "opens": 560, "clicks": 92, "interactions": 24},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/feedback",
            json={"impressions": 900, "clicks": 58, "interactions": 61},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/feedback",
            json={"impressions": 1100, "clicks": 126, "interactions": 19},
        ).status_code == 200

        next_article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-12", "story_ids": [next_story_id]},
        )
        assert next_article_response.status_code == 200
        next_article_id = next_article_response.json()["id"]

        variants_response = client.get(f"/articles/{next_article_id}/variants")
        assert variants_response.status_code == 200
        variants_by_platform = {variant["platform"]: variant["content"] for variant in variants_response.json()}

        assert "\u7f16\u8f91\u6458\u8981\uff1a" in variants_by_platform["wechat"]
        assert "\u672c\u671f\u680f\u76ee\uff1a" in variants_by_platform["wechat"]
        assert "\u4f60\u6700\u60f3\u7ee7\u7eed\u8ddf\u8fdb\u54ea\u6761\uff1f" in variants_by_platform["x"]
        assert "\u901f\u89c8\u6e05\u5355" in variants_by_platform["telegram"]


def test_periodic_variants_combine_platform_strategy_with_section_mix() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_phase06_periodic_platform_variants.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_payloads = [
            _story_payload(
                story_key="periodic-variant-research-1",
                cluster_title="Reasoning benchmark paper anchors the recap",
                summary="Research momentum should shape the weekly and monthly variants.",
                score=8.9,
                tags=["paper", "benchmark", "reasoning"],
                source_links=["https://arxiv.org/abs/8000.0001"],
            ),
            _story_payload(
                story_key="periodic-variant-open-source-1",
                cluster_title="Open-source runtime broadens deployment coverage",
                summary="Open-source tooling should appear in the same recap window.",
                score=8.3,
                tags=["github", "runtime", "deployment"],
                source_links=["https://github.com/example/runtime-periodic"],
            ),
        ]

        story_ids: list[int] = []
        for payload in story_payloads:
            story_response = client.post("/stories", json=payload)
            assert story_response.status_code == 201
            story_id = story_response.json()["id"]
            story_ids.append(story_id)
            assert client.post(f"/stories/{story_id}/approve").status_code == 200

        seed_article_response = client.post(
            "/articles/generate/daily",
            json={"target_date": "2026-05-13", "story_ids": story_ids},
        )
        assert seed_article_response.status_code == 200
        seed_article_id = seed_article_response.json()["id"]
        publish_response = client.post(
            f"/articles/{seed_article_id}/publish",
            json={"platforms": ["wechat", "x", "telegram"], "scheduled_for": "2026-05-13T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs_by_platform = {job["platform"]: job["id"] for job in publish_response.json()["jobs"]}

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/result",
            json={"status": "published", "external_id": "wx-periodic-variant-seed"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/result",
            json={"status": "published", "external_id": "x-periodic-variant-seed"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/result",
            json={"status": "published", "external_id": "tg-periodic-variant-seed"},
        ).status_code == 200

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/feedback",
            json={"impressions": 1500, "opens": 620, "clicks": 88, "interactions": 18},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/feedback",
            json={"impressions": 950, "clicks": 54, "interactions": 64},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/feedback",
            json={"impressions": 1200, "clicks": 132, "interactions": 17},
        ).status_code == 200

        weekly_response = client.post(
            "/articles/generate/weekly",
            json={"target_date": "2026-05-17", "story_ids": story_ids},
        )
        assert weekly_response.status_code == 200
        weekly_article_id = weekly_response.json()["id"]
        weekly_variants = {
            variant["platform"]: variant["content"]
            for variant in client.get(f"/articles/{weekly_article_id}/variants").json()
        }

        monthly_response = client.post(
            "/articles/generate/monthly",
            json={"target_date": "2026-05-31", "story_ids": story_ids},
        )
        assert monthly_response.status_code == 200
        monthly_article_id = monthly_response.json()["id"]
        monthly_variants = {
            variant["platform"]: variant["content"]
            for variant in client.get(f"/articles/{monthly_article_id}/variants").json()
        }

        assert "\u672c\u5468\u4e3b\u7ebf\u680f\u76ee\uff1a" in weekly_variants["wechat"]
        assert "\u680f\u76ee\u8f6e\u503c\uff1a" in weekly_variants["wechat"]
        assert "\u672c\u5468\u6700\u503c\u5f97\u7ee7\u7eed\u8ffd\u8e2a\u7684\u680f\u76ee\u662f" in weekly_variants["x"]
        assert "\u680f\u76ee\u901f\u89c8" in weekly_variants["telegram"]

        assert "\u672c\u6708\u4e3b\u7ebf\u680f\u76ee\uff1a" in monthly_variants["wechat"]
        assert "\u680f\u76ee\u8f6e\u503c\uff1a" in monthly_variants["wechat"]
        assert "\u672c\u6708\u6700\u503c\u5f97\u7ee7\u7eed\u8ffd\u8e2a\u7684\u680f\u76ee\u662f" in monthly_variants["x"]
        assert "\u680f\u76ee\u901f\u89c8" in monthly_variants["telegram"]
