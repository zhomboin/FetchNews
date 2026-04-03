"""attach digest templates to article drafts

Revision ID: 20260403_0003
Revises: 20260403_0002
Create Date: 2026-04-03 23:55:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '20260403_0003'
down_revision = '20260403_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('article_drafts', sa.Column('template_id', sa.Integer(), nullable=True))
    op.create_index('ix_article_drafts_template_id', 'article_drafts', ['template_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_article_drafts_template_id', table_name='article_drafts')
    op.drop_column('article_drafts', 'template_id')