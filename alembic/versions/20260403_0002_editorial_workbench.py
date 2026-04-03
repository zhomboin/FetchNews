"""editorial workbench schema

Revision ID: 20260403_0002
Revises: 20260401_0001
Create Date: 2026-04-03 23:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260403_0002'
down_revision = '20260401_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'digest_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('section_quotas', sa.JSON(), nullable=False),
        sa.Column('section_order', sa.JSON(), nullable=False),
        sa.Column('default_platform_templates', sa.JSON(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('period_type', 'name', name='uq_digest_templates_period_name'),
    )
    op.create_index('ix_digest_templates_period_type', 'digest_templates', ['period_type'], unique=False)

    op.create_table(
        'article_revisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('article_drafts.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(length=30), nullable=False),
        sa.Column('change_note', sa.Text(), nullable=True),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('digest_templates.id'), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('article_id', 'version_number', name='uq_article_revisions_article_version'),
    )
    op.create_index('ix_article_revisions_article_id', 'article_revisions', ['article_id'], unique=False)

    op.add_column('article_drafts', sa.Column('active_revision_id', sa.Integer(), nullable=True))
    op.create_index('ix_article_drafts_active_revision_id', 'article_drafts', ['active_revision_id'], unique=False)

    op.create_table(
        'article_blocks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('article_drafts.id'), nullable=False),
        sa.Column('revision_id', sa.Integer(), sa.ForeignKey('article_revisions.id'), nullable=False),
        sa.Column('block_key', sa.String(length=120), nullable=False),
        sa.Column('block_type', sa.String(length=40), nullable=False),
        sa.Column('section_key', sa.String(length=40), nullable=True),
        sa.Column('platform_scope', sa.String(length=40), nullable=True),
        sa.Column('story_id', sa.Integer(), sa.ForeignKey('stories.id'), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_manual', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('revision_id', 'block_key', name='uq_article_blocks_revision_block_key'),
    )
    op.create_index('ix_article_blocks_article_id', 'article_blocks', ['article_id'], unique=False)
    op.create_index('ix_article_blocks_revision_id', 'article_blocks', ['revision_id'], unique=False)
    op.create_index('ix_article_blocks_block_type', 'article_blocks', ['block_type'], unique=False)
    op.create_index('ix_article_blocks_section_key', 'article_blocks', ['section_key'], unique=False)
    op.create_index('ix_article_blocks_platform_scope', 'article_blocks', ['platform_scope'], unique=False)
    op.create_index('ix_article_blocks_story_id', 'article_blocks', ['story_id'], unique=False)

    op.create_table(
        'editorial_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('article_drafts.id'), nullable=False),
        sa.Column('revision_id', sa.Integer(), sa.ForeignKey('article_revisions.id'), nullable=True),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=120), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_editorial_actions_article_id', 'editorial_actions', ['article_id'], unique=False)
    op.create_index('ix_editorial_actions_revision_id', 'editorial_actions', ['revision_id'], unique=False)
    op.create_index('ix_editorial_actions_actor_user_id', 'editorial_actions', ['actor_user_id'], unique=False)
    op.create_index('ix_editorial_actions_action_type', 'editorial_actions', ['action_type'], unique=False)
    op.create_index('ix_editorial_actions_target_type', 'editorial_actions', ['target_type'], unique=False)
    op.create_index('ix_editorial_actions_target_id', 'editorial_actions', ['target_id'], unique=False)
    op.create_index('ix_editorial_actions_created_at', 'editorial_actions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_editorial_actions_created_at', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_target_id', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_target_type', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_action_type', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_actor_user_id', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_revision_id', table_name='editorial_actions')
    op.drop_index('ix_editorial_actions_article_id', table_name='editorial_actions')
    op.drop_table('editorial_actions')

    op.drop_index('ix_article_blocks_story_id', table_name='article_blocks')
    op.drop_index('ix_article_blocks_platform_scope', table_name='article_blocks')
    op.drop_index('ix_article_blocks_section_key', table_name='article_blocks')
    op.drop_index('ix_article_blocks_block_type', table_name='article_blocks')
    op.drop_index('ix_article_blocks_revision_id', table_name='article_blocks')
    op.drop_index('ix_article_blocks_article_id', table_name='article_blocks')
    op.drop_table('article_blocks')

    op.drop_index('ix_article_drafts_active_revision_id', table_name='article_drafts')
    op.drop_column('article_drafts', 'active_revision_id')

    op.drop_index('ix_article_revisions_article_id', table_name='article_revisions')
    op.drop_table('article_revisions')

    op.drop_index('ix_digest_templates_period_type', table_name='digest_templates')
    op.drop_table('digest_templates')