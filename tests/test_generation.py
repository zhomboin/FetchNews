from datetime import date

from fetchnews.pipeline.generation import generate_daily_digest
from fetchnews.schemas import StoryCandidate


def test_generate_daily_digest_returns_article_and_posts() -> None:
    stories = [
        StoryCandidate(
            story_key="story-1",
            cluster_title="OpenAI releases agent benchmark toolkit",
            summary="OpenAI 发布了用于评估 agent 工作流的新工具集。",
            highlights=["支持多任务评估", "面向开源社区"],
            source_links=["https://github.com/openai/agent-bench"],
            tags=["github", "agent"],
            risk_flags=[],
            score=9.2,
            item_count=2,
        )
    ]

    digest = generate_daily_digest(target_date=date(2026, 3, 25), stories=stories)

    assert "AI 资讯日报" in digest.article.title
    assert "OpenAI 发布了用于评估 agent 工作流的新工具集" in digest.article.body
    assert "x" in digest.posts
    assert "telegram" in digest.posts
