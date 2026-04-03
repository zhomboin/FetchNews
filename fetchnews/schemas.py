from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from fetchnews.pipeline.sections import infer_sections_from_signals


class SourceSpec(BaseModel):
    slug: str
    label: str
    platform: str
    priority: str
    kind: str
    enabled: bool = True
    config: dict = Field(default_factory=dict)
    effective_trust_score: float | None = None
    effective_score_multiplier: float | None = None
    feedback_signals: dict = Field(default_factory=dict)
    governance_flags: list[str] = Field(default_factory=list)


class AuthConfigResponse(BaseModel):
    auth_enabled: bool


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: AuthUserResponse


class RawIngestedItem(BaseModel):
    source_slug: str
    external_id: str
    title: str
    url: str
    author: str | None = None
    published_at: datetime
    content: str
    metadata: dict = Field(default_factory=dict)


class NormalizedItem(BaseModel):
    raw_item_id: int | None = None
    source_slug: str
    source_priority: str = "P2"
    external_id: str
    canonical_url: str
    title: str
    normalized_title: str
    author: str | None = None
    published_at: datetime
    summary: str
    content: str
    language: str = "unknown"
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class StoryCandidate(BaseModel):
    payload_story_id: int | None = None
    story_key: str
    cluster_title: str
    summary: str
    highlights: list[str]
    source_links: list[str]
    tags: list[str]
    risk_flags: list[str]
    score: float
    item_count: int
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    primary_section: str = "community"
    sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_sections(self) -> "StoryCandidate":
        primary_section, sections = infer_sections_from_signals(
            title=self.cluster_title,
            summary=self.summary,
            tags=self.tags,
            source_hints=self.source_links,
        )
        if not self.sections:
            self.sections = sections
        else:
            self.sections = list(dict.fromkeys(self.sections))
        if not self.primary_section or self.primary_section == "community":
            self.primary_section = primary_section
        if self.primary_section not in self.sections:
            self.sections.insert(0, self.primary_section)
        return self


class ArticleDraftPayload(BaseModel):
    id: int | None = None
    period_type: str = "daily"
    target_date: date
    title: str
    summary: str
    body: str
    story_keys: list[str]
    sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_sections(self) -> "ArticleDraftPayload":
        self.sections = list(dict.fromkeys(self.sections))
        return self


class DailyDigest(BaseModel):
    article: ArticleDraftPayload
    posts: dict[str, str]


class StoryCreatePayload(BaseModel):
    story_key: str
    cluster_title: str
    summary: str
    highlights: list[str]
    source_links: list[str]
    tags: list[str]
    risk_flags: list[str]
    score: float
    item_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    primary_section: str = "community"
    sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_sections(self) -> "StoryCreatePayload":
        primary_section, sections = infer_sections_from_signals(
            title=self.cluster_title,
            summary=self.summary,
            tags=self.tags,
            source_hints=self.source_links,
        )
        if not self.sections:
            self.sections = sections
        else:
            self.sections = list(dict.fromkeys(self.sections))
        if not self.primary_section or self.primary_section == "community":
            self.primary_section = primary_section
        if self.primary_section not in self.sections:
            self.sections.insert(0, self.primary_section)
        return self


class StoryResponse(StoryCreatePayload):
    id: int
    status: str


class GenerateDailyArticleRequest(BaseModel):
    target_date: date
    story_ids: list[int] | None = None
    generation_note: str | None = None
    template_id: int | None = None


class GenerateArticleRequest(GenerateDailyArticleRequest):
    period_type: Literal['daily', 'weekly', 'monthly'] = 'daily'


class ArticleSectionPlanResponse(BaseModel):
    section_key: str
    section_label: str
    target_ratio: float | None = None
    story_count: int = 0
    story_ids: list[int] = Field(default_factory=list)


class ArticleDraftResponse(ArticleDraftPayload):
    id: int
    status: str
    story_ids: list[int] = Field(default_factory=list)
    generation_note: str | None = None
    template_id: int | None = None
    template_name: str | None = None
    active_revision_id: int | None = None
    block_count: int = 0
    section_plan: list[ArticleSectionPlanResponse] = Field(default_factory=list)
    blocks: list[ArticleBlockResponse] = Field(default_factory=list)
    story_count: int
    variant_count: int
    created_at: datetime
    updated_at: datetime


class PostVariantResponse(BaseModel):
    id: int
    article_id: int
    platform: str
    content: str
    updated_at: datetime


class ArticleBlockResponse(BaseModel):
    id: int
    article_id: int
    revision_id: int
    block_key: str
    block_type: str
    section_key: str | None = None
    platform_scope: str | None = None
    story_id: int | None = None
    title: str | None = None
    content: str
    sort_order: int
    is_locked: bool
    is_manual: bool
    payload: dict = Field(default_factory=dict)
    updated_at: datetime


class ArticleRevisionResponse(BaseModel):
    id: int
    article_id: int
    version_number: int
    change_type: str
    change_note: str | None = None
    template_id: int | None = None
    snapshot: dict = Field(default_factory=dict)
    created_by_user_id: int | None = None
    created_at: datetime


class DigestTemplateResponse(BaseModel):
    id: int
    name: str
    period_type: str
    description: str | None = None
    section_quotas: dict = Field(default_factory=dict)
    section_order: list[str] = Field(default_factory=list)
    default_platform_templates: dict = Field(default_factory=dict)
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ArticleBlockUpdateRequest(BaseModel):
    content: str | None = None
    title: str | None = None
    is_locked: bool | None = None
    sort_order: int | None = None


class ArticleRebuildRequest(BaseModel):
    mode: Literal['mixed', 'force_full'] = 'mixed'
    template_id: int | None = None
    section_keys: list[str] | None = None


class EditorialActionResponse(BaseModel):
    id: int
    article_id: int
    revision_id: int | None = None
    actor_user_id: int | None = None
    action_type: str
    target_type: str
    target_id: str | None = None
    detail: dict = Field(default_factory=dict)
    created_at: datetime


class IngestRunRequest(BaseModel):
    source_slugs: list[str] | None = None


class IngestRunError(BaseModel):
    source_slug: str
    message: str


class IngestRunResponse(BaseModel):
    id: int
    source_slugs: list[str]
    status: str
    sources_total: int
    sources_succeeded: int
    sources_failed: int
    items_ingested: int
    errors: list[IngestRunError] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None


class PipelineRebuildResponse(BaseModel):
    normalized_items: int
    stories: int


class PublishRequest(BaseModel):
    platforms: list[str]
    scheduled_for: datetime


class PublishJobResultRequest(BaseModel):
    status: Literal["published", "failed"]
    external_id: str | None = None
    error_message: str | None = None


class PublishJobFeedbackRequest(BaseModel):
    impressions: int | None = Field(default=None, ge=0)
    opens: int | None = Field(default=None, ge=0)
    clicks: int | None = Field(default=None, ge=0)
    interactions: int | None = Field(default=None, ge=0)


class PublishJobResponse(BaseModel):
    id: int
    article_id: int
    platform: str
    scheduled_for: datetime
    status: str
    retries: int
    external_id: str | None = None
    error_message: str | None = None
    provider_job_id: str | None = None
    performance_metrics: dict[str, int] = Field(default_factory=dict)
    metrics_recorded_at: datetime | None = None
    updated_at: datetime


class PublishDispatchResponse(BaseModel):
    jobs_dispatched: int
    jobs_failed: int = 0


class PublishPollResponse(BaseModel):
    jobs_polled: int
    jobs_completed: int
    jobs_failed: int = 0


class FailureGroupResponse(BaseModel):
    category: str
    reason: str
    count: int
    targets: list[str] = Field(default_factory=list)
    suggestion: str


class AlertRecordResponse(BaseModel):
    severity: Literal["critical", "warning", "info"]
    category: str
    title: str
    summary: str
    target: str | None = None
    suggestion: str
    count: int = 0


class PublishPlatformMetricResponse(BaseModel):
    platform: str
    total_jobs: int
    scheduled_jobs: int
    published_jobs: int
    failed_jobs: int
    success_rate: float
    engagement_impressions: int = 0
    engagement_opens: int = 0
    engagement_clicks: int = 0
    engagement_interactions: int = 0
    click_through_rate: float = 0.0
    interaction_rate: float = 0.0
    last_error: str | None = None


class SectionReviewMetricResponse(BaseModel):
    section: str
    label: str
    total_stories: int
    approved_stories: int
    pending_stories: int
    flagged_stories: int
    engagement_impressions: int = 0
    engagement_opens: int = 0
    engagement_clicks: int = 0
    engagement_interactions: int = 0
    click_through_rate: float = 0.0
    interaction_rate: float = 0.0
    momentum_tier: str = "steady"


class FeedbackRecommendationResponse(BaseModel):
    category: str
    target: str
    title: str
    summary: str
    suggestion: str
    signal_count: int = 0


class OpsSummaryResponse(BaseModel):
    ingest_runs_total: int
    ingest_runs_failed: int
    items_ingested_total: int
    stories_total: int
    stories_approved: int
    stories_pending: int
    articles_total: int
    articles_ready: int
    articles_published: int
    articles_failed: int
    publish_jobs_total: int
    publish_jobs_scheduled: int
    publish_jobs_published: int
    publish_jobs_failed: int
    publish_success_rate: float
    due_publish_jobs: int
    engagement_impressions_total: int = 0
    engagement_opens_total: int = 0
    engagement_clicks_total: int = 0
    engagement_interactions_total: int = 0
    alerts: list[AlertRecordResponse] = Field(default_factory=list)
    recent_failure_groups: list[FailureGroupResponse] = Field(default_factory=list)
    publish_platform_metrics: list[PublishPlatformMetricResponse] = Field(default_factory=list)
    section_review_metrics: list[SectionReviewMetricResponse] = Field(default_factory=list)
    feedback_recommendations: list[FeedbackRecommendationResponse] = Field(default_factory=list)
