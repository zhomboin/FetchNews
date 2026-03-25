from collections import defaultdict
from hashlib import sha1

from fetchnews.schemas import NormalizedItem, StoryCandidate


def _token_signature(title: str) -> frozenset[str]:
    return frozenset(token for token in title.split() if len(token) > 2)


def cluster_items(items: list[NormalizedItem]) -> list[StoryCandidate]:
    groups: dict[frozenset[str], list[NormalizedItem]] = defaultdict(list)
    for item in items:
        groups[_token_signature(item.normalized_title)].append(item)

    stories: list[StoryCandidate] = []
    for signature, grouped_items in groups.items():
        sorted_items = sorted(grouped_items, key=lambda current: current.published_at)
        first = sorted_items[0]
        story_key = sha1("|".join(sorted(signature)).encode("utf-8")).hexdigest()[:12]
        stories.append(
            StoryCandidate(
                story_key=story_key,
                cluster_title=first.title,
                summary=first.summary,
                highlights=[f"聚合了 {len(sorted_items)} 条相关来源"],
                source_links=[item.canonical_url for item in sorted_items],
                tags=[first.source_slug],
                risk_flags=[],
                score=float(len(sorted_items)) * 5.0,
                item_count=len(sorted_items),
                first_seen_at=sorted_items[0].published_at,
                last_seen_at=sorted_items[-1].published_at,
            )
        )

    return stories
