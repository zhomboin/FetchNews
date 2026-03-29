from datetime import UTC, datetime

from fetchnews.pipeline.clustering import cluster_items
from fetchnews.pipeline.normalize import normalize_raw_item
from fetchnews.schemas import RawIngestedItem


def test_normalize_raw_item_extracts_canonical_url_language_tags_and_keywords() -> None:
    normalized = normalize_raw_item(
        RawIngestedItem(
            source_slug="openai-blog",
            external_id="blog-1",
            title="OpenAI releases an agent benchmark toolkit",
            url="https://openai.com/blog/agent-benchmark-toolkit?utm_source=x#section",
            author="OpenAI",
            published_at=datetime(2026, 3, 25, 9, 0, tzinfo=UTC),
            content="The post introduces a toolkit for evaluating agent workflows.",
            metadata={"category": "blog", "tags": ["agents", "benchmark"]},
        ),
        source_priority="P0",
    )

    assert normalized.canonical_url == "https://openai.com/blog/agent-benchmark-toolkit"
    assert normalized.normalized_title == "openai releases agent benchmark toolkit"
    assert normalized.language == "en"
    assert normalized.tags[:3] == ["openai-blog", "agents", "benchmark"]
    assert normalized.keywords[:3] == ["openai", "releases", "agent"]


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
        ),
        source_priority="P0",
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
        ),
        source_priority="P0",
    )

    stories = cluster_items([first, second])

    assert len(stories) == 1
    story = stories[0]
    assert story.item_count == 2
    assert "agent benchmark toolkit" in story.cluster_title.lower()
    assert len(story.source_links) == 2
    assert story.score > 0


def test_cluster_scoring_prefers_high_trust_sources_over_secondary_volume() -> None:
    published_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
    high_trust_items = [
        normalize_raw_item(
            RawIngestedItem(
                source_slug="github-trending",
                external_id="repo-1",
                title="OpenAI releases agent benchmark toolkit",
                url="https://github.com/openai/agent-bench",
                author="openai",
                published_at=published_at,
                content="A toolkit for evaluating agent workflows.",
                metadata={"stars": 1200},
            ),
            source_priority="P0",
        ),
        normalize_raw_item(
            RawIngestedItem(
                source_slug="openai-blog",
                external_id="blog-1",
                title="OpenAI releases an agent benchmark toolkit",
                url="https://openai.com/blog/agent-benchmark-toolkit",
                author="OpenAI",
                published_at=published_at,
                content="The post introduces a toolkit for evaluating agent workflows.",
                metadata={"category": "blog"},
            ),
            source_priority="P0",
        ),
    ]
    low_trust_items = [
        normalize_raw_item(
            RawIngestedItem(
                source_slug=f"secondary-{index}",
                external_id=f"secondary-{index}",
                title="Community discussion of agent benchmark toolkit",
                url=f"https://example.com/posts/{index}",
                author="community",
                published_at=published_at,
                content="A repost discussing the toolkit.",
                metadata={"category": "community"},
            ),
            source_priority="P2",
        )
        for index in range(5)
    ]

    high_trust_story = cluster_items(high_trust_items)[0]
    low_trust_story = cluster_items(low_trust_items)[0]

    assert high_trust_story.score > low_trust_story.score
def test_source_quality_rules_blacklist_and_demote_items() -> None:
    published_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)

    trusted = normalize_raw_item(
        RawIngestedItem(
            source_slug="openai-blog",
            external_id="blog-1",
            title="OpenAI releases an agent benchmark toolkit",
            url="https://openai.com/blog/agent-benchmark-toolkit",
            author="OpenAI",
            published_at=published_at,
            content="The post introduces a toolkit for evaluating agent workflows.",
            metadata={"category": "blog"},
        ),
        source_priority="P0",
        source_config={"trust_score": 7.0, "score_multiplier": 1.05},
    )
    neutral_repost = normalize_raw_item(
        RawIngestedItem(
            source_slug="reddit-ml",
            external_id="reddit-neutral-1",
            title="OpenAI agent benchmark toolkit deep dive",
            url="https://openai.com/blog/agent-benchmark-toolkit?ref=community-neutral",
            author="community",
            published_at=published_at,
            content="Community recap for the benchmark toolkit.",
            metadata={"category": "community"},
        ),
        source_priority="P2",
        source_config={"score_multiplier": 1.0},
    )
    demoted_repost = normalize_raw_item(
        RawIngestedItem(
            source_slug="reddit-ml",
            external_id="reddit-demoted-1",
            title="OpenAI agent benchmark toolkit discussion",
            url="https://openai.com/blog/agent-benchmark-toolkit?ref=community-demoted",
            author="community",
            published_at=published_at,
            content="Community discussion for the benchmark toolkit.",
            metadata={"category": "community"},
        ),
        source_priority="P2",
        source_config={"score_multiplier": 0.75, "demote_title_keywords": ["discussion"]},
    )
    blacklisted_item = normalize_raw_item(
        RawIngestedItem(
            source_slug="reddit-ml",
            external_id="reddit-blocked-1",
            title="Weekly self-promo thread",
            url="https://reddit.com/r/MachineLearning/comments/self-promo",
            author="community",
            published_at=published_at,
            content="Self-promo collection.",
            metadata={"category": "community"},
        ),
        source_priority="P2",
        source_config={"blacklist_title_keywords": ["self-promo"]},
    )

    neutral_story = cluster_items([trusted, neutral_repost])[0]
    governed_stories = cluster_items([trusted, demoted_repost, blacklisted_item])

    assert len(governed_stories) == 1
    assert governed_stories[0].item_count == 2
    assert "demoted_source_signal" in governed_stories[0].risk_flags
    assert governed_stories[0].score < neutral_story.score