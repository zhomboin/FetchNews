from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fetchnews.db.base import Base


class StoryStatus(StrEnum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class ArticleStatus(StrEnum):
    DRAFT = 'draft'
    READY = 'ready'
    SCHEDULED = 'scheduled'
    PUBLISHED = 'published'
    PARTIALLY_PUBLISHED = 'partially_published'
    FAILED = 'failed'


class PublishJobStatus(StrEnum):
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    PUBLISHED = 'published'
    FAILED = 'failed'


class IngestRunStatus(StrEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    COMPLETED_WITH_ERRORS = 'completed_with_errors'
    FAILED = 'failed'


class UserRole(StrEnum):
    ADMIN = 'admin'
    EDITOR = 'editor'
    VIEWER = 'viewer'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.EDITOR, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    actor_username: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)


class Source(Base):
    __tablename__ = 'sources'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(50), index=True)
    priority: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    incremental_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class IngestRun(Base):
    __tablename__ = 'ingest_runs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_source_slugs: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default=IngestRunStatus.PENDING)
    sources_total: Mapped[int] = mapped_column(Integer, default=0)
    sources_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    sources_failed: Mapped[int] = mapped_column(Integer, default=0)
    items_ingested: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RawItem(Base):
    __tablename__ = 'raw_items'
    __table_args__ = (UniqueConstraint('source_id', 'external_id', name='uq_raw_items_source_external_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    ingest_run_id: Mapped[int] = mapped_column(ForeignKey('ingest_runs.id'), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    first_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class NormalizedItemRecord(Base):
    __tablename__ = 'normalized_items'
    __table_args__ = (UniqueConstraint('raw_item_id', name='uq_normalized_items_raw_item_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_item_id: Mapped[int] = mapped_column(ForeignKey('raw_items.id'), index=True)
    source_slug: Mapped[str] = mapped_column(String(120), index=True)
    source_priority: Mapped[str] = mapped_column(String(10), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    canonical_url: Mapped[str] = mapped_column(String(1000), index=True)
    title: Mapped[str] = mapped_column(String(500))
    normalized_title: Mapped[str] = mapped_column(String(500), index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    summary: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default='unknown')
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Story(Base):
    __tablename__ = 'stories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    cluster_title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    highlights: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float)
    item_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=StoryStatus.PENDING)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DigestTemplate(Base):
    __tablename__ = 'digest_templates'
    __table_args__ = (UniqueConstraint('period_type', 'name', name='uq_digest_templates_period_name'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    period_type: Mapped[str] = mapped_column(String(20), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_quotas: Mapped[dict] = mapped_column(JSON, default=dict)
    section_order: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_platform_templates: Mapped[dict] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ArticleDraft(Base):
    __tablename__ = 'article_drafts'
    __table_args__ = (UniqueConstraint('period_type', 'target_date', name='uq_article_drafts_period_target_date'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_type: Mapped[str] = mapped_column(String(20), default='daily', index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ArticleStatus.DRAFT)
    story_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    story_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    generation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    active_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ArticleRevision(Base):
    __tablename__ = 'article_revisions'
    __table_args__ = (UniqueConstraint('article_id', 'version_number', name='uq_article_revisions_article_version'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('article_drafts.id'), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(30))
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey('digest_templates.id'), nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ArticleBlock(Base):
    __tablename__ = 'article_blocks'
    __table_args__ = (UniqueConstraint('revision_id', 'block_key', name='uq_article_blocks_revision_block_key'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('article_drafts.id'), index=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey('article_revisions.id'), index=True)
    block_key: Mapped[str] = mapped_column(String(120))
    block_type: Mapped[str] = mapped_column(String(40), index=True)
    section_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    platform_scope: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    story_id: Mapped[int | None] = mapped_column(ForeignKey('stories.id'), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class EditorialAction(Base):
    __tablename__ = 'editorial_actions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('article_drafts.id'), index=True)
    revision_id: Mapped[int | None] = mapped_column(ForeignKey('article_revisions.id'), nullable=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)


class PostVariant(Base):
    __tablename__ = 'post_variants'
    __table_args__ = (UniqueConstraint('article_id', 'platform', name='uq_post_variants_article_platform'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('article_drafts.id'), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PublishJob(Base):
    __tablename__ = 'publish_jobs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(Integer, index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=PublishJobStatus.SCHEDULED)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_job_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dispatch_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    failure_category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    last_provider_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    performance_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )