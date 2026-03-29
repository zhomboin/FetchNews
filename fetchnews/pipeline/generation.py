from __future__ import annotations

from collections import OrderedDict
from datetime import date

from fetchnews.pipeline.sections import get_section_label
from fetchnews.schemas import ArticleDraftPayload, DailyDigest, StoryCandidate


PERIOD_LABELS = {
    "daily": "日报",
    "weekly": "周报",
    "monthly": "月报",
}


def generate_digest(
    target_date: date,
    stories: list[StoryCandidate],
    period_type: str = "daily",
    generation_note: str | None = None,
) -> DailyDigest:
    ordered = sorted(stories, key=lambda story: (story.score, story.last_seen_at), reverse=True)
    section_groups = group_stories_by_section(ordered)
    article_sections = resolve_article_sections(ordered, section_groups)

    period_label = PERIOD_LABELS.get(period_type, PERIOD_LABELS["daily"])
    summary = _build_summary(ordered, article_sections)
    body = _build_body(ordered, section_groups, generation_note)
    article = ArticleDraftPayload(
        period_type=period_type,
        target_date=target_date,
        title=f"AI 资讯{period_label} {_format_period_marker(target_date, period_type)}",
        summary=summary,
        body=body,
        story_keys=[story.story_key for story in ordered],
        sections=article_sections,
    )

    top_story = ordered[0] if ordered else None
    top_label = top_story.cluster_title if top_story else "本期暂无通过审核内容"
    top_sections = " / ".join(get_section_label(section) for section in article_sections[:2])
    top_tags = " #" + " #".join(top_story.tags[:2]) if top_story and top_story.tags else ""
    posts = {
        "wechat": f"{article.title}\n\n{article.summary}\n\n{article.body}",
        "x": f"{article.title}｜{top_sections or '综合观察'}：{top_label}{top_tags}"[:280],
        "telegram": f"{article.title}\n\n{article.summary}\n\n{article.body}",
    }
    return DailyDigest(article=article, posts=posts)


def generate_daily_digest(
    target_date: date,
    stories: list[StoryCandidate],
    generation_note: str | None = None,
) -> DailyDigest:
    return generate_digest(
        target_date=target_date,
        stories=stories,
        period_type="daily",
        generation_note=generation_note,
    )


def group_stories_by_section(stories: list[StoryCandidate]) -> OrderedDict[str, list[StoryCandidate]]:
    grouped: OrderedDict[str, list[StoryCandidate]] = OrderedDict()
    for story in stories:
        grouped.setdefault(story.primary_section, []).append(story)
    return grouped


def resolve_article_sections(
    stories: list[StoryCandidate],
    section_groups: OrderedDict[str, list[StoryCandidate]] | None = None,
) -> list[str]:
    if not stories:
        return []

    grouped = section_groups or group_stories_by_section(stories)
    if len(grouped) == 1:
        return stories[0].sections
    return list(grouped.keys())


def _build_summary(stories: list[StoryCandidate], article_sections: list[str]) -> str:
    if not stories:
        return "本期暂无通过审核的 AI 资讯。"

    section_labels = " / ".join(get_section_label(section) for section in article_sections[:3]) or "综合观察"
    return f"本期整理 {len(stories)} 条高价值 AI 资讯，重点栏目：{section_labels}。"


def _build_body(
    stories: list[StoryCandidate],
    section_groups: OrderedDict[str, list[StoryCandidate]],
    generation_note: str | None,
) -> str:
    if not stories:
        if generation_note:
            return f"编辑说明：{generation_note}\n\n本期暂无通过审核的 AI 资讯。"
        return "本期暂无通过审核的 AI 资讯。"

    body_blocks: list[str] = []
    if generation_note:
        body_blocks.append(f"编辑说明：{generation_note}")

    for section, section_stories in section_groups.items():
        section_lines = [f"## {get_section_label(section)}"]
        for index, story in enumerate(section_stories, start=1):
            highlights = "；".join(story.highlights[:2]) if story.highlights else "待补充亮点"
            sources = " / ".join(story.source_links[:3])
            section_lines.append(
                f"{index}. {story.cluster_title}\n"
                f"摘要：{story.summary}\n"
                f"亮点：{highlights}\n"
                f"来源：{sources}"
            )
        body_blocks.append("\n\n".join(section_lines))

    return "\n\n".join(body_blocks)


def _format_period_marker(target_date: date, period_type: str) -> str:
    if period_type == "weekly":
        iso_year, iso_week, _ = target_date.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if period_type == "monthly":
        return target_date.strftime("%Y-%m")
    return target_date.isoformat()