from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.db.base import Base
from fetchnews.db.session import create_engine_and_factory, init_database, session_scope
from fetchnews.models import (
    ArticleDraft,
    IngestRun,
    NormalizedItemRecord,
    PublishJob,
    PublishJobStatus,
    Story,
    StoryStatus,
)
from fetchnews.pipeline.article_service import (
    article_to_response,
    generate_and_persist_daily_digest,
    list_article_variants,
    list_articles,
)
from fetchnews.pipeline.service import run_story_pipeline
from fetchnews.schemas import (
    ArticleDraftResponse,
    IngestRunRequest,
    IngestRunResponse,
    NormalizedItem,
    PipelineRebuildResponse,
    PostVariantResponse,
    PublishJobResponse,
    PublishRequest,
    StoryCreatePayload,
    StoryResponse,
)
from fetchnews.settings import Settings
from fetchnews.sources.catalog import get_source_specs
from fetchnews.sources.connectors import build_default_connector_registry
from fetchnews.sources.service import execute_ingest_run, ingest_run_to_response


class AppState:
    def __init__(self, settings: Settings, connector_overrides: dict[str, Any] | None = None) -> None:
        self.settings = settings
        self.engine, self.session_factory = create_engine_and_factory(settings.database_url)
        if settings.environment == "test":
            Base.metadata.drop_all(bind=self.engine)
        init_database(self.engine)
        self.connector_registry = build_default_connector_registry()
        if connector_overrides:
            self.connector_registry.update(connector_overrides)


def create_app(settings: Settings | None = None, connector_overrides: dict[str, Any] | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    state = AppState(resolved_settings, connector_overrides=connector_overrides)
    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = state
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_db() -> Session:
        with session_scope(state.session_factory) as session:
            yield session

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": resolved_settings.app_name}

    @app.get("/dashboard/summary")
    def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, int]:
        stories = db.scalar(select(func.count()).select_from(Story)) or 0
        articles = db.scalar(select(func.count()).select_from(ArticleDraft)) or 0
        jobs = db.scalar(select(func.count()).select_from(PublishJob)) or 0
        return {"stories": stories, "articles": articles, "publish_jobs": jobs}

    @app.get("/sources")
    def list_sources() -> list[dict[str, object]]:
        return [spec.model_dump() for spec in get_source_specs()]

    @app.post("/ingest/run", response_model=IngestRunResponse)
    def run_ingestion(payload: IngestRunRequest, db: Session = Depends(get_db)) -> IngestRunResponse:
        try:
            run = execute_ingest_run(
                db,
                source_slugs=payload.source_slugs,
                connector_registry=state.connector_registry,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ingest_run_to_response(run)

    @app.get("/ingest/runs", response_model=list[IngestRunResponse])
    def list_ingest_runs(db: Session = Depends(get_db)) -> list[IngestRunResponse]:
        runs = db.scalars(select(IngestRun).order_by(IngestRun.id.desc())).all()
        return [ingest_run_to_response(run) for run in runs]

    @app.get("/ingest/runs/{run_id}", response_model=IngestRunResponse)
    def get_ingest_run(run_id: int, db: Session = Depends(get_db)) -> IngestRunResponse:
        run = db.get(IngestRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ingest run not found")
        return ingest_run_to_response(run)

    @app.get("/normalized-items", response_model=list[NormalizedItem])
    def list_normalized_items(
        limit: int = Query(default=50, ge=1, le=200),
        db: Session = Depends(get_db),
    ) -> list[NormalizedItem]:
        items = db.scalars(
            select(NormalizedItemRecord)
            .order_by(NormalizedItemRecord.published_at.desc(), NormalizedItemRecord.id.desc())
            .limit(limit)
        ).all()
        return [_normalized_item_to_response(item) for item in items]

    @app.post("/pipeline/stories/rebuild", response_model=PipelineRebuildResponse)
    def rebuild_story_pipeline(db: Session = Depends(get_db)) -> PipelineRebuildResponse:
        result = run_story_pipeline(db)
        db.commit()
        return PipelineRebuildResponse(**result)

    @app.post("/stories", response_model=StoryResponse, status_code=201)
    def create_story(payload: StoryCreatePayload, db: Session = Depends(get_db)) -> StoryResponse:
        story = Story(status=StoryStatus.PENDING, **payload.model_dump())
        db.add(story)
        db.commit()
        db.refresh(story)
        return StoryResponse(id=story.id, status=story.status, **payload.model_dump())

    @app.get("/stories", response_model=list[StoryResponse])
    def list_stories(db: Session = Depends(get_db)) -> list[StoryResponse]:
        stories = db.scalars(select(Story).order_by(Story.score.desc(), Story.last_seen_at.desc())).all()
        return [
            StoryResponse(
                id=story.id,
                status=story.status,
                story_key=story.story_key,
                cluster_title=story.cluster_title,
                summary=story.summary,
                highlights=story.highlights,
                source_links=story.source_links,
                tags=story.tags,
                risk_flags=story.risk_flags,
                score=story.score,
                item_count=story.item_count,
                first_seen_at=story.first_seen_at,
                last_seen_at=story.last_seen_at,
            )
            for story in stories
        ]

    @app.post("/stories/{story_id}/approve")
    def approve_story(story_id: int, db: Session = Depends(get_db)) -> dict[str, str | int]:
        story = db.get(Story, story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")
        story.status = StoryStatus.APPROVED
        db.commit()
        return {"id": story.id, "status": story.status}

    @app.post("/articles/generate/daily", response_model=ArticleDraftResponse)
    def generate_daily_article(target_date: date, db: Session = Depends(get_db)) -> ArticleDraftResponse:
        article = generate_and_persist_daily_digest(db, target_date)
        db.commit()
        return article

    @app.get("/articles", response_model=list[ArticleDraftResponse])
    def list_article_drafts(db: Session = Depends(get_db)) -> list[ArticleDraftResponse]:
        return list_articles(db)

    @app.get("/articles/{article_id}", response_model=ArticleDraftResponse)
    def get_article(article_id: int, db: Session = Depends(get_db)) -> ArticleDraftResponse:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        variant_count = len(list_article_variants(db, article.id))
        return article_to_response(article, variant_count)

    @app.get("/articles/{article_id}/variants", response_model=list[PostVariantResponse])
    def get_article_variants(article_id: int, db: Session = Depends(get_db)) -> list[PostVariantResponse]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return list_article_variants(db, article.id)

    @app.post("/articles/{article_id}/publish")
    def publish_article(article_id: int, payload: PublishRequest, db: Session = Depends(get_db)) -> dict[str, list[PublishJobResponse]]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        jobs: list[PublishJobResponse] = []
        for platform in payload.platforms:
            job = PublishJob(
                article_id=article.id,
                platform=platform,
                scheduled_for=payload.scheduled_for,
                status=PublishJobStatus.SCHEDULED,
                retries=0,
                external_id=None,
            )
            db.add(job)
            db.flush()
            jobs.append(
                PublishJobResponse(
                    id=job.id,
                    article_id=job.article_id,
                    platform=job.platform,
                    scheduled_for=job.scheduled_for,
                    status=job.status,
                    retries=job.retries,
                    external_id=job.external_id,
                )
            )
        db.commit()
        return {"jobs": jobs}

    @app.get("/publish-jobs", response_model=list[PublishJobResponse])
    def list_publish_jobs(db: Session = Depends(get_db)) -> list[PublishJobResponse]:
        jobs = db.scalars(select(PublishJob).order_by(PublishJob.id.asc())).all()
        return [
            PublishJobResponse(
                id=job.id,
                article_id=job.article_id,
                platform=job.platform,
                scheduled_for=job.scheduled_for,
                status=job.status,
                retries=job.retries,
                external_id=job.external_id,
            )
            for job in jobs
        ]

    @app.post("/publish-jobs/{job_id}/retry")
    def retry_publish_job(job_id: int, db: Session = Depends(get_db)) -> dict[str, str | int]:
        job = db.get(PublishJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Publish job not found")
        job.retries += 1
        job.status = PublishJobStatus.SCHEDULED
        db.commit()
        return {"id": job.id, "status": job.status, "retries": job.retries}

    return app


def _normalized_item_to_response(item: NormalizedItemRecord) -> NormalizedItem:
    return NormalizedItem(
        raw_item_id=item.raw_item_id,
        source_slug=item.source_slug,
        source_priority=item.source_priority,
        external_id=item.external_id,
        canonical_url=item.canonical_url,
        title=item.title,
        normalized_title=item.normalized_title,
        author=item.author,
        published_at=item.published_at,
        summary=item.summary,
        content=item.content,
        language=item.language,
        tags=item.tags,
        keywords=item.keywords,
        metadata=item.payload,
    )


app = create_app()