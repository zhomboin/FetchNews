"""add phase 07 publish and source contract fields

Revision ID: 20260404_0004
Revises: 20260403_0003
Create Date: 2026-04-04 10:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20260404_0004'
down_revision = '20260403_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sources', sa.Column('incremental_cursor', sa.String(length=255), nullable=True))
    op.add_column('sources', sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('publish_jobs', sa.Column('dispatch_key', sa.String(length=160), nullable=True))
    op.add_column('publish_jobs', sa.Column('failure_category', sa.String(length=60), nullable=True))
    op.add_column('publish_jobs', sa.Column('last_provider_status', sa.String(length=80), nullable=True))
    op.create_index('ix_publish_jobs_dispatch_key', 'publish_jobs', ['dispatch_key'], unique=False)
    op.create_index('ix_publish_jobs_failure_category', 'publish_jobs', ['failure_category'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_publish_jobs_failure_category', table_name='publish_jobs')
    op.drop_index('ix_publish_jobs_dispatch_key', table_name='publish_jobs')
    op.drop_column('publish_jobs', 'last_provider_status')
    op.drop_column('publish_jobs', 'failure_category')
    op.drop_column('publish_jobs', 'dispatch_key')
    op.drop_column('sources', 'last_success_at')
    op.drop_column('sources', 'incremental_cursor')
