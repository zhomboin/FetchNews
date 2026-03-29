from __future__ import annotations

from collections.abc import Sequence

SECTION_ORDER = [
    "model_release",
    "open_source",
    "research",
    "agents",
    "infrastructure",
    "product_updates",
    "community",
]

SECTION_LABELS = {
    "model_release": "模型发布",
    "open_source": "开源项目",
    "research": "论文精选",
    "agents": "Agent 工作流",
    "infrastructure": "基础设施",
    "product_updates": "产品动态",
    "community": "社区热议",
}

SECTION_KEYWORDS = {
    "model_release": {
        "model",
        "release",
        "launch",
        "launched",
        "announced",
        "announce",
        "ships",
        "ship",
        "unveil",
        "new model",
        "weights",
        "checkpoint",
        "llama",
        "gpt",
        "claude",
        "gemini",
        "mistral",
    },
    "open_source": {
        "github",
        "repo",
        "repository",
        "open source",
        "open-source",
        "library",
        "toolkit",
        "framework",
        "sdk",
        "runtime",
        "project",
        "huggingface",
    },
    "research": {
        "paper",
        "research",
        "arxiv",
        "benchmark",
        "evaluation",
        "reasoning",
        "dataset",
        "sota",
        "benchmarking",
        "eval",
    },
    "agents": {
        "agent",
        "agents",
        "workflow",
        "orchestration",
        "planning",
        "tool use",
        "tool-use",
        "multi agent",
        "multi-agent",
    },
    "infrastructure": {
        "inference",
        "serving",
        "runtime",
        "deployment",
        "infra",
        "gpu",
        "throughput",
        "latency",
        "vllm",
        "tensor",
        "kernel",
        "stack",
    },
    "product_updates": {
        "blog",
        "news",
        "product",
        "api",
        "platform",
        "feature",
        "update",
        "roadmap",
        "release note",
        "release notes",
    },
}


def get_section_label(section_slug: str) -> str:
    return SECTION_LABELS.get(section_slug, section_slug.replace("_", " ").title())


def infer_sections_from_signals(
    *,
    title: str,
    summary: str = "",
    tags: Sequence[str] | None = None,
    keywords: Sequence[str] | None = None,
    source_hints: Sequence[str] | None = None,
) -> tuple[str, list[str]]:
    normalized_tags = [str(tag).strip().lower() for tag in tags or [] if str(tag).strip()]
    normalized_keywords = [str(keyword).strip().lower() for keyword in keywords or [] if str(keyword).strip()]
    normalized_sources = [str(hint).strip().lower() for hint in source_hints or [] if str(hint).strip()]
    haystack_parts = [title, summary, *normalized_tags, *normalized_keywords, *normalized_sources]
    haystack = " ".join(part.lower() for part in haystack_parts if part)

    scores = {section: 0.0 for section in SECTION_ORDER}

    for section, keywords_set in SECTION_KEYWORDS.items():
        for keyword in keywords_set:
            if keyword in haystack:
                scores[section] += 1.0

    if any("github.com" in hint or "huggingface.co" in hint for hint in normalized_sources):
        scores["open_source"] += 2.0
    if any("arxiv.org" in hint or "paperswithcode.com" in hint for hint in normalized_sources):
        scores["research"] += 2.0
    if any(hint.endswith("-blog") or "/blog" in hint or "/news" in hint for hint in normalized_sources + normalized_tags):
        scores["product_updates"] += 1.5
    if "agent" in haystack or "agents" in haystack:
        scores["agents"] += 1.5
    if "inference" in haystack or "runtime" in haystack:
        scores["infrastructure"] += 1.0
    if any(token in haystack for token in ("model", "weights", "checkpoint")) and any(
        token in haystack for token in ("release", "launch", "ships", "announce", "announced")
    ):
        scores["model_release"] += 2.0

    ranked_sections = [
        section
        for section, score in sorted(
            scores.items(),
            key=lambda item: (-item[1], SECTION_ORDER.index(item[0])),
        )
        if score > 0
    ]

    if not ranked_sections:
        return "community", ["community"]

    primary_section = ranked_sections[0]
    sections = ranked_sections[:3]
    if primary_section not in sections:
        sections.insert(0, primary_section)

    return primary_section, sections