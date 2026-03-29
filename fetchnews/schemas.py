from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceSpec(BaseModel):
    slug: str
    label: str
    platform: str
    priority: str
    kind: str
    enabled: bool = True
    config: dict = Field(default_factory=dict)


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


class ArticleDraftPayload(BaseModel):
    id: int | None = None
    target_date: date
    title: str
    summary: str
    body: str
    story_keys: list[str]


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


class StoryResponse(StoryCreatePayload):
    id: int
    status: str


class GenerateDailyArticleRequest(BaseModel):
    target_date: date
    story_ids: list[int] | None = None
    generation_note: str | None = None


class ArticleDraftResponse(ArticleDraftPayload):
    id: int
    status: str
    story_ids: list[int] = Field(default_factory=list)
    generation_note: str | None = None
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
    updated_at: datetime


class PublishDispatchResponse(BaseModel):
    jobs_dispatched: int
    jobs_failed: int = 0


class PublishPollResponse(BaseModel):
    jobs_polled: int
    jobs_completed: int
    jobs_failed: int = 0