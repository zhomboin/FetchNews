from datetime import UTC, datetime

from fetchnews.pipeline.clustering import cluster_items
from fetchnews.pipeline.normalize import normalize_raw_item
from fetchnews.schemas import RawIngestedItem


def test_normalize_and_cluster_merge_similar_items() -> None:
    published_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)

    first = normalize_raw_item(
        RawIngestedItem(
            source_slug="github-trending",
            external_id="repo-1",
            title="OpenAI releases agent benchmark toolkit",
            url="https://github.com/openai/agent-bench",
            author="openai",
            published_at=published_at,
            content="A toolkit for evaluating agent workflows.",
            metadata={"stars": 1200},
        )
    )
    second = normalize_raw_item(
        RawIngestedItem(
            source_slug="openai-blog",
            external_id="blog-1",
            title="OpenAI releases an agent benchmark toolkit",
            url="https://openai.com/blog/agent-benchmark-toolkit",
            author="OpenAI",
            published_at=published_at,
            content="The post introduces a toolkit for evaluating agent workflows.",
            metadata={"category": "blog"},
        )
    )

    stories = cluster_items([first, second])

    assert len(stories) == 1
    story = stories[0]
    assert story.item_count == 2
    assert "agent benchmark toolkit" in story.cluster_title.lower()
