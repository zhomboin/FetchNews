from __future__ import annotations

from fetchnews.schemas import SourceSpec


DEFAULT_SOURCE_SPECS = [
    SourceSpec(
        slug="github-trending",
        label="GitHub Trending",
        platform="github",
        priority="P0",
        kind="html",
        config={"url": "https://github.com/trending?since=daily"},
    ),
    SourceSpec(
        slug="arxiv-cs-ai",
        label="arXiv cs.AI",
        platform="arxiv",
        priority="P0",
        kind="feed",
        config={"url": "https://export.arxiv.org/rss/cs.AI"},
    ),
    SourceSpec(
        slug="openai-blog",
        label="OpenAI Blog",
        platform="blog",
        priority="P0",
        kind="rss",
        config={"url": "https://openai.com/news/rss.xml"},
    ),
    SourceSpec(
        slug="x-allowlist",
        label="X Allowlist",
        platform="x",
        priority="P0",
        kind="api",
        config={"allowlist": ["OpenAI", "AnthropicAI", "huggingface"]},
    ),
    SourceSpec(
        slug="hf-daily",
        label="Hugging Face Daily",
        platform="huggingface",
        priority="P1",
        kind="html",
        config={"url": "https://huggingface.co/papers"},
    ),
    SourceSpec(
        slug="reddit-ml",
        label="Reddit MachineLearning",
        platform="reddit",
        priority="P2",
        kind="rss",
        config={"url": "https://www.reddit.com/r/MachineLearning/.rss"},
    ),
]

_SOURCE_SPEC_BY_SLUG = {spec.slug: spec for spec in DEFAULT_SOURCE_SPECS}


def priority_order(specs: list[SourceSpec]) -> list[SourceSpec]:
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(specs, key=lambda spec: (priority_rank.get(spec.priority, 9), spec.slug))


def get_source_specs(source_slugs: list[str] | None = None) -> list[SourceSpec]:
    if source_slugs is None:
        return [spec for spec in priority_order(DEFAULT_SOURCE_SPECS) if spec.enabled]

    unknown = sorted({slug for slug in source_slugs if slug not in _SOURCE_SPEC_BY_SLUG})
    if unknown:
        raise ValueError(f"Unknown source slugs: {', '.join(unknown)}")

    return [_SOURCE_SPEC_BY_SLUG[slug] for slug in source_slugs if _SOURCE_SPEC_BY_SLUG[slug].enabled]
