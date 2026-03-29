from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fetchnews.schemas import NormalizedItem, RawIngestedItem


TRACKING_KEYS = {"fbclid", "gclid", "ref", "source"}
TRACKING_PREFIXES = ("utm_",)
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "into",
    "new",
    "of",
    "on",
    "the",
    "to",
    "with",
}
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
NON_WORD_PATTERN = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in TRACKING_KEYS or any(key.startswith(prefix) for prefix in TRACKING_PREFIXES):
            continue
        query_items.append((key, value))

    normalized_query = urlencode(query_items)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, normalized_query, ""))


def normalize_title(title: str) -> str:
    cleaned = NON_WORD_PATTERN.sub(" ", title.lower())
    tokens = [token for token in cleaned.split() if token and token not in STOPWORDS]
    return " ".join(tokens)


def normalize_raw_item(
    item: RawIngestedItem,
    *,
    source_priority: str = "P2",
    source_config: dict | None = None,
) -> NormalizedItem:
    normalized_title = normalize_title(item.title)
    keywords = _extract_keywords(normalized_title)
    tags = _extract_tags(item, keywords)
    content = " ".join(item.content.split())
    summary = content[:240] or item.title
    published_at = _ensure_utc(item.published_at)
    metadata = dict(item.metadata)
    metadata.update(_build_source_quality_metadata(item, normalized_title, source_config or {}))
    return NormalizedItem(
        source_slug=item.source_slug,
        source_priority=source_priority,
        external_id=item.external_id,
        canonical_url=canonicalize_url(item.url),
        title=item.title,
        normalized_title=normalized_title,
        author=item.author,
        published_at=published_at,
        summary=summary,
        content=item.content,
        language=_detect_language(item.title, item.content),
        tags=tags,
        keywords=keywords,
        metadata=metadata,
    )


def _extract_keywords(normalized_title: str) -> list[str]:
    keywords: list[str] = []
    for token in normalized_title.split():
        if len(token) <= 2:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords[:6]


def _extract_tags(item: RawIngestedItem, keywords: list[str]) -> list[str]:
    values: list[str] = [item.source_slug]
    metadata_tags = item.metadata.get("tags")
    if isinstance(metadata_tags, list):
        values.extend(str(tag).strip() for tag in metadata_tags if str(tag).strip())

    category = item.metadata.get("category")
    if isinstance(category, str) and category.strip():
        values.append(category.strip())

    values.extend(keywords[:2])
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen[:8]


def _build_source_quality_metadata(item: RawIngestedItem, normalized_title: str, source_config: dict) -> dict:
    combined_text = f"{normalized_title} {item.content.lower()}"
    blacklist_keywords = _normalize_quality_keywords(source_config.get("blacklist_title_keywords"))
    demote_keywords = _normalize_quality_keywords(source_config.get("demote_title_keywords"))

    quality_flags: list[str] = []
    if any(keyword in combined_text for keyword in blacklist_keywords):
        quality_flags.append("blacklisted_match")
    if any(keyword in combined_text for keyword in demote_keywords):
        quality_flags.append("demoted_match")

    blocked = bool(source_config.get("blacklisted", False) or "blacklisted_match" in quality_flags)
    return {
        "source_trust_score": _coerce_float(source_config.get("trust_score")),
        "source_score_multiplier": _coerce_float(source_config.get("score_multiplier"), 1.0),
        "source_quality_flags": quality_flags,
        "source_blocked": blocked,
    }


def _normalize_quality_keywords(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        keyword = str(item).strip().lower()
        if keyword:
            normalized.append(keyword)
    return normalized


def _coerce_float(value: object, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return fallback


def _detect_language(title: str, content: str) -> str:
    text = f"{title} {content}"
    if CJK_PATTERN.search(text):
        return "zh"
    if any(character.isalpha() for character in text):
        return "en"
    return "unknown"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)