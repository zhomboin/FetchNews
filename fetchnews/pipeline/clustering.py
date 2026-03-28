from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1

from fetchnews.schemas import NormalizedItem, StoryCandidate


PRIORITY_SCORES = {"P0": 8.0, "P1": 5.0, "P2": 2.0}


def cluster_items(items: list[NormalizedItem]) -> list[StoryCandidate]:
    clusters: list[list[NormalizedItem]] = []

    for item in sorted(items, key=lambda current: (current.published_at, current.canonical_url)):
        cluster = _find_cluster(item, clusters)
        if cluster is None:
            clusters.append([item])
        else:
            cluster.append(item)

    return [_build_story_candidate(cluster) for cluster in clusters]


def _find_cluster(item: NormalizedItem, clusters: list[list[NormalizedItem]]) -> list[NormalizedItem] | None:
    for cluster in clusters:
        if any(_should_merge(item, existing) for existing in cluster):
            return cluster
    return None


def _should_merge(left: NormalizedItem, right: NormalizedItem) -> bool:
    if left.canonical_url == right.canonical_url:
        return True
    if left.normalized_title == right.normalized_title:
        return True

    left_tokens = _token_signature(left.normalized_title)
    right_tokens = _token_signature(right.normalized_title)
    if not left_tokens or not right_tokens:
        return False

    overlap = left_tokens & right_tokens
    union = left_tokens | right_tokens
    similarity = len(overlap) / len(union)
    return similarity >= 0.6 or (len(overlap) >= 3 and (left_tokens <= right_tokens or right_tokens <= left_tokens))


def _token_signature(title: str) -> frozenset[str]:
    return frozenset(token for token in title.split() if len(token) > 2)


def _build_story_candidate(cluster: list[NormalizedItem]) -> StoryCandidate:
    sorted_items = sorted(cluster, key=lambda current: (current.published_at, current.canonical_url))
    representative = sorted_items[0]
    unique_sources = sorted({item.source_slug for item in sorted_items})
    unique_links = sorted({item.canonical_url for item in sorted_items})
    merged_tags = _merge_tags(sorted_items)
    risk_flags = _build_risk_flags(sorted_items)
    highlights = [f"聚合 {len(sorted_items)} 条相关来源"]
    if len(unique_sources) > 1:
        highlights.append(f"覆盖 {len(unique_sources)} 个来源")
    if representative.keywords:
        highlights.append(f"关键词：{' / '.join(representative.keywords[:3])}")

    story_key = sha1(f"{representative.normalized_title}|{representative.canonical_url}".encode("utf-8")).hexdigest()[:12]
    return StoryCandidate(
        story_key=story_key,
        cluster_title=representative.title,
        summary=representative.summary,
        highlights=highlights,
        source_links=unique_links,
        tags=merged_tags,
        risk_flags=risk_flags,
        score=_score_story(sorted_items),
        item_count=len(sorted_items),
        first_seen_at=sorted_items[0].published_at,
        last_seen_at=sorted_items[-1].published_at,
    )


def _merge_tags(items: list[NormalizedItem]) -> list[str]:
    tags: list[str] = []
    for item in items:
        for tag in [*item.tags, *item.keywords]:
            if tag not in tags:
                tags.append(tag)
    return tags[:8]


def _build_risk_flags(items: list[NormalizedItem]) -> list[str]:
    priorities = {item.source_priority for item in items}
    if "P0" not in priorities:
        return ["secondary_sources_only"]
    return []


def _score_story(items: list[NormalizedItem]) -> float:
    unique_sources = {item.source_slug: item for item in items}.values()
    latest_seen = max(item.published_at for item in items)
    now = datetime.now(UTC)
    hours_since_latest = max((now - latest_seen).total_seconds() / 3600, 0)

    priority_score = sum(PRIORITY_SCORES.get(item.source_priority, 1.0) for item in unique_sources)
    trust_score = sum(_source_trust_score(item.source_slug) for item in unique_sources)
    volume_score = min(len(items), 4) * 1.5
    freshness_score = max(0.0, 10.0 - min(hours_since_latest, 72.0) / 8.0)
    diversity_bonus = min(len(list(unique_sources)), 3) * 1.2
    secondary_penalty = 5.0 if all(item.source_priority != "P0" for item in unique_sources) else 0.0

    return round(priority_score + trust_score + volume_score + freshness_score + diversity_bonus - secondary_penalty, 2)


def _source_trust_score(source_slug: str) -> float:
    if source_slug.endswith("-blog"):
        return 6.5
    if source_slug.startswith("github"):
        return 5.5
    if source_slug.startswith("arxiv"):
        return 5.0
    if source_slug.startswith("hf"):
        return 4.0
    if source_slug.startswith("x-"):
        return 3.0
    if source_slug.startswith("reddit"):
        return 1.0
    return 1.5