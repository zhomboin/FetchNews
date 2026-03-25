from fetchnews.schemas import SourceSpec


DEFAULT_SOURCE_SPECS = [
    SourceSpec(slug="github-trending", label="GitHub Trending", platform="github", priority="P0", kind="html"),
    SourceSpec(slug="arxiv-cs-ai", label="arXiv cs.AI", platform="arxiv", priority="P0", kind="feed"),
    SourceSpec(slug="openai-blog", label="OpenAI Blog", platform="blog", priority="P0", kind="rss"),
    SourceSpec(slug="x-allowlist", label="X Allowlist", platform="x", priority="P0", kind="api"),
    SourceSpec(slug="hf-daily", label="Hugging Face Daily", platform="huggingface", priority="P1", kind="html"),
    SourceSpec(slug="reddit-ml", label="Reddit MachineLearning", platform="reddit", priority="P2", kind="rss"),
]


def priority_order(specs: list[SourceSpec]) -> list[SourceSpec]:
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(specs, key=lambda spec: (priority_rank.get(spec.priority, 9), spec.slug))
