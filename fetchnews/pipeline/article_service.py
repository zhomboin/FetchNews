from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleBlock, ArticleDraft, ArticleRevision, ArticleStatus, DigestTemplate, PostVariant, Story, StoryStatus
from fetchnews.pipeline.editorial_templates import build_section_plan, order_stories_by_template, resolve_digest_template
from fetchnews.pipeline.engagement import build_section_engagement_snapshots, resolve_story_primary_section
from fetchnews.pipeline.generation import generate_digest, group_stories_by_section, resolve_article_sections
from fetchnews.pipeline.platform_copy import build_platform_copy_profiles
from fetchnews.schemas import (
    ArticleBlockResponse,
    ArticleDraftResponse,
    ArticleRevisionResponse,
    PostVariantResponse,
    StoryCandidate,
)


def generate_and_persist_daily_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
    template_id: int | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type='daily',
        story_ids=story_ids,
        generation_note=generation_note,
        template_id=template_id,
    )


def generate_and_persist_weekly_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
    template_id: int | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type='weekly',
        story_ids=story_ids,
        generation_note=generation_note,
        template_id=template_id,
    )


def generate_and_persist_monthly_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
    template_id: int | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type='monthly',
        story_ids=story_ids,
        generation_note=generation_note,
        template_id=template_id,
    )


def generate_and_persist_digest(
    session: Session,
    target_date: date,
    period_type: str,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
    template_id: int | None = None,
) -> ArticleDraftResponse:
    template = resolve_digest_template(session, period_type=period_type, template_id=template_id)
    section_engagement = build_section_engagement_snapshots(session)
    approved_stories = _load_approved_stories(
        session,
        story_ids,
        period_type=period_type,
        section_engagement=section_engagement,
    )
    story_candidates = [
        _story_to_candidate(story, score_override=_ranking_score_for_story(story, section_engagement))
        for story in approved_stories
    ]
    ordered_story_candidates = order_stories_by_template(story_candidates, template)
    approved_stories = _order_story_models_by_candidates(approved_stories, ordered_story_candidates)

    platform_profiles = build_platform_copy_profiles(session)
    digest = generate_digest(
        target_date=target_date,
        period_type=period_type,
        stories=ordered_story_candidates,
        generation_note=generation_note,
        platform_profiles=platform_profiles,
    )
    section_plan = build_section_plan(ordered_story_candidates, template)

    normalized_note = generation_note.strip() if generation_note and generation_note.strip() else None
    selected_story_ids = [story.id for story in approved_stories]

    article = session.scalar(
        select(ArticleDraft).where(
            ArticleDraft.period_type == period_type,
            ArticleDraft.target_date == target_date,
        )
    )
    resolved_template_id = template.id if template is not None else None
    if article is None:
        article = ArticleDraft(
            period_type=period_type,
            target_date=target_date,
            title=digest.article.title,
            summary=digest.article.summary,
            body=digest.article.body,
            story_ids=selected_story_ids,
            story_keys=digest.article.story_keys,
            generation_note=normalized_note,
            template_id=resolved_template_id,
            status=ArticleStatus.READY,
        )
        session.add(article)
        session.flush()
    else:
        article.period_type = period_type
        article.title = digest.article.title
        article.summary = digest.article.summary
        article.body = digest.article.body
        article.story_ids = selected_story_ids
        article.story_keys = digest.article.story_keys
        article.generation_note = normalized_note
        article.template_id = resolved_template_id
        article.status = ArticleStatus.READY
        session.flush()

    _upsert_post_variants(session, article.id, digest.posts)
    active_revision_id, block_count = _create_active_revision(
        session,
        article=article,
        approved_stories=approved_stories,
        sections=digest.article.sections,
        posts=digest.posts,
        template=template,
    )
    session.flush()
    session.refresh(article)
    variants = list_article_variants(session, article.id)
    blocks = list_article_blocks(session, article.id, revision_id=active_revision_id)
    return article_to_response(
        article,
        len(variants),
        sections=digest.article.sections,
        template=template,
        active_revision_id=active_revision_id,
        block_count=block_count,
        section_plan=section_plan,
        blocks=blocks,
    )


def list_articles(session: Session) -> list[ArticleDraftResponse]:
    articles = session.scalars(select(ArticleDraft).order_by(ArticleDraft.target_date.desc(), ArticleDraft.id.desc())).all()
    variant_counts = _variant_count_by_article(session)
    article_sections = _build_article_sections_lookup(session, articles)
    revision_stats = _build_article_revision_stats_lookup(session, articles)
    template_lookup = _build_template_lookup(session, articles)
    return [
        article_to_response(
            article,
            variant_counts.get(article.id, 0),
            sections=article_sections.get(article.id, []),
            template=template_lookup.get(article.template_id),
            active_revision_id=revision_stats.get(article.id, {}).get('active_revision_id'),
            block_count=revision_stats.get(article.id, {}).get('block_count', 0),
        )
        for article in articles
    ]


def list_article_variants(session: Session, article_id: int) -> list[PostVariantResponse]:
    variants = session.scalars(
        select(PostVariant).where(PostVariant.article_id == article_id).order_by(PostVariant.platform.asc())
    ).all()
    return [variant_to_response(variant) for variant in variants]


def list_article_blocks(
    session: Session,
    article_id: int,
    *,
    revision_id: int | None = None,
) -> list[ArticleBlockResponse]:
    resolved_revision_id = revision_id
    if resolved_revision_id is None:
        article = session.get(ArticleDraft, article_id)
        if article is None or article.active_revision_id is None:
            return []
        resolved_revision_id = article.active_revision_id

    blocks = session.scalars(
        select(ArticleBlock)
        .where(ArticleBlock.article_id == article_id, ArticleBlock.revision_id == resolved_revision_id)
        .order_by(ArticleBlock.sort_order.asc(), ArticleBlock.id.asc())
    ).all()
    return [block_to_response(block) for block in blocks]


def list_article_revisions(session: Session, article_id: int) -> list[ArticleRevisionResponse]:
    revisions = session.scalars(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.version_number.asc(), ArticleRevision.id.asc())
    ).all()
    return [revision_to_response(revision) for revision in revisions]


def article_to_response(
    article: ArticleDraft,
    variant_count: int,
    *,
    sections: list[str] | None = None,
    template: DigestTemplate | None = None,
    active_revision_id: int | None = None,
    block_count: int = 0,
    section_plan: list | None = None,
    blocks: list[ArticleBlockResponse] | None = None,
) -> ArticleDraftResponse:
    return ArticleDraftResponse(
        id=article.id,
        period_type=article.period_type,
        target_date=article.target_date,
        title=article.title,
        summary=article.summary,
        body=article.body,
        story_ids=article.story_ids,
        story_keys=article.story_keys,
        generation_note=article.generation_note,
        template_id=template.id if template is not None else article.template_id,
        template_name=template.name if template is not None else None,
        active_revision_id=active_revision_id if active_revision_id is not None else article.active_revision_id,
        block_count=block_count,
        section_plan=section_plan or [],
        blocks=blocks or [],
        status=article.status,
        story_count=len(article.story_ids),
        variant_count=variant_count,
        created_at=article.created_at,
        updated_at=article.updated_at,
        sections=sections or [],
    )


def variant_to_response(variant: PostVariant) -> PostVariantResponse:
    return PostVariantResponse(
        id=variant.id,
        article_id=variant.article_id,
        platform=variant.platform,
        content=variant.content,
        updated_at=variant.updated_at,
    )


def block_to_response(block: ArticleBlock) -> ArticleBlockResponse:
    return ArticleBlockResponse(
        id=block.id,
        article_id=block.article_id,
        revision_id=block.revision_id,
        block_key=block.block_key,
        block_type=block.block_type,
        section_key=block.section_key,
        platform_scope=block.platform_scope,
        story_id=block.story_id,
        title=block.title,
        content=block.content,
        sort_order=block.sort_order,
        is_locked=block.is_locked,
        is_manual=block.is_manual,
        payload=block.payload,
        updated_at=block.updated_at,
    )


def revision_to_response(revision: ArticleRevision) -> ArticleRevisionResponse:
    return ArticleRevisionResponse(
        id=revision.id,
        article_id=revision.article_id,
        version_number=revision.version_number,
        change_type=revision.change_type,
        change_note=revision.change_note,
        template_id=revision.template_id,
        snapshot=revision.snapshot,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
    )


def _load_approved_stories(
    session: Session,
    story_ids: list[int] | None,
    *,
    period_type: str = 'daily',
    section_engagement: dict[str, object] | None = None,
) -> list[Story]:
    query = select(Story).where(Story.status == StoryStatus.APPROVED)
    feedback = section_engagement or build_section_engagement_snapshots(session)
    if story_ids:
        requested_story_ids = list(dict.fromkeys(story_ids))
        stories = session.scalars(query.where(Story.id.in_(requested_story_ids))).all()
        loaded_story_ids = {story.id for story in stories}
        if loaded_story_ids != set(requested_story_ids):
            raise ValueError('One or more selected stories are unavailable or not approved')
        return _compose_digest_story_mix(stories, period_type, feedback)

    stories = session.scalars(query).all()
    return _compose_digest_story_mix(stories, period_type, feedback)


def _compose_digest_story_mix(
    stories: list[Story],
    period_type: str,
    section_engagement: dict[str, object],
) -> list[Story]:
    ranked_stories = _sort_stories_for_digest(stories, section_engagement)
    if period_type == 'daily' or len(ranked_stories) <= 1:
        return ranked_stories

    section_groups: dict[str, list[Story]] = {}
    for story in ranked_stories:
        section_groups.setdefault(resolve_story_primary_section(story), []).append(story)
    if len(section_groups) <= 1:
        return ranked_stories

    section_cycle = _build_section_cycle(list(section_groups.keys()), period_type, section_engagement)
    mixed_stories: list[Story] = []
    while any(section_groups.values()):
        progressed = False
        for section in section_cycle:
            bucket = section_groups.get(section)
            if bucket:
                mixed_stories.append(bucket.pop(0))
                progressed = True
        if not progressed:
            break
    return mixed_stories


def _build_section_cycle(
    ordered_sections: list[str],
    period_type: str,
    section_engagement: dict[str, object],
) -> list[str]:
    bonus_sections: list[str] = []
    for section in ordered_sections:
        feedback = section_engagement.get(section)
        momentum_tier = str(getattr(feedback, 'momentum_tier', 'steady')) if feedback is not None else 'steady'
        if momentum_tier in {'hot', 'rising'}:
            bonus_sections.append(section)
        if period_type == 'monthly' and momentum_tier == 'hot':
            bonus_sections.append(section)
    return [*ordered_sections, *bonus_sections]


def _story_to_candidate(story: Story, *, score_override: float | None = None) -> StoryCandidate:
    return StoryCandidate(
        payload_story_id=story.id,
        story_key=story.story_key,
        cluster_title=story.cluster_title,
        summary=story.summary,
        highlights=story.highlights,
        source_links=story.source_links,
        tags=story.tags,
        risk_flags=story.risk_flags,
        score=score_override if score_override is not None else story.score,
        item_count=story.item_count,
        first_seen_at=story.first_seen_at,
        last_seen_at=story.last_seen_at,
    )


def _order_story_models_by_candidates(stories: list[Story], candidates: list[StoryCandidate]) -> list[Story]:
    order_lookup = {candidate.payload_story_id: index for index, candidate in enumerate(candidates)}
    return sorted(stories, key=lambda story: order_lookup.get(story.id, len(order_lookup)))


def _upsert_post_variants(session: Session, article_id: int, posts: dict[str, str]) -> None:
    existing_variants = {
        variant.platform: variant
        for variant in session.scalars(select(PostVariant).where(PostVariant.article_id == article_id)).all()
    }

    for platform, content in posts.items():
        existing = existing_variants.get(platform)
        if existing is None:
            session.add(PostVariant(article_id=article_id, platform=platform, content=content))
            continue
        existing.content = content


def _create_active_revision(
    session: Session,
    *,
    article: ArticleDraft,
    approved_stories: list[Story],
    sections: list[str],
    posts: dict[str, str],
    template: DigestTemplate | None,
) -> tuple[int, int]:
    current_versions = session.scalars(
        select(ArticleRevision).where(ArticleRevision.article_id == article.id).order_by(ArticleRevision.version_number.asc())
    ).all()
    next_version_number = current_versions[-1].version_number + 1 if current_versions else 1

    revision = ArticleRevision(
        article_id=article.id,
        version_number=next_version_number,
        change_type='generate',
        template_id=template.id if template is not None else None,
        snapshot={},
    )
    session.add(revision)
    session.flush()

    blocks = _build_revision_blocks(article, revision.id, approved_stories, sections, posts)
    revision.snapshot = {
        'title': article.title,
        'summary': article.summary,
        'body': article.body,
        'story_ids': article.story_ids,
        'story_keys': article.story_keys,
        'sections': sections,
        'posts': posts,
        'template_id': template.id if template is not None else None,
        'template_name': template.name if template is not None else None,
        'blocks': [_serialize_block(block) for block in blocks],
    }
    session.add_all(blocks)
    article.active_revision_id = revision.id
    session.flush()
    return revision.id, len(blocks)


def _serialize_block(block: ArticleBlock) -> dict:
    return {
        'block_key': block.block_key,
        'block_type': block.block_type,
        'section_key': block.section_key,
        'platform_scope': block.platform_scope,
        'story_id': block.story_id,
        'title': block.title,
        'content': block.content,
        'sort_order': block.sort_order,
        'is_locked': block.is_locked,
        'is_manual': block.is_manual,
        'payload': block.payload,
    }


def _build_revision_blocks(
    article: ArticleDraft,
    revision_id: int,
    approved_stories: list[Story],
    sections: list[str],
    posts: dict[str, str],
) -> list[ArticleBlock]:
    blocks: list[ArticleBlock] = [
        ArticleBlock(
            article_id=article.id,
            revision_id=revision_id,
            block_key='title',
            block_type='title',
            content=article.title,
            sort_order=10,
        ),
        ArticleBlock(
            article_id=article.id,
            revision_id=revision_id,
            block_key='summary',
            block_type='summary',
            content=article.summary,
            sort_order=20,
        ),
        ArticleBlock(
            article_id=article.id,
            revision_id=revision_id,
            block_key='intro',
            block_type='intro',
            content=article.body,
            sort_order=30,
            payload={'sections': sections},
        ),
    ]

    sort_order = 100
    for story in approved_stories:
        section_key = resolve_story_primary_section(story)
        blocks.append(
            ArticleBlock(
                article_id=article.id,
                revision_id=revision_id,
                block_key=f'story-{story.id}',
                block_type='story_paragraph',
                section_key=section_key,
                story_id=story.id,
                title=story.cluster_title,
                content=story.summary,
                sort_order=sort_order,
                payload={'story_key': story.story_key},
            )
        )
        sort_order += 10

    for platform, content in posts.items():
        blocks.append(
            ArticleBlock(
                article_id=article.id,
                revision_id=revision_id,
                block_key=f'platform-{platform}',
                block_type='platform_body',
                platform_scope=platform,
                content=content,
                sort_order=sort_order,
            )
        )
        sort_order += 10

    return blocks


def _sort_stories_for_digest(stories: list[Story], section_engagement: dict[str, object]) -> list[Story]:
    return sorted(
        stories,
        key=lambda story: (_ranking_score_for_story(story, section_engagement), story.last_seen_at, story.id),
        reverse=True,
    )


def _ranking_score_for_story(story: Story, section_engagement: dict[str, object]) -> float:
    primary_section = resolve_story_primary_section(story)
    feedback = section_engagement.get(primary_section)
    if feedback is None:
        return story.score
    score_boost = float(getattr(feedback, 'score_boost', 0.0))
    score_penalty = float(getattr(feedback, 'score_penalty', 0.0))
    return round(max(story.score + score_boost - score_penalty, 0.0), 2)


def _variant_count_by_article(session: Session) -> dict[int, int]:
    variants = session.scalars(select(PostVariant)).all()
    counts: dict[int, int] = {}
    for variant in variants:
        counts[variant.article_id] = counts.get(variant.article_id, 0) + 1
    return counts


def _build_article_sections_lookup(session: Session, articles: list[ArticleDraft]) -> dict[int, list[str]]:
    if not articles:
        return {}

    story_ids = sorted({story_id for article in articles for story_id in article.story_ids})
    if not story_ids:
        return {article.id: [] for article in articles}

    stories = session.scalars(select(Story).where(Story.id.in_(story_ids))).all()
    story_candidates = {story.id: _story_to_candidate(story) for story in stories}
    lookup: dict[int, list[str]] = {}
    for article in articles:
        candidates = [story_candidates[story_id] for story_id in article.story_ids if story_id in story_candidates]
        lookup[article.id] = resolve_article_sections(candidates, group_stories_by_section(candidates))
    return lookup


def _build_article_revision_stats_lookup(session: Session, articles: list[ArticleDraft]) -> dict[int, dict[str, int | None]]:
    if not articles:
        return {}

    active_revision_ids = {article.active_revision_id for article in articles if article.active_revision_id is not None}
    if not active_revision_ids:
        return {article.id: {'active_revision_id': article.active_revision_id, 'block_count': 0} for article in articles}

    block_counts: dict[int, int] = {}
    blocks = session.scalars(select(ArticleBlock).where(ArticleBlock.revision_id.in_(active_revision_ids))).all()
    for block in blocks:
        block_counts[block.revision_id] = block_counts.get(block.revision_id, 0) + 1

    return {
        article.id: {
            'active_revision_id': article.active_revision_id,
            'block_count': block_counts.get(article.active_revision_id, 0) if article.active_revision_id is not None else 0,
        }
        for article in articles
    }


def _build_template_lookup(session: Session, articles: list[ArticleDraft]) -> dict[int, DigestTemplate]:
    template_ids = sorted({article.template_id for article in articles if article.template_id is not None})
    if not template_ids:
        return {}
    templates = session.scalars(select(DigestTemplate).where(DigestTemplate.id.in_(template_ids))).all()
    return {template.id: template for template in templates}


def resolve_article_sections_for_story_ids(session: Session, story_ids: list[int]) -> list[str]:
    if not story_ids:
        return []

    stories = session.scalars(select(Story).where(Story.id.in_(story_ids))).all()
    candidates = [_story_to_candidate(story) for story in stories]
    return resolve_article_sections(candidates, group_stories_by_section(candidates))