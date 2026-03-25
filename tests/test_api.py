from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fetchnews.main import create_app
from fetchnews.models import StoryStatus
from fetchnews.schemas import StoryCreatePayload
from fetchnews.settings import Settings


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
