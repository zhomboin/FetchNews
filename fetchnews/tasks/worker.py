from __future__ import annotations

from typing import Any

from celery import Celery

from fetchnews.db.base import Base
from fetchnews.db.session import create_engine_and_factory, init_database, session_scope
from fetchnews.settings import Settings
from fetchnews.sources.connectors import build_default_connector_registry
from fetchnews.sources.service import execute_ingest_run, ingest_run_to_response

settings = Settings()
celery_app = Celery("fetchnews", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {}


def run_ingestion_job(
    source_slugs: list[str] | None = None,
    settings: Settings | None = None,
    connector_overrides: dict[str, Any] | None = None,
) -> dict[str, object]:
    resolved_settings = settings or Settings()
    engine, session_factory = create_engine_and_factory(resolved_settings.database_url)
    if resolved_settings.environment == "test":
        Base.metadata.drop_all(bind=engine)
    init_database(engine)

    connector_registry = build_default_connector_registry()
    if connector_overrides:
        connector_registry.update(connector_overrides)

    with session_scope(session_factory) as session:
        run = execute_ingest_run(
            session,
            source_slugs=source_slugs,
            connector_registry=connector_registry,
        )
        return ingest_run_to_response(run).model_dump(mode="json")


@celery_app.task(name="fetchnews.healthcheck")
def healthcheck() -> str:
    return "ok"


@celery_app.task(name="fetchnews.ingest.run")
def run_ingestion_task(source_slugs: list[str] | None = None) -> dict[str, object]:
    return run_ingestion_job(source_slugs=source_slugs)
