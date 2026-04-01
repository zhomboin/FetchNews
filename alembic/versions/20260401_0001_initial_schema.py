"""initial schema

Revision ID: 20260401_0001
Revises: 
Create Date: 2026-04-01 22:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_username", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_actor_username", "audit_logs", ["actor_username"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"], unique=False)
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"], unique=True)
    op.create_index("ix_sources_platform", "sources", ["platform"], unique=False)
    op.create_index("ix_sources_priority", "sources", ["priority"], unique=False)
    op.create_index("ix_sources_kind", "sources", ["kind"], unique=False)

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requested_source_slugs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("sources_total", sa.Integer(), nullable=False),
        sa.Column("sources_succeeded", sa.Integer(), nullable=False),
        sa.Column("sources_failed", sa.Integer(), nullable=False),
        sa.Column("items_ingested", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "raw_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("ingest_run_id", sa.Integer(), sa.ForeignKey("ingest_runs.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("first_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_items_source_external_id"),
    )
    op.create_index("ix_raw_items_source_id", "raw_items", ["source_id"], unique=False)
    op.create_index("ix_raw_items_ingest_run_id", "raw_items", ["ingest_run_id"], unique=False)

    op.create_table(
        "normalized_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("raw_item_id", sa.Integer(), sa.ForeignKey("raw_items.id"), nullable=False),
        sa.Column("source_slug", sa.String(length=120), nullable=False),
        sa.Column("source_priority", sa.String(length=10), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("normalized_title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("raw_item_id", name="uq_normalized_items_raw_item_id"),
    )
    op.create_index("ix_normalized_items_raw_item_id", "normalized_items", ["raw_item_id"], unique=False)
    op.create_index("ix_normalized_items_source_slug", "normalized_items", ["source_slug"], unique=False)
    op.create_index("ix_normalized_items_source_priority", "normalized_items", ["source_priority"], unique=False)
    op.create_index("ix_normalized_items_canonical_url", "normalized_items", ["canonical_url"], unique=False)
    op.create_index("ix_normalized_items_normalized_title", "normalized_items", ["normalized_title"], unique=False)
    op.create_index("ix_normalized_items_published_at", "normalized_items", ["published_at"], unique=False)

    op.create_table(
        "stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("story_key", sa.String(length=120), nullable=False),
        sa.Column("cluster_title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("highlights", sa.JSON(), nullable=False),
        sa.Column("source_links", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stories_story_key", "stories", ["story_key"], unique=True)

    op.create_table(
        "article_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("story_ids", sa.JSON(), nullable=False),
        sa.Column("story_keys", sa.JSON(), nullable=False),
        sa.Column("generation_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("period_type", "target_date", name="uq_article_drafts_period_target_date"),
    )
    op.create_index("ix_article_drafts_period_type", "article_drafts", ["period_type"], unique=False)
    op.create_index("ix_article_drafts_target_date", "article_drafts", ["target_date"], unique=False)

    op.create_table(
        "post_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("article_drafts.id"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("article_id", "platform", name="uq_post_variants_article_platform"),
    )
    op.create_index("ix_post_variants_article_id", "post_variants", ["article_id"], unique=False)
    op.create_index("ix_post_variants_platform", "post_variants", ["platform"], unique=False)

    op.create_table(
        "publish_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provider_job_id", sa.String(length=160), nullable=True),
        sa.Column("provider_payload", sa.JSON(), nullable=False),
        sa.Column("performance_metrics", sa.JSON(), nullable=False),
        sa.Column("metrics_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publish_jobs_article_id", "publish_jobs", ["article_id"], unique=False)
    op.create_index("ix_publish_jobs_platform", "publish_jobs", ["platform"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_platform", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_article_id", table_name="publish_jobs")
    op.drop_table("publish_jobs")

    op.drop_index("ix_post_variants_platform", table_name="post_variants")
    op.drop_index("ix_post_variants_article_id", table_name="post_variants")
    op.drop_table("post_variants")

    op.drop_index("ix_article_drafts_target_date", table_name="article_drafts")
    op.drop_index("ix_article_drafts_period_type", table_name="article_drafts")
    op.drop_table("article_drafts")

    op.drop_index("ix_stories_story_key", table_name="stories")
    op.drop_table("stories")

    op.drop_index("ix_normalized_items_published_at", table_name="normalized_items")
    op.drop_index("ix_normalized_items_normalized_title", table_name="normalized_items")
    op.drop_index("ix_normalized_items_canonical_url", table_name="normalized_items")
    op.drop_index("ix_normalized_items_source_priority", table_name="normalized_items")
    op.drop_index("ix_normalized_items_source_slug", table_name="normalized_items")
    op.drop_index("ix_normalized_items_raw_item_id", table_name="normalized_items")
    op.drop_table("normalized_items")

    op.drop_index("ix_raw_items_ingest_run_id", table_name="raw_items")
    op.drop_index("ix_raw_items_source_id", table_name="raw_items")
    op.drop_table("raw_items")

    op.drop_table("ingest_runs")

    op.drop_index("ix_sources_kind", table_name="sources")
    op.drop_index("ix_sources_priority", table_name="sources")
    op.drop_index("ix_sources_platform", table_name="sources")
    op.drop_index("ix_sources_slug", table_name="sources")
    op.drop_table("sources")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_username", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
