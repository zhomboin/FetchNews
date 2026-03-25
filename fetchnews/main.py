from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.db.base import Base
from fetchnews.db.session import create_engine_and_factory, init_database, session_scope
from fetchnews.models import ArticleDraft, ArticleStatus, PublishJob, PublishJobStatus, Story, StoryStatus
from fetchnews.pipeline.generation import generate_daily_digest
from fetchnews.schemas import PublishJobResponse, PublishRequest, StoryCandidate, StoryCreatePayload, StoryResponse
from fetchnews.settings import Settings


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine, self.session_factory = create_engine_and_factory(settings.database_url)
        if settings.environment == "test":
            Base.metadata.drop_all(bind=self.engine)
        init_database(self.engine)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    state = AppState(resolved_settings)
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

    @app.post("/stories", response_model=StoryResponse, status_code=201)
    def create_story(payload: StoryCreatePayload, db: Session = Depends(get_db)) -> StoryResponse:
        story = Story(status=StoryStatus.PENDING, **payload.model_dump())
        db.add(story)
        db.commit()
        db.refresh(story)
        return StoryResponse(id=story.id, status=story.status, **payload.model_dump())

    @app.get("/stories", response_model=list[StoryResponse])
    def list_stories(db: Session = Depends(get_db)) -> list[StoryResponse]:
        stories = db.scalars(select(Story).order_by(Story.score.desc())).all()
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

    @app.post("/articles/generate/daily")
    def generate_daily_article(target_date: date, db: Session = Depends(get_db)) -> dict[str, object]:
        approved_stories = db.scalars(select(Story).where(Story.status == StoryStatus.APPROVED)).all()
        candidates = [
            StoryCandidate(
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
            for story in approved_stories
        ]
        digest = generate_daily_digest(target_date=target_date, stories=candidates)

        article = db.scalar(select(ArticleDraft).where(ArticleDraft.target_date == target_date))
        if article is None:
            article = ArticleDraft(
                target_date=target_date,
                title=digest.article.title,
                summary=digest.article.summary,
                body=digest.article.body,
                story_keys=digest.article.story_keys,
                status=ArticleStatus.READY,
            )
            db.add(article)
        else:
            article.title = digest.article.title
            article.summary = digest.article.summary
            article.body = digest.article.body
            article.story_keys = digest.article.story_keys
            article.status = ArticleStatus.READY
        db.commit()
        db.refresh(article)
        return {"id": article.id, "title": article.title, "summary": article.summary}

    @app.get("/articles/{article_id}")
    def get_article(article_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return {
            "id": article.id,
            "target_date": article.target_date,
            "title": article.title,
            "summary": article.summary,
            "body": article.body,
            "story_keys": article.story_keys,
            "status": article.status,
        }

    @app.get("/articles/{article_id}/variants")
    def get_article_variants(article_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return {
            "wechat": article.title,
            "x": f"{article.title} | {article.summary}",
            "telegram": article.summary,
        }

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


app = create_app()
