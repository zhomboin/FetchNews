from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, PostVariant, Story, StoryStatus
from fetchnews.pipeline.engagement import build_section_engagement_snapshots, resolve_story_primary_section
from fetchnews.pipeline.generation import generate_digest, group_stories_by_section, resolve_article_sections
from fetchnews.pipeline.platform_copy import build_platform_copy_profiles
from fetchnews.schemas import ArticleDraftResponse, PostVariantResponse, StoryCandidate


def generate_and_persist_daily_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type="daily",
        story_ids=story_ids,
        generation_note=generation_note,
    )


def generate_and_persist_weekly_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type="weekly",
        story_ids=story_ids,
        generation_note=generation_note,
    )


def generate_and_persist_monthly_digest(
    session: Session,
    target_date: date,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
) -> ArticleDraftResponse:
    return generate_and_persist_digest(
        session,
        target_date=target_date,
        period_type="monthly",
        story_ids=story_ids,
        generation_note=generation_note,
    )


def generate_and_persist_digest(
    session: Session,
    target_date: date,
    period_type: str,
    story_ids: list[int] | None = None,
    generation_note: str | None = None,
) -> ArticleDraftResponse:
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
    platform_profiles = build_platform_copy_profiles(session)
    digest = generate_digest(
        target_date=target_date,
        period_type=period_type,
        stories=story_candidates,
        generation_note=generation_note,
        platform_profiles=platform_profiles,
    )

    normalized_note = generation_note.strip() if generation_note and generation_note.strip() else None
    selected_story_ids = [story.id for story in approved_stories]

    article = session.scalar(
        select(ArticleDraft).where(
            ArticleDraft.period_type == period_type,
            ArticleDraft.target_date == target_date,
        )
    )
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
        article.status = ArticleStatus.READY
        session.flush()

    _upsert_post_variants(session, article.id, digest.posts)
    session.flush()
    session.refresh(article)
    variants = list_article_variants(session, article.id)
    return article_to_response(article, len(variants), sections=digest.article.sections)


def list_articles(session: Session) -> list[ArticleDraftResponse]:
    articles = session.scalars(select(ArticleDraft).order_by(ArticleDraft.target_date.desc(), ArticleDraft.id.desc())).all()
    variant_counts = _variant_count_by_article(session)
    article_sections = _build_article_sections_lookup(session, articles)
    return [
        article_to_response(article, variant_counts.get(article.id, 0), sections=article_sections.get(article.id, []))
        for article in articles
    ]


def list_article_variants(session: Session, article_id: int) -> list[PostVariantResponse]:
    variants = session.scalars(
        select(PostVariant).where(PostVariant.article_id == article_id).order_by(PostVariant.platform.asc())
    ).all()
    return [variant_to_response(variant) for variant in variants]


def article_to_response(article: ArticleDraft, variant_count: int, *, sections: list[str] | None = None) -> ArticleDraftResponse:
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


def _load_approved_stories(
    session: Session,
    story_ids: list[int] | None,
    *,
    period_type: str = "daily",
    section_engagement: dict[str, object] | None = None,
) -> list[Story]:
    query = select(Story).where(Story.status == StoryStatus.APPROVED)
    feedback = section_engagement or build_section_engagement_snapshots(session)
    if story_ids:
        requested_story_ids = list(dict.fromkeys(story_ids))
        stories = session.scalars(query.where(Story.id.in_(requested_story_ids))).all()
        loaded_story_ids = {story.id for story in stories}
        if loaded_story_ids != set(requested_story_ids):
            raise ValueError("One or more selected stories are unavailable or not approved")
        return _compose_digest_story_mix(stories, period_type, feedback)

    stories = session.scalars(query).all()
    return _compose_digest_story_mix(stories, period_type, feedback)




def _compose_digest_story_mix(
    stories: list[Story],
    period_type: str,
    section_engagement: dict[str, object],
) -> list[Story]:
    ranked_stories = _sort_stories_for_digest(stories, section_engagement)
    if period_type == "daily" or len(ranked_stories) <= 1:
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
        momentum_tier = str(getattr(feedback, "momentum_tier", "steady")) if feedback is not None else "steady"
        if momentum_tier in {"hot", "rising"}:
            bonus_sections.append(section)
        if period_type == "monthly" and momentum_tier == "hot":
            bonus_sections.append(section)
    return [*ordered_sections, *bonus_sections]


def _story_to_candidate(story: Story, *, score_override: float | None = None) -> StoryCandidate:
    return StoryCandidate(
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
    score_boost = float(getattr(feedback, "score_boost", 0.0))
    score_penalty = float(getattr(feedback, "score_penalty", 0.0))
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

def resolve_article_sections_for_story_ids(session: Session, story_ids: list[int]) -> list[str]:
    if not story_ids:
        return []

    stories = session.scalars(select(Story).where(Story.id.in_(story_ids))).all()
    candidates = [_story_to_candidate(story) for story in stories]
    return resolve_article_sections(candidates, group_stories_by_section(candidates))