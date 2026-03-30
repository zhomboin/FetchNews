from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, PublishJob, PublishJobStatus, Story
from fetchnews.pipeline.sections import get_section_label, infer_sections_from_signals


@dataclass(slots=True)
class SectionEngagementSnapshot:
    section: str
    label: str
    engagement_impressions: int = 0
    engagement_opens: int = 0
    engagement_clicks: int = 0
    engagement_interactions: int = 0
    published_jobs: int = 0
    momentum_tier: str = "steady"
    score_boost: float = 0.0
    score_penalty: float = 0.0

    @property
    def click_through_rate(self) -> float:
        if self.engagement_impressions <= 0:
            return 0.0
        return self.engagement_clicks / self.engagement_impressions

    @property
    def interaction_rate(self) -> float:
        if self.engagement_impressions <= 0:
            return 0.0
        return self.engagement_interactions / self.engagement_impressions


class _MutableSectionAggregate(dict[str, object]):
    pass


def build_section_engagement_snapshots(session: Session) -> dict[str, SectionEngagementSnapshot]:
    articles = session.scalars(select(ArticleDraft).order_by(ArticleDraft.id.asc())).all()
    if not articles:
        return {}

    article_sections = _resolve_article_primary_sections(session, articles)
    if not article_sections:
        return {}

    jobs = session.scalars(select(PublishJob).order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())).all()
    grouped: dict[str, _MutableSectionAggregate] = {}

    for job in jobs:
        section = article_sections.get(job.article_id)
        if not section:
            continue

        entry = grouped.setdefault(
            section,
            {
                "section": section,
                "label": get_section_label(section),
                "engagement_impressions": 0,
                "engagement_opens": 0,
                "engagement_clicks": 0,
                "engagement_interactions": 0,
                "published_jobs": 0,
            },
        )
        if job.status == PublishJobStatus.PUBLISHED:
            entry["published_jobs"] = int(entry["published_jobs"]) + 1

        metrics = job.performance_metrics or {}
        entry["engagement_impressions"] = int(entry["engagement_impressions"]) + _read_metric(metrics, "impressions")
        entry["engagement_opens"] = int(entry["engagement_opens"]) + _read_metric(metrics, "opens")
        entry["engagement_clicks"] = int(entry["engagement_clicks"]) + _read_metric(metrics, "clicks")
        entry["engagement_interactions"] = int(entry["engagement_interactions"]) + _read_metric(metrics, "interactions")

    snapshots: dict[str, SectionEngagementSnapshot] = {}
    for section, entry in grouped.items():
        impressions = int(entry["engagement_impressions"])
        clicks = int(entry["engagement_clicks"])
        interactions = int(entry["engagement_interactions"])
        momentum_tier, score_boost, score_penalty = _classify_section_momentum(
            impressions=impressions,
            clicks=clicks,
            interactions=interactions,
        )
        snapshots[section] = SectionEngagementSnapshot(
            section=section,
            label=str(entry["label"]),
            engagement_impressions=impressions,
            engagement_opens=int(entry["engagement_opens"]),
            engagement_clicks=clicks,
            engagement_interactions=interactions,
            published_jobs=int(entry["published_jobs"]),
            momentum_tier=momentum_tier,
            score_boost=score_boost,
            score_penalty=score_penalty,
        )
    return snapshots


def resolve_story_primary_section(story: Story) -> str:
    primary_section, _ = infer_sections_from_signals(
        title=story.cluster_title,
        summary=story.summary,
        tags=story.tags,
        source_hints=story.source_links,
    )
    return primary_section


def _resolve_article_primary_sections(session: Session, articles: list[ArticleDraft]) -> dict[int, str]:
    story_ids = sorted({story_id for article in articles for story_id in article.story_ids})
    if not story_ids:
        return {}

    stories = session.scalars(select(Story).where(Story.id.in_(story_ids))).all()
    stories_by_id = {story.id: story for story in stories}
    article_sections: dict[int, str] = {}
    for article in articles:
        article_stories = [stories_by_id[story_id] for story_id in article.story_ids if story_id in stories_by_id]
        if not article_stories:
            continue
        article_stories.sort(key=lambda story: (story.score, story.last_seen_at, story.id), reverse=True)
        article_sections[article.id] = resolve_story_primary_section(article_stories[0])
    return article_sections


def _classify_section_momentum(*, impressions: int, clicks: int, interactions: int) -> tuple[str, float, float]:
    if impressions <= 0:
        return "steady", 0.0, 0.0

    click_through_rate = clicks / impressions
    interaction_rate = interactions / impressions

    if impressions >= 600 and (click_through_rate >= 0.08 or interaction_rate >= 0.05):
        return "hot", 1.8, 0.0
    if impressions >= 250 and (click_through_rate >= 0.045 or interaction_rate >= 0.03):
        return "rising", 0.9, 0.0
    if impressions >= 250 and click_through_rate < 0.025 and interaction_rate < 0.02:
        return "cooling", 0.0, 1.1
    return "steady", 0.0, 0.0


def _read_metric(metrics: dict[str, object], key: str) -> int:
    value = metrics.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0