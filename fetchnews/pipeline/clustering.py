from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1

from fetchnews.pipeline.sections import infer_sections_from_signals
from fetchnews.schemas import NormalizedItem, StoryCandidate


PRIORITY_SCORES = {"P0": 8.0, "P1": 5.0, "P2": 2.0}


def cluster_items(
    items: list[NormalizedItem],
    *,
    section_feedback: dict[str, object] | None = None,
) -> list[StoryCandidate]:
    eligible_items = [item for item in items if not _is_blocked_item(item)]
    clusters: list[list[NormalizedItem]] = []

    for item in sorted(eligible_items, key=lambda current: (current.published_at, current.canonical_url)):
        cluster = _find_cluster(item, clusters)
        if cluster is None:
            clusters.append([item])
        else:
            cluster.append(item)

    feedback = section_feedback or {}
    return [_build_story_candidate(cluster, feedback) for cluster in clusters]


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


def _build_story_candidate(cluster: list[NormalizedItem], section_feedback: dict[str, object]) -> StoryCandidate:
    sorted_items = sorted(cluster, key=lambda current: (current.published_at, current.canonical_url))
    representative = sorted_items[0]
    unique_sources = sorted({item.source_slug for item in sorted_items})
    unique_links = sorted({item.canonical_url for item in sorted_items})
    merged_tags = _merge_tags(sorted_items)
    primary_section, sections = infer_sections_from_signals(
        title=representative.title,
        summary=representative.summary,
        tags=merged_tags,
        keywords=representative.keywords,
        source_hints=[representative.source_slug, *unique_links],
    )
    risk_flags = _build_risk_flags(sorted_items)
    highlights = [f"Aggregates {len(sorted_items)} related items"]
    if len(unique_sources) > 1:
        highlights.append(f"Covers {len(unique_sources)} distinct sources")
    if representative.keywords:
        highlights.append(f"Keywords: {' / '.join(representative.keywords[:3])}")

    score = _score_story(sorted_items)
    section_adjustment = section_feedback.get(primary_section)
    if section_adjustment is not None:
        boost = float(getattr(section_adjustment, "score_boost", 0.0))
        penalty = float(getattr(section_adjustment, "score_penalty", 0.0))
        score = round(max(score + boost - penalty, 0.0), 2)
        for flag in getattr(section_adjustment, "risk_flags", []):
            if flag not in risk_flags:
                risk_flags.append(flag)
        for note in getattr(section_adjustment, "highlights", []):
            if note not in highlights:
                highlights.append(str(note))
        if penalty > 0 and all("penalty" not in highlight.lower() for highlight in highlights):
            highlights.append(f"Section governance penalty: -{penalty:.1f}")

    story_key = sha1(f"{representative.normalized_title}|{representative.canonical_url}".encode("utf-8")).hexdigest()[:12]
    return StoryCandidate(
        story_key=story_key,
        cluster_title=representative.title,
        summary=representative.summary,
        highlights=highlights,
        source_links=unique_links,
        tags=merged_tags,
        risk_flags=risk_flags,
        score=score,
        item_count=len(sorted_items),
        first_seen_at=sorted_items[0].published_at,
        last_seen_at=sorted_items[-1].published_at,
        primary_section=primary_section,
        sections=sections,
    )


def _merge_tags(items: list[NormalizedItem]) -> list[str]:
    tags: list[str] = []
    for item in items:
        for tag in [*item.tags, *item.keywords]:
            if tag not in tags:
                tags.append(tag)
    return tags[:8]


def _build_risk_flags(items: list[NormalizedItem]) -> list[str]:
    flags: list[str] = []
    priorities = {item.source_priority for item in items}
    if "P0" not in priorities:
        flags.append("secondary_sources_only")
    if any(_is_demoted_item(item) for item in items):
        flags.append("demoted_source_signal")
    if any(_has_source_governance_flags(item) for item in items):
        flags.append("source_governance_watch")
    return flags


def _score_story(items: list[NormalizedItem]) -> float:
    unique_sources = {item.source_slug: item for item in items}.values()
    latest_seen = max(item.published_at for item in items)
    now = datetime.now(UTC)
    hours_since_latest = max((now - latest_seen).total_seconds() / 3600, 0)

    priority_score = sum(PRIORITY_SCORES.get(item.source_priority, 1.0) * _source_score_multiplier(item) for item in unique_sources)
    trust_score = sum(_source_trust_score(item) * _source_score_multiplier(item) for item in unique_sources)
    volume_score = min(len(items), 4) * 1.5
    freshness_score = max(0.0, 10.0 - min(hours_since_latest, 72.0) / 8.0)
    diversity_bonus = min(len(list(unique_sources)), 3) * 1.2
    demotion_penalty = sum(2.5 for item in unique_sources if _is_demoted_item(item))
    secondary_penalty = 5.0 if all(item.source_priority != "P0" for item in unique_sources) else 0.0
    governance_penalty = sum(_source_ranking_penalty(item) for item in unique_sources)

    return round(
        priority_score + trust_score + volume_score + freshness_score + diversity_bonus - demotion_penalty - secondary_penalty - governance_penalty,
        2,
    )


def _source_trust_score(item: NormalizedItem) -> float:
    metadata_value = item.metadata.get("source_trust_score")
    if isinstance(metadata_value, (int, float)):
        return float(metadata_value)

    source_slug = item.source_slug
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


def _source_score_multiplier(item: NormalizedItem) -> float:
    metadata_value = item.metadata.get("source_score_multiplier")
    if isinstance(metadata_value, (int, float)):
        return max(float(metadata_value), 0.0)
    return 1.0


def _source_ranking_penalty(item: NormalizedItem) -> float:
    feedback_signals = item.metadata.get("source_feedback_signals")
    if not isinstance(feedback_signals, dict):
        return 0.0
    penalty = feedback_signals.get("ranking_penalty")
    if isinstance(penalty, (int, float)):
        return float(penalty)
    return 0.0


def _is_blocked_item(item: NormalizedItem) -> bool:
    return bool(item.metadata.get("source_blocked"))


def _is_demoted_item(item: NormalizedItem) -> bool:
    quality_flags = item.metadata.get("source_quality_flags")
    if not isinstance(quality_flags, list):
        return False
    return "demoted_match" in {str(flag) for flag in quality_flags}


def _has_source_governance_flags(item: NormalizedItem) -> bool:
    governance_flags = item.metadata.get("source_governance_flags")
    return isinstance(governance_flags, list) and len(governance_flags) > 0