from datetime import UTC, date, datetime

from fetchnews.pipeline.generation import generate_daily_digest
from fetchnews.pipeline.sections import get_section_label
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
            primary_section="open_source",
            sections=["open_source", "agents"],
        )
    ]

    digest = generate_daily_digest(target_date=date(2026, 3, 25), stories=stories)

    assert "AI 资讯日报" in digest.article.title
    assert "OpenAI 发布了用于评估 agent 工作流的新工具集。" in digest.article.body
    assert "x" in digest.posts
    assert "telegram" in digest.posts
    assert digest.article.sections == ["open_source", "agents"]


def test_generate_digest_groups_stories_by_thematic_sections() -> None:
    stories = [
        StoryCandidate(
            story_key="story-open-source",
            cluster_title="Open-source agent runtime ships on GitHub",
            summary="A new agent runtime has been published as an open-source project.",
            highlights=["GitHub 发布", "聚焦 agent workflow"],
            source_links=["https://github.com/example/agent-runtime"],
            tags=["github", "agent", "runtime"],
            risk_flags=[],
            score=9.3,
            item_count=2,
            first_seen_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
            last_seen_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
            primary_section="open_source",
            sections=["open_source", "agents"],
        ),
        StoryCandidate(
            story_key="story-research",
            cluster_title="New arXiv paper improves reasoning benchmarks",
            summary="A new research paper improves reasoning evaluation.",
            highlights=["论文更新", "评测更稳定"],
            source_links=["https://arxiv.org/abs/1234.5678"],
            tags=["paper", "benchmark", "reasoning"],
            risk_flags=[],
            score=8.9,
            item_count=1,
            first_seen_at=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
            last_seen_at=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
            primary_section="research",
            sections=["research"],
        ),
    ]

    digest = generate_daily_digest(target_date=date(2026, 4, 1), stories=stories)

    assert f"## {get_section_label('open_source')}" in digest.article.body
    assert f"## {get_section_label('research')}" in digest.article.body
    assert digest.article.sections == ["open_source", "research"]
    assert "开源项目 / 论文精选" in digest.article.summary