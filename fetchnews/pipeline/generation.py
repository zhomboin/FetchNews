from __future__ import annotations

from datetime import date

from fetchnews.schemas import ArticleDraftPayload, DailyDigest, StoryCandidate


def generate_daily_digest(
    target_date: date,
    stories: list[StoryCandidate],
    generation_note: str | None = None,
) -> DailyDigest:
    ordered = sorted(stories, key=lambda story: (story.score, story.last_seen_at), reverse=True)
    body_sections: list[str] = []
    for index, story in enumerate(ordered, start=1):
        highlights = "；".join(story.highlights[:2]) if story.highlights else "待补充亮点"
        sources = "、".join(story.source_links[:3])
        body_sections.append(
            f"{index}. {story.cluster_title}\n"
            f"摘要：{story.summary}\n"
            f"亮点：{highlights}\n"
            f"来源：{sources}"
        )

    story_count = len(ordered)
    summary = f"今日整理 {story_count} 条高价值 AI 资讯，重点关注模型能力、开源工具链与基础设施更新。"
    body = "\n\n".join(body_sections) if body_sections else "今日暂无通过审核的 AI 资讯。"
    if generation_note:
        body = f"编辑说明：{generation_note}\n\n{body}"

    article = ArticleDraftPayload(
        target_date=target_date,
        title=f"AI 资讯日报 {target_date.isoformat()}",
        summary=summary,
        body=body,
        story_keys=[story.story_key for story in ordered],
    )

    top_story = ordered[0] if ordered else None
    top_label = top_story.cluster_title if top_story else "今日暂无通过审核内容"
    top_tags = " #" + " #".join(top_story.tags[:2]) if top_story and top_story.tags else ""
    posts = {
        "wechat": f"{article.title}\n\n{article.summary}\n\n{article.body}",
        "x": f"{article.title}｜{top_label}{top_tags}"[:280],
        "telegram": f"{article.title}\n\n{article.summary}\n\n{article.body}",
    }
    return DailyDigest(article=article, posts=posts)