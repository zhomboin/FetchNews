from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleBlock, ArticleDraft, ArticleRevision, DigestTemplate, EditorialAction, PostVariant, User
from fetchnews.pipeline.article_service import (
    article_to_response,
    block_to_response,
    generate_and_persist_digest,
    list_article_blocks,
    list_article_variants,
    resolve_article_sections_for_story_ids,
)
from fetchnews.pipeline.editorial_templates import build_section_plan
from fetchnews.schemas import (
    ArticleBlockResponse,
    ArticleBlockUpdateRequest,
    ArticleDraftResponse,
    ArticleRebuildRequest,
    EditorialActionResponse,
    StoryCandidate,
)
from fetchnews.models import Story


def update_article_block(
    session: Session,
    *,
    article_id: int,
    block_id: int,
    payload: ArticleBlockUpdateRequest,
    actor: User | None = None,
) -> ArticleBlockResponse:
    article = session.get(ArticleDraft, article_id)
    if article is None or article.active_revision_id is None:
        raise ValueError('Article not found or has no active revision')

    block = session.get(ArticleBlock, block_id)
    if block is None or block.article_id != article_id or block.revision_id != article.active_revision_id:
        raise ValueError('Article block not found in the active revision')

    changed_fields: dict[str, object] = {}
    if payload.content is not None and payload.content != block.content:
        block.content = payload.content
        block.is_manual = True
        changed_fields['content'] = True
    if payload.title is not None and payload.title != block.title:
        block.title = payload.title
        block.is_manual = True
        changed_fields['title'] = True
    if payload.is_locked is not None and payload.is_locked != block.is_locked:
        block.is_locked = payload.is_locked
        changed_fields['is_locked'] = payload.is_locked
    if payload.sort_order is not None and payload.sort_order != block.sort_order:
        block.sort_order = payload.sort_order
        changed_fields['sort_order'] = payload.sort_order

    _sync_article_from_active_blocks(session, article)
    _record_editorial_action(
        session,
        article=article,
        revision_id=article.active_revision_id,
        actor=actor,
        action_type='edit_block',
        target_type='article_block',
        target_id=str(block.id),
        detail={'changed_fields': changed_fields},
    )
    session.flush()
    return block_to_response(block)



def rebuild_article_draft(
    session: Session,
    *,
    article_id: int,
    payload: ArticleRebuildRequest,
    actor: User | None = None,
) -> ArticleDraftResponse:
    article = session.get(ArticleDraft, article_id)
    if article is None or article.active_revision_id is None:
        raise ValueError('Article not found or has no active revision')

    previous_blocks = session.scalars(
        select(ArticleBlock)
        .where(ArticleBlock.article_id == article.id, ArticleBlock.revision_id == article.active_revision_id)
        .order_by(ArticleBlock.sort_order.asc(), ArticleBlock.id.asc())
    ).all()

    selected_section_keys = list(dict.fromkeys(payload.section_keys or []))
    selected_section_set = set(selected_section_keys)
    effective_template_id = payload.template_id if payload.template_id is not None else article.template_id
    preserved_blocks = {
        block.block_key: block
        for block in previous_blocks
        if _should_preserve_block(block, payload.mode, selected_section_set)
    }
    preserved_locked_blocks = sum(1 for block in previous_blocks if block.is_locked and payload.mode == 'mixed')

    generate_and_persist_digest(
        session,
        target_date=article.target_date,
        period_type=article.period_type,
        story_ids=article.story_ids,
        generation_note=article.generation_note,
        template_id=effective_template_id,
    )
    refreshed_article = session.get(ArticleDraft, article.id)
    assert refreshed_article is not None
    assert refreshed_article.active_revision_id is not None

    active_revision = session.get(ArticleRevision, refreshed_article.active_revision_id)
    assert active_revision is not None
    active_revision.change_type = 'rebuild'
    active_revision.change_note = payload.mode

    new_blocks = session.scalars(
        select(ArticleBlock)
        .where(ArticleBlock.article_id == article.id, ArticleBlock.revision_id == refreshed_article.active_revision_id)
        .order_by(ArticleBlock.sort_order.asc(), ArticleBlock.id.asc())
    ).all()

    for block in new_blocks:
        preserved = preserved_blocks.get(block.block_key)
        if preserved is None:
            continue
        block.content = preserved.content
        block.title = preserved.title
        block.is_locked = preserved.is_locked
        block.is_manual = preserved.is_manual
        block.payload = preserved.payload
        block.sort_order = preserved.sort_order

    _sync_article_from_active_blocks(session, refreshed_article)
    _record_editorial_action(
        session,
        article=refreshed_article,
        revision_id=refreshed_article.active_revision_id,
        actor=actor,
        action_type='rebuild_article',
        target_type='article',
        target_id=str(refreshed_article.id),
        detail={
            'mode': payload.mode,
            'preserved_locked_blocks': preserved_locked_blocks,
            'preserved_blocks': len(preserved_blocks),
            'template_id': effective_template_id,
            'section_keys': selected_section_keys,
        },
    )

    template = session.get(DigestTemplate, refreshed_article.template_id) if refreshed_article.template_id is not None else None
    sections = resolve_article_sections_for_story_ids(session, refreshed_article.story_ids)
    section_plan = _build_article_section_plan(session, refreshed_article, template)
    blocks = list_article_blocks(session, refreshed_article.id)
    variants = list_article_variants(session, refreshed_article.id)
    session.flush()
    session.refresh(refreshed_article)
    return article_to_response(
        refreshed_article,
        len(variants),
        sections=sections,
        template=template,
        active_revision_id=refreshed_article.active_revision_id,
        block_count=len(blocks),
        section_plan=section_plan,
        blocks=blocks,
    )



def restore_article_revision(
    session: Session,
    *,
    article_id: int,
    revision_id: int,
    actor: User | None = None,
) -> ArticleDraftResponse:
    article = session.get(ArticleDraft, article_id)
    if article is None:
        raise ValueError('Article not found')

    source_revision = session.get(ArticleRevision, revision_id)
    if source_revision is None or source_revision.article_id != article_id:
        raise ValueError('Revision not found for the requested article')

    snapshot = source_revision.snapshot or {}
    snapshot_blocks = snapshot.get('blocks') or []
    if not snapshot_blocks:
        raise ValueError('Revision snapshot does not contain restorable blocks')

    latest_revision = session.scalar(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.version_number.desc(), ArticleRevision.id.desc())
    )
    next_version_number = latest_revision.version_number + 1 if latest_revision is not None else 1

    restored_revision = ArticleRevision(
        article_id=article_id,
        version_number=next_version_number,
        change_type='restore',
        change_note=f'restored_from:{revision_id}',
        template_id=source_revision.template_id,
        snapshot=snapshot,
        created_by_user_id=actor.id if actor is not None else None,
    )
    session.add(restored_revision)
    session.flush()

    restored_blocks: list[ArticleBlock] = []
    for block_snapshot in snapshot_blocks:
        restored_blocks.append(
            ArticleBlock(
                article_id=article_id,
                revision_id=restored_revision.id,
                block_key=block_snapshot['block_key'],
                block_type=block_snapshot['block_type'],
                section_key=block_snapshot.get('section_key'),
                platform_scope=block_snapshot.get('platform_scope'),
                story_id=block_snapshot.get('story_id'),
                title=block_snapshot.get('title'),
                content=block_snapshot['content'],
                sort_order=block_snapshot.get('sort_order', 0),
                is_locked=bool(block_snapshot.get('is_locked', False)),
                is_manual=bool(block_snapshot.get('is_manual', False)),
                payload=block_snapshot.get('payload') or {},
            )
        )
    session.add_all(restored_blocks)

    article.template_id = snapshot.get('template_id')
    article.story_ids = snapshot.get('story_ids') or article.story_ids
    article.story_keys = snapshot.get('story_keys') or article.story_keys
    article.title = snapshot.get('title') or article.title
    article.summary = snapshot.get('summary') or article.summary
    article.body = snapshot.get('body') or article.body
    article.active_revision_id = restored_revision.id
    session.flush()
    _sync_article_from_active_blocks(session, article)

    _record_editorial_action(
        session,
        article=article,
        revision_id=restored_revision.id,
        actor=actor,
        action_type='restore_revision',
        target_type='article_revision',
        target_id=str(revision_id),
        detail={'source_revision_id': revision_id},
    )

    template = session.get(DigestTemplate, article.template_id) if article.template_id is not None else None
    sections = resolve_article_sections_for_story_ids(session, article.story_ids)
    section_plan = _build_article_section_plan(session, article, template)
    blocks = list_article_blocks(session, article.id)
    variants = list_article_variants(session, article.id)
    session.refresh(article)
    return article_to_response(
        article,
        len(variants),
        sections=sections,
        template=template,
        active_revision_id=article.active_revision_id,
        block_count=len(blocks),
        section_plan=section_plan,
        blocks=blocks,
    )


def list_editorial_actions(session: Session, article_id: int) -> list[EditorialActionResponse]:
    actions = session.scalars(
        select(EditorialAction)
        .where(EditorialAction.article_id == article_id)
        .order_by(EditorialAction.created_at.asc(), EditorialAction.id.asc())
    ).all()
    return [
        EditorialActionResponse(
            id=action.id,
            article_id=action.article_id,
            revision_id=action.revision_id,
            actor_user_id=action.actor_user_id,
            action_type=action.action_type,
            target_type=action.target_type,
            target_id=action.target_id,
            detail=action.detail,
            created_at=action.created_at,
        )
        for action in actions
    ]



def _should_preserve_block(block: ArticleBlock, rebuild_mode: str, selected_section_keys: set[str]) -> bool:
    if rebuild_mode != 'mixed':
        return False
    if block.is_locked:
        return True
    if not selected_section_keys:
        return False
    return block.section_key not in selected_section_keys



def _sync_article_from_active_blocks(session: Session, article: ArticleDraft) -> None:
    assert article.active_revision_id is not None
    blocks = session.scalars(
        select(ArticleBlock)
        .where(ArticleBlock.article_id == article.id, ArticleBlock.revision_id == article.active_revision_id)
        .order_by(ArticleBlock.sort_order.asc(), ArticleBlock.id.asc())
    ).all()
    article.title = _read_block_content(blocks, 'title', fallback=article.title)
    article.summary = _read_block_content(blocks, 'summary', fallback=article.summary)
    article.body = _compose_body_from_blocks(blocks)
    _sync_platform_variants_from_blocks(session, article.id, blocks)
    session.flush()



def _compose_body_from_blocks(blocks: list[ArticleBlock]) -> str:
    body_parts: list[str] = []
    intro = next((block.content for block in blocks if block.block_type == 'intro'), None)
    if intro:
        body_parts.append(intro)
    for block in blocks:
        if block.block_type != 'story_paragraph':
            continue
        title_line = f"{block.title}\n" if block.title else ''
        body_parts.append(f'{title_line}{block.content}'.strip())
    return '\n\n'.join(part for part in body_parts if part)



def _sync_platform_variants_from_blocks(session: Session, article_id: int, blocks: list[ArticleBlock]) -> None:
    platform_blocks = [block for block in blocks if block.block_type == 'platform_body' and block.platform_scope]
    existing_variants = {
        variant.platform: variant
        for variant in session.scalars(select(PostVariant).where(PostVariant.article_id == article_id)).all()
    }
    for block in platform_blocks:
        assert block.platform_scope is not None
        variant = existing_variants.get(block.platform_scope)
        if variant is None:
            session.add(PostVariant(article_id=article_id, platform=block.platform_scope, content=block.content))
            continue
        variant.content = block.content



def _read_block_content(blocks: list[ArticleBlock], block_type: str, *, fallback: str) -> str:
    block = next((item for item in blocks if item.block_type == block_type), None)
    if block is None:
        return fallback
    return block.content



def _build_article_section_plan(
    session: Session,
    article: ArticleDraft,
    template: DigestTemplate | None,
):
    stories = session.scalars(select(Story).where(Story.id.in_(article.story_ids))).all()
    candidates = [
        StoryCandidate(
            payload_story_id=story.id,
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
    return build_section_plan(candidates, template)



def _record_editorial_action(
    session: Session,
    *,
    article: ArticleDraft,
    revision_id: int | None,
    actor: User | None,
    action_type: str,
    target_type: str,
    target_id: str | None,
    detail: dict,
) -> None:
    session.add(
        EditorialAction(
            article_id=article.id,
            revision_id=revision_id,
            actor_user_id=actor.id if actor is not None else None,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
    session.flush()
