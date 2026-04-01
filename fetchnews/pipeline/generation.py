from __future__ import annotations

from collections import OrderedDict
from datetime import date

from fetchnews.pipeline.platform_copy import PlatformCopyProfile
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
    platform_profiles: dict[str, PlatformCopyProfile] | None = None,
) -> DailyDigest:
    ordered = _order_stories_for_period(stories, period_type)
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

    posts = _build_platform_posts(article, ordered, article_sections, period_type, platform_profiles or {})
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


def _order_stories_for_period(stories: list[StoryCandidate], period_type: str) -> list[StoryCandidate]:
    if period_type in {"weekly", "monthly"}:
        return list(stories)
    return sorted(stories, key=lambda story: (story.score, story.last_seen_at), reverse=True)


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


def _build_platform_posts(
    article: ArticleDraftPayload,
    stories: list[StoryCandidate],
    article_sections: list[str],
    period_type: str,
    platform_profiles: dict[str, PlatformCopyProfile],
) -> dict[str, str]:
    section_summary = " / ".join(get_section_label(section) for section in article_sections[:2]) or "综合观察"
    top_story = stories[0] if stories else None
    top_label = top_story.cluster_title if top_story else "本期暂无通过审核内容"
    top_tags = " #" + " #".join(top_story.tags[:2]) if top_story and top_story.tags else ""

    return {
        "wechat": _build_wechat_post(article, stories, article_sections, section_summary, period_type, platform_profiles.get("wechat")),
        "x": _build_x_post(article, top_label, article_sections, section_summary, period_type, top_story, top_tags, platform_profiles.get("x")),
        "telegram": _build_telegram_post(article, stories, article_sections, period_type, platform_profiles.get("telegram")),
    }


def _build_wechat_post(
    article: ArticleDraftPayload,
    stories: list[StoryCandidate],
    article_sections: list[str],
    section_summary: str,
    period_type: str,
    profile: PlatformCopyProfile | None,
) -> str:
    strategy = profile.strategy if profile is not None else "balanced"
    period_scope = _build_period_scope_label(period_type)
    lead_section = _build_lead_section_label(article_sections)
    if strategy == "editorial":
        if period_type in {"weekly", "monthly"}:
            return "\n\n".join([
                article.title,
                f"编辑摘要：{article.summary}",
                f"{period_scope}主线栏目：{lead_section}",
                f"栏目轮值：{section_summary}",
                article.body,
            ])
        return "\n\n".join([
            article.title,
            f"编辑摘要：{article.summary}",
            f"本期栏目：{section_summary}",
            article.body,
        ])
    if strategy == "actionable":
        if period_type in {"weekly", "monthly"}:
            return "\n\n".join([
                article.title,
                f"{period_scope}主线栏目：{lead_section}",
                f"栏目轮值：{section_summary}",
                _build_story_bullet_list(stories),
                article.body,
            ])
        return "\n\n".join([
            article.title,
            "先看这 3 条：",
            _build_story_bullet_list(stories),
            article.body,
        ])
    return f"{article.title}\n\n{article.summary}\n\n{article.body}"


def _build_x_post(
    article: ArticleDraftPayload,
    top_label: str,
    article_sections: list[str],
    section_summary: str,
    period_type: str,
    top_story: StoryCandidate | None,
    top_tags: str,
    profile: PlatformCopyProfile | None,
) -> str:
    strategy = profile.strategy if profile is not None else "headline"
    period_scope = _build_period_scope_label(period_type)
    lead_section = _build_lead_section_label(article_sections)
    if strategy == "conversational":
        focus_line = _build_focus_line(top_story)
        if period_type in {"weekly", "monthly"}:
            return f"{article.title}?{period_scope}最值得继续追踪的栏目是{lead_section}：{top_label}。{focus_line}。你最想继续跟进哪条？{top_tags}"[:280]
        return f"{article.title}?{section_summary}：{top_label}。{focus_line}。你最想继续跟进哪条？{top_tags}"[:280]
    if strategy == "link_out":
        if period_type in {"weekly", "monthly"}:
            return f"{article.title}?{period_scope}栏目轮值：{section_summary}。先看 {lead_section}。{top_tags}"[:280]
        return f"{article.title}?{section_summary}：{top_label}。今天更偏工具与来源速览。{top_tags}"[:280]
    return f"{article.title}?{section_summary}：{top_label}{top_tags}"[:280]


def _build_telegram_post(
    article: ArticleDraftPayload,
    stories: list[StoryCandidate],
    article_sections: list[str],
    period_type: str,
    profile: PlatformCopyProfile | None,
) -> str:
    strategy = profile.strategy if profile is not None else "digest"
    section_summary = " / ".join(get_section_label(section) for section in article_sections[:3]) or "综合观察"
    if strategy == "bulletin":
        if period_type in {"weekly", "monthly"}:
            return "\n\n".join([
                article.title,
                "栏目速览",
                section_summary,
                _build_story_bullet_list(stories),
                article.summary,
            ])
        return "\n\n".join([
            article.title,
            "速览清单",
            _build_story_bullet_list(stories),
            article.summary,
        ])
    if strategy == "discussion":
        if period_type in {"weekly", "monthly"}:
            return "\n\n".join([
                article.title,
                "栏目速览",
                section_summary,
                _build_discussion_prompts(stories),
                article.summary,
            ])
        return "\n\n".join([
            article.title,
            "讨论焦点",
            _build_discussion_prompts(stories),
            article.summary,
        ])
    return f"{article.title}\n\n{article.summary}\n\n{article.body}"


def _build_period_scope_label(period_type: str) -> str:
    if period_type == "weekly":
        return "本周"
    if period_type == "monthly":
        return "本月"
    return "本期"


def _build_lead_section_label(article_sections: list[str]) -> str:
    if not article_sections:
        return "综合观察"
    return get_section_label(article_sections[0])


def _build_story_bullet_list(stories: list[StoryCandidate], limit: int = 3) -> str:
    if not stories:
        return "- 暂无可分发内容"
    lines = [f"- {story.cluster_title}" for story in stories[:limit]]
    return "\n".join(lines)


def _build_discussion_prompts(stories: list[StoryCandidate], limit: int = 2) -> str:
    if not stories:
        return "- 暂无可讨论内容"
    prompts: list[str] = []
    for story in stories[:limit]:
        highlight = story.highlights[0] if story.highlights else story.summary
        prompts.append(f"- {story.cluster_title}：{highlight}")
    return "\n".join(prompts)


def _build_focus_line(top_story: StoryCandidate | None) -> str:
    if top_story is None:
        return "继续观察今日动态"
    if top_story.highlights:
        return top_story.highlights[0]
    return top_story.summary


def _format_period_marker(target_date: date, period_type: str) -> str:
    if period_type == "weekly":
        iso_year, iso_week, _ = target_date.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if period_type == "monthly":
        return target_date.strftime("%Y-%m")
    return target_date.isoformat()
