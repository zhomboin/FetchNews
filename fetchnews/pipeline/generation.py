from datetime import date

from fetchnews.schemas import ArticleDraftPayload, DailyDigest, StoryCandidate


def generate_daily_digest(target_date: date, stories: list[StoryCandidate]) -> DailyDigest:
    ordered = sorted(stories, key=lambda story: story.score, reverse=True)
    body_sections = []
    for index, story in enumerate(ordered, start=1):
        body_sections.append(f"{index}. {story.cluster_title}\n{story.summary}\n来源：{', '.join(story.source_links)}")

    article = ArticleDraftPayload
    payload = article(
        target_date=target_date,
        title=f"AI 资讯日报 {target_date.isoformat()}",
        summary=f"今日共整理 {len(ordered)} 条 AI 重点资讯。",
        body="\n\n".join(body_sections),
        story_keys=[story.story_key for story in ordered],
    )
    posts = {
        "x": f"AI 资讯日报 {target_date.isoformat()}：{ordered[0].cluster_title}" if ordered else "AI 资讯日报暂无内容",
        "telegram": payload.summary,
        "wechat": payload.title,
    }
    return DailyDigest(article=payload, posts=posts)
