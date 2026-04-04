from datetime import UTC, datetime
import os

os.environ.setdefault("APP_DATABASE_URL", "sqlite:///./test_import_bootstrap.db")

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from fetchnews.db.session import create_engine_and_factory, init_database
from fetchnews.main import create_app
from fetchnews.settings import Settings


def _story_payload() -> dict:
    return {
        "story_key": "auth-story-1",
        "cluster_title": "Protected workflow story",
        "summary": "A protected story used to verify auth and audit behavior.",
        "highlights": ["Auth required", "Audit required"],
        "source_links": ["https://example.com/protected-story"],
        "tags": ["workflow"],
        "risk_flags": [],
        "score": 8.4,
        "item_count": 1,
        "first_seen_at": "2026-06-01T09:00:00Z",
        "last_seen_at": "2026-06-01T09:00:00Z",
    }


def _login(client: TestClient, username: str = "admin", password: str = "admin-secret") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_enabled_requires_login_and_records_audit_logs() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_auth_enabled.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
            auth_enabled=True,
            bootstrap_admin_username="admin",
            bootstrap_admin_password="admin-secret",
        )
    )

    with TestClient(app) as client:
        unauthorized_response = client.get("/stories")
        assert unauthorized_response.status_code == 401

        headers = _login(client)

        create_response = client.post("/stories", json=_story_payload(), headers=headers)
        assert create_response.status_code == 201
        story_id = create_response.json()["id"]

        approve_response = client.post(f"/stories/{story_id}/approve", headers=headers)
        assert approve_response.status_code == 200

        with app.state.container.session_factory() as session:
            user_model = app.state.container.model_registry["user"]
            audit_log_model = app.state.container.model_registry["audit_log"]

            admin_user = session.scalar(select(user_model).where(user_model.username == "admin"))
            assert admin_user is not None
            audit_actions = [
                record.action
                for record in session.scalars(select(audit_log_model).order_by(audit_log_model.id.asc())).all()
            ]
            assert "auth.login" in audit_actions
            assert "story.approve" in audit_actions


def test_viewer_role_can_read_but_cannot_mutate() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_auth_roles.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
            auth_enabled=True,
            bootstrap_admin_username="admin",
            bootstrap_admin_password="admin-secret",
        )
    )

    with app.state.container.session_factory() as session:
        user_model = app.state.container.model_registry["user"]
        viewer = user_model(
            username="viewer",
            display_name="Viewer",
            role="viewer",
            password_hash="viewer-secret",
            is_active=True,
        )
        session.add(viewer)
        session.commit()

    with TestClient(app) as client:
        admin_headers = _login(client)
        create_response = client.post("/stories", json=_story_payload(), headers=admin_headers)
        assert create_response.status_code == 201

        viewer_headers = _login(client, username="viewer", password="viewer-secret")
        list_response = client.get("/stories", headers=viewer_headers)
        assert list_response.status_code == 200

        rebuild_response = client.post("/pipeline/stories/rebuild", headers=viewer_headers)
        assert rebuild_response.status_code == 403


def test_ops_summary_exposes_alerts_for_failed_runs_and_publish_jobs() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_ops_alerts.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post("/stories", json=_story_payload())
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post("/articles/generate/daily", json={"target_date": "2026-06-02"})
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat"], "scheduled_for": "2026-06-02T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        job_id = publish_response.json()["jobs"][0]["id"]

        assert client.post(
            f"/publish-jobs/{job_id}/result",
            json={"status": "failed", "error_message": "platform rejected"},
        ).status_code == 200

        with app.state.container.session_factory() as session:
            ingest_run_model = app.state.container.model_registry["ingest_run"]
            failed_run = ingest_run_model(
                requested_source_slugs=["openai-blog"],
                status="completed_with_errors",
                sources_total=1,
                sources_succeeded=0,
                sources_failed=1,
                items_ingested=0,
                errors=[{"source_slug": "openai-blog", "message": "feed timeout"}],
                started_at=datetime(2026, 6, 2, 8, 0, tzinfo=UTC),
                finished_at=datetime(2026, 6, 2, 8, 1, tzinfo=UTC),
            )
            session.add(failed_run)
            session.commit()

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        payload = summary_response.json()
        assert payload["alerts"]
        alert_categories = {alert["category"] for alert in payload["alerts"]}
        assert {"ingest", "publish"}.issubset(alert_categories)


def test_ops_summary_groups_publish_failures_by_platform_and_category() -> None:
    app = create_app(
        Settings(
            database_url="sqlite:///./test_ops_publish_failure_groups.db",
            redis_url="redis://localhost:6379/0",
            environment="test",
        )
    )

    with TestClient(app) as client:
        story_response = client.post("/stories", json=_story_payload())
        assert story_response.status_code == 201
        story_id = story_response.json()["id"]
        assert client.post(f"/stories/{story_id}/approve").status_code == 200

        article_response = client.post("/articles/generate/daily", json={"target_date": "2026-06-03"})
        assert article_response.status_code == 200
        article_id = article_response.json()["id"]

        publish_response = client.post(
            f"/articles/{article_id}/publish",
            json={"platforms": ["wechat", "x", "telegram"], "scheduled_for": "2026-06-03T18:00:00Z"},
        )
        assert publish_response.status_code == 200
        jobs_by_platform = {job["platform"]: job["id"] for job in publish_response.json()["jobs"]}

        assert client.post(
            f"/publish-jobs/{jobs_by_platform['wechat']}/result",
            json={"status": "failed", "error_message": "wechat auth token expired"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['x']}/result",
            json={"status": "failed", "error_message": "x credential missing"},
        ).status_code == 200
        assert client.post(
            f"/publish-jobs/{jobs_by_platform['telegram']}/result",
            json={"status": "failed", "error_message": "platform rejected by moderation"},
        ).status_code == 200

        summary_response = client.get("/ops/summary")
        assert summary_response.status_code == 200
        payload = summary_response.json()

        publish_groups = [group for group in payload["recent_failure_groups"] if group["category"] == "publish"]
        assert publish_groups[0]["reason"] == "auth"
        assert publish_groups[0]["count"] == 2
        assert publish_groups[0]["targets"] == ["wechat", "x"]

        moderation_group = next(group for group in publish_groups if group["reason"] == "moderation")
        assert moderation_group["count"] == 1
        assert moderation_group["targets"] == ["telegram"]

        metrics_by_platform = {metric["platform"]: metric for metric in payload["publish_platform_metrics"]}
        assert metrics_by_platform["wechat"]["last_failure_category"] == "auth"
        assert metrics_by_platform["x"]["last_failure_category"] == "auth"
        assert metrics_by_platform["telegram"]["last_failure_category"] == "moderation"


def test_postgres_bootstrap_mode_skip_does_not_create_tables() -> None:
    engine, _factory = create_engine_and_factory("sqlite:///./test_bootstrap_skip.db")

    init_database(engine, bootstrap_mode="skip")

    inspector = inspect(engine)
    assert inspector.get_table_names() == []
