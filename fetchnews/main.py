from __future__ import annotations

import secrets
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.db.base import Base
from fetchnews.db.session import create_engine_and_factory, init_database, session_scope
from fetchnews.models import (
    ArticleDraft,
    AuditLog,
    IngestRun,
    NormalizedItemRecord,
    PublishJob,
    Story,
    StoryStatus,
    User,
    UserRole,
)
from fetchnews.core.audit import record_audit_log
from fetchnews.core.security import authenticate_user, create_access_token, decode_access_token, ensure_bootstrap_admin, role_satisfies
from fetchnews.ops.service import build_ops_summary
from fetchnews.pipeline.article_service import (
    article_to_response,
    generate_and_persist_daily_digest,
    generate_and_persist_monthly_digest,
    generate_and_persist_weekly_digest,
    list_article_blocks,
    list_article_revisions,
    list_article_variants,
    list_articles,
    resolve_article_sections_for_story_ids,
)
from fetchnews.pipeline.editorial_revisions import rebuild_article_draft, list_editorial_actions, restore_article_revision, update_article_block
from fetchnews.pipeline.editorial_templates import ensure_default_digest_templates, list_digest_templates
from fetchnews.pipeline.service import run_story_pipeline
from fetchnews.publishing.service import (
    build_default_publisher_registry,
    create_publish_jobs,
    dispatch_due_publish_jobs,
    handle_publish_callback,
    poll_publish_jobs,
    publish_job_to_response,
    retry_publish_job,
    write_publish_job_feedback,
    write_publish_job_result,
)
from fetchnews.schemas import (
    ArticleDraftResponse,
    ArticleBlockResponse,
    ArticleBlockUpdateRequest,
    ArticleRebuildRequest,
    ArticleRevisionResponse,
    AuthConfigResponse,
    DigestTemplateResponse,
    EditorialActionResponse,
    AuthLoginRequest,
    AuthTokenResponse,
    AuthUserResponse,
    GenerateArticleRequest,
    GenerateDailyArticleRequest,
    IngestRunRequest,
    IngestRunResponse,
    NormalizedItem,
    OpsSummaryResponse,
    PipelineRebuildResponse,
    PostVariantResponse,
    PublishDispatchResponse,
    PublishJobFeedbackRequest,
    PublishJobResponse,
    PublishJobResultRequest,
    PublishPollResponse,
    PublishRequest,
    StoryCreatePayload,
    StoryResponse,
)
from fetchnews.settings import Settings
from fetchnews.sources.catalog import get_source_specs
from fetchnews.sources.governance import annotate_source_specs
from fetchnews.sources.connectors import build_default_connector_registry
from fetchnews.sources.service import execute_ingest_run, ingest_run_to_response


class AppState:
    def __init__(
        self,
        settings: Settings,
        connector_overrides: dict[str, Any] | None = None,
        publisher_overrides: dict[str, Any] | None = None,
    ) -> None:
        self.settings = settings
        self.engine, self.session_factory = create_engine_and_factory(settings.database_url)
        if settings.environment == "test":
            Base.metadata.drop_all(bind=self.engine)
        init_database(
            self.engine,
            database_url=settings.database_url,
            environment=settings.environment,
            bootstrap_mode=settings.database_bootstrap_mode,
        )
        self.connector_registry = build_default_connector_registry()
        if connector_overrides:
            self.connector_registry.update(connector_overrides)
        self.publisher_registry = build_default_publisher_registry(settings)
        if publisher_overrides:
            self.publisher_registry.update(publisher_overrides)
        self.model_registry = {
            "user": User,
            "audit_log": AuditLog,
            "ingest_run": IngestRun,
            "story": Story,
            "article": ArticleDraft,
            "publish_job": PublishJob,
        }
        with session_scope(self.session_factory) as session:
            ensure_bootstrap_admin(session, settings)
            ensure_default_digest_templates(session)
            session.commit()


def create_app(
    settings: Settings | None = None,
    connector_overrides: dict[str, Any] | None = None,
    publisher_overrides: dict[str, Any] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    state = AppState(
        resolved_settings,
        connector_overrides=connector_overrides,
        publisher_overrides=publisher_overrides,
    )
    app = FastAPI(title=resolved_settings.app_name)
    app.state.container = state
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bearer = HTTPBearer(auto_error=False)

    def get_db() -> Session:
        with session_scope(state.session_factory) as session:
            yield session

    def get_optional_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(get_db),
    ) -> User | None:
        if not resolved_settings.auth_enabled:
            return None
        if credentials is None:
            return None
        payload = decode_access_token(credentials.credentials, resolved_settings)
        if payload is None:
            return None
        subject = payload.get("sub")
        if subject is None:
            return None
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            return None
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user

    def get_current_user(current_user: User | None = Depends(get_optional_user)) -> User | None:
        if not resolved_settings.auth_enabled:
            return None
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        return current_user

    def require_role(required_role: str) -> Callable[[User | None], User | None]:
        def dependency(current_user: User | None = Depends(get_current_user)) -> User | None:
            if not resolved_settings.auth_enabled:
                return None
            if current_user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
            if not role_satisfies(current_user.role, required_role):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            return current_user

        return dependency

    viewer_access = require_role(UserRole.VIEWER)
    editor_access = require_role(UserRole.EDITOR)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": resolved_settings.app_name}

    @app.get("/auth/config", response_model=AuthConfigResponse)
    def auth_config() -> AuthConfigResponse:
        return AuthConfigResponse(auth_enabled=resolved_settings.auth_enabled)

    @app.post("/auth/login", response_model=AuthTokenResponse)
    def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
        if not resolved_settings.auth_enabled:
            raise HTTPException(status_code=400, detail="Authentication is disabled")
        user = authenticate_user(db, payload.username, payload.password)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        access_token, expires_at = create_access_token(user, resolved_settings)
        record_audit_log(
            db,
            actor=user,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            detail={"role": user.role},
        )
        db.commit()
        return AuthTokenResponse(
            access_token=access_token,
            expires_at=expires_at,
            user=_auth_user_to_response(user),
        )

    @app.get("/auth/me", response_model=AuthUserResponse)
    def auth_me(current_user: User | None = Depends(get_current_user)) -> AuthUserResponse:
        assert current_user is not None
        return _auth_user_to_response(current_user)

    @app.get("/dashboard/summary")
    def dashboard_summary(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> dict[str, int]:
        stories = db.scalar(select(func.count()).select_from(Story)) or 0
        articles = db.scalar(select(func.count()).select_from(ArticleDraft)) or 0
        jobs = db.scalar(select(func.count()).select_from(PublishJob)) or 0
        return {"stories": stories, "articles": articles, "publish_jobs": jobs}

    @app.get("/ops/summary", response_model=OpsSummaryResponse)
    def ops_summary(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> OpsSummaryResponse:
        return build_ops_summary(db)

    @app.get("/sources")
    def list_sources(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[dict[str, object]]:
        specs = annotate_source_specs(db, get_source_specs())
        return [spec.model_dump() for spec in specs]

    @app.get("/templates/digests", response_model=list[DigestTemplateResponse])
    def get_digest_templates(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[DigestTemplateResponse]:
        return list_digest_templates(db)

    @app.post("/ingest/run", response_model=IngestRunResponse)
    def run_ingestion(
        payload: IngestRunRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> IngestRunResponse:
        try:
            run = execute_ingest_run(
                db,
                source_slugs=payload.source_slugs,
                connector_registry=state.connector_registry,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        record_audit_log(
            db,
            actor=current_user,
            action="ingest.run",
            resource_type="ingest_run",
            resource_id=run.id,
            detail={"source_slugs": payload.source_slugs or []},
        )
        db.commit()
        return ingest_run_to_response(run)

    @app.get("/ingest/runs", response_model=list[IngestRunResponse])
    def list_ingest_runs(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[IngestRunResponse]:
        runs = db.scalars(select(IngestRun).order_by(IngestRun.id.desc())).all()
        return [ingest_run_to_response(run) for run in runs]

    @app.get("/ingest/runs/{run_id}", response_model=IngestRunResponse)
    def get_ingest_run(
        run_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> IngestRunResponse:
        run = db.get(IngestRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ingest run not found")
        return ingest_run_to_response(run)

    @app.get("/normalized-items", response_model=list[NormalizedItem])
    def list_normalized_items(
        limit: int = Query(default=50, ge=1, le=200),
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[NormalizedItem]:
        items = db.scalars(
            select(NormalizedItemRecord)
            .order_by(NormalizedItemRecord.published_at.desc(), NormalizedItemRecord.id.desc())
            .limit(limit)
        ).all()
        return [_normalized_item_to_response(item) for item in items]

    @app.post("/pipeline/stories/rebuild", response_model=PipelineRebuildResponse)
    def rebuild_story_pipeline(
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PipelineRebuildResponse:
        result = run_story_pipeline(db)
        record_audit_log(
            db,
            actor=current_user,
            action="pipeline.rebuild",
            resource_type="story_pipeline",
            detail=result,
        )
        db.commit()
        return PipelineRebuildResponse(**result)

    @app.post("/stories", response_model=StoryResponse, status_code=201)
    def create_story(
        payload: StoryCreatePayload,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> StoryResponse:
        story = Story(status=StoryStatus.PENDING, **payload.model_dump(exclude={"primary_section", "sections"}))
        db.add(story)
        db.flush()
        record_audit_log(
            db,
            actor=current_user,
            action="story.create",
            resource_type="story",
            resource_id=story.id,
            detail={"story_key": story.story_key},
        )
        db.commit()
        db.refresh(story)
        return StoryResponse(id=story.id, status=story.status, **payload.model_dump())

    @app.get("/stories", response_model=list[StoryResponse])
    def list_stories(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[StoryResponse]:
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
    def approve_story(
        story_id: int,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> dict[str, str | int]:
        story = db.get(Story, story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Story not found")
        story.status = StoryStatus.APPROVED
        record_audit_log(
            db,
            actor=current_user,
            action="story.approve",
            resource_type="story",
            resource_id=story.id,
            detail={"story_key": story.story_key},
        )
        db.commit()
        return {"id": story.id, "status": story.status}

    @app.post("/articles/generate", response_model=ArticleDraftResponse)
    def generate_article(
        payload: GenerateArticleRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        generator_map: dict[str, Callable[..., ArticleDraftResponse]] = {
            'daily': generate_and_persist_daily_digest,
            'weekly': generate_and_persist_weekly_digest,
            'monthly': generate_and_persist_monthly_digest,
        }
        generator = generator_map[payload.period_type]
        return _generate_article_digest(db, payload, generator, current_user)

    @app.post("/articles/generate/daily", response_model=ArticleDraftResponse)
    def generate_daily_article(
        payload: GenerateDailyArticleRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        return _generate_article_digest(db, payload, generate_and_persist_daily_digest, current_user)

    @app.post("/articles/generate/weekly", response_model=ArticleDraftResponse)
    def generate_weekly_article(
        payload: GenerateDailyArticleRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        return _generate_article_digest(db, payload, generate_and_persist_weekly_digest, current_user)

    @app.post("/articles/generate/monthly", response_model=ArticleDraftResponse)
    def generate_monthly_article(
        payload: GenerateDailyArticleRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        return _generate_article_digest(db, payload, generate_and_persist_monthly_digest, current_user)

    @app.get("/articles", response_model=list[ArticleDraftResponse])
    def list_article_drafts(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[ArticleDraftResponse]:
        return list_articles(db)

    @app.get("/articles/{article_id}", response_model=ArticleDraftResponse)
    def get_article(
        article_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> ArticleDraftResponse:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        variant_count = len(list_article_variants(db, article.id))
        sections = resolve_article_sections_for_story_ids(db, article.story_ids)
        return article_to_response(article, variant_count, sections=sections)

    @app.get("/articles/{article_id}/blocks", response_model=list[ArticleBlockResponse])
    def get_article_blocks(
        article_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[ArticleBlockResponse]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return list_article_blocks(db, article.id)

    @app.get("/articles/{article_id}/revisions", response_model=list[ArticleRevisionResponse])
    def get_article_revisions(
        article_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[ArticleRevisionResponse]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return list_article_revisions(db, article.id)

    @app.get("/articles/{article_id}/editorial-actions", response_model=list[EditorialActionResponse])
    def get_editorial_actions(
        article_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[EditorialActionResponse]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return list_editorial_actions(db, article.id)

    @app.post("/articles/{article_id}/revisions/{revision_id}/restore", response_model=ArticleDraftResponse)
    def restore_revision(
        article_id: int,
        revision_id: int,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        try:
            result = restore_article_revision(
                db,
                article_id=article_id,
                revision_id=revision_id,
                actor=current_user,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        record_audit_log(
            db,
            actor=current_user,
            action='article.revision.restore',
            resource_type='article_revision',
            resource_id=revision_id,
            detail={'article_id': article_id},
        )
        db.commit()
        return result

    @app.patch("/articles/{article_id}/blocks/{block_id}", response_model=ArticleBlockResponse)
    def patch_article_block(
        article_id: int,
        block_id: int,
        payload: ArticleBlockUpdateRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleBlockResponse:
        try:
            result = update_article_block(
                db,
                article_id=article_id,
                block_id=block_id,
                payload=payload,
                actor=current_user,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        record_audit_log(
            db,
            actor=current_user,
            action='article.block.update',
            resource_type='article_block',
            resource_id=block_id,
            detail=payload.model_dump(exclude_none=True),
        )
        db.commit()
        return result

    @app.post("/articles/{article_id}/rebuild", response_model=ArticleDraftResponse)
    def rebuild_article(
        article_id: int,
        payload: ArticleRebuildRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> ArticleDraftResponse:
        try:
            result = rebuild_article_draft(
                db,
                article_id=article_id,
                payload=payload,
                actor=current_user,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        record_audit_log(
            db,
            actor=current_user,
            action='article.rebuild',
            resource_type='article',
            resource_id=article_id,
            detail=payload.model_dump(exclude_none=True),
        )
        db.commit()
        return result

    @app.get("/articles/{article_id}/variants", response_model=list[PostVariantResponse])
    def get_article_variants(
        article_id: int,
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[PostVariantResponse]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return list_article_variants(db, article.id)

    @app.post("/articles/{article_id}/publish")
    def publish_article(
        article_id: int,
        payload: PublishRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> dict[str, list[PublishJobResponse]]:
        article = db.get(ArticleDraft, article_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        jobs = create_publish_jobs(db, article, payload.platforms, payload.scheduled_for)
        record_audit_log(
            db,
            actor=current_user,
            action="publish.schedule",
            resource_type="article",
            resource_id=article.id,
            detail={"platforms": payload.platforms, "scheduled_for": payload.scheduled_for.isoformat()},
        )
        db.commit()
        return {"jobs": jobs}

    @app.get("/publish-jobs", response_model=list[PublishJobResponse])
    def list_publish_jobs(
        db: Session = Depends(get_db),
        _current_user: User | None = Depends(viewer_access),
    ) -> list[PublishJobResponse]:
        jobs = db.scalars(select(PublishJob).order_by(PublishJob.id.asc())).all()
        return [publish_job_to_response(job) for job in jobs]

    @app.post("/publish-jobs/dispatch-due", response_model=PublishDispatchResponse)
    def dispatch_due_jobs(
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PublishDispatchResponse:
        result = dispatch_due_publish_jobs(db, state.publisher_registry)
        record_audit_log(
            db,
            actor=current_user,
            action="publish.dispatch_due",
            resource_type="publish_job",
            detail=result.model_dump(),
        )
        db.commit()
        return result

    @app.post("/publish-jobs/poll", response_model=PublishPollResponse)
    def poll_jobs(
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PublishPollResponse:
        result = poll_publish_jobs(db, state.publisher_registry)
        record_audit_log(
            db,
            actor=current_user,
            action="publish.poll",
            resource_type="publish_job",
            detail=result.model_dump(),
        )
        db.commit()
        return result

    @app.post("/publish-jobs/callback/{platform}", response_model=PublishJobResponse)
    def handle_job_callback(
        platform: str,
        payload: dict[str, object],
        callback_secret: str | None = Header(default=None, alias="X-FetchNews-Callback-Secret"),
        db: Session = Depends(get_db),
    ) -> PublishJobResponse:
        _validate_publish_callback_secret(callback_secret, resolved_settings)
        try:
            result = handle_publish_callback(
                db,
                platform=platform,
                payload=payload,
                publisher_registry=state.publisher_registry,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        db.commit()
        return result

    @app.post("/publish-jobs/{job_id}/result", response_model=PublishJobResponse)
    def write_job_result(
        job_id: int,
        payload: PublishJobResultRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PublishJobResponse:
        job = db.get(PublishJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Publish job not found")
        result = write_publish_job_result(
            db,
            job,
            status=payload.status,
            external_id=payload.external_id,
            error_message=payload.error_message,
        )
        record_audit_log(
            db,
            actor=current_user,
            action="publish.result",
            resource_type="publish_job",
            resource_id=job.id,
            detail=payload.model_dump(exclude_none=True),
        )
        db.commit()
        return result

    @app.post("/publish-jobs/{job_id}/feedback", response_model=PublishJobResponse)
    def write_job_feedback(
        job_id: int,
        payload: PublishJobFeedbackRequest,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PublishJobResponse:
        job = db.get(PublishJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Publish job not found")
        if all(
            value is None
            for value in [payload.impressions, payload.opens, payload.clicks, payload.interactions]
        ):
            raise HTTPException(status_code=400, detail="At least one performance metric is required")
        result = write_publish_job_feedback(
            db,
            job,
            impressions=payload.impressions,
            opens=payload.opens,
            clicks=payload.clicks,
            interactions=payload.interactions,
        )
        record_audit_log(
            db,
            actor=current_user,
            action="publish.feedback",
            resource_type="publish_job",
            resource_id=job.id,
            detail=payload.model_dump(exclude_none=True),
        )
        db.commit()
        return result

    @app.post("/publish-jobs/{job_id}/retry", response_model=PublishJobResponse)
    def retry_job(
        job_id: int,
        db: Session = Depends(get_db),
        current_user: User | None = Depends(editor_access),
    ) -> PublishJobResponse:
        job = db.get(PublishJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Publish job not found")
        result = retry_publish_job(db, job)
        record_audit_log(
            db,
            actor=current_user,
            action="publish.retry",
            resource_type="publish_job",
            resource_id=job.id,
            detail={"retries": job.retries},
        )
        db.commit()
        return result

    return app


def _generate_article_digest(
    db: Session,
    payload: GenerateDailyArticleRequest,
    generator: Callable[..., ArticleDraftResponse],
    current_user: User | None,
) -> ArticleDraftResponse:
    try:
        article = generator(
            db,
            target_date=payload.target_date,
            story_ids=payload.story_ids,
            generation_note=payload.generation_note,
            template_id=getattr(payload, 'template_id', None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor=current_user,
        action=f"article.generate.{article.period_type}",
        resource_type="article",
        resource_id=article.id,
        detail={
            "target_date": payload.target_date.isoformat(),
            "story_ids": payload.story_ids or [],
            "generation_note": payload.generation_note,
        },
    )
    db.commit()
    return article



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



def _auth_user_to_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _validate_publish_callback_secret(
    callback_secret: str | None,
    settings: Settings,
) -> None:
    if callback_secret is None or not secrets.compare_digest(callback_secret, settings.publish_callback_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid callback secret")


app = create_app()
