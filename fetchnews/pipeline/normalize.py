from urllib.parse import urlsplit, urlunsplit

from fetchnews.schemas import NormalizedItem, RawIngestedItem


TRACKING_PREFIXES = ("utm_", "ref", "source")


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = "&".join(
        item
        for item in parts.query.split("&")
        if item and not any(item.startswith(prefix + "=") for prefix in TRACKING_PREFIXES)
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, query, ""))


def normalize_title(title: str) -> str:
    normalized = " ".join(title.lower().replace("-", " ").split())
    return normalized.replace(" an ", " ").replace(" a ", " ")


def normalize_raw_item(item: RawIngestedItem) -> NormalizedItem:
    return NormalizedItem(
        source_slug=item.source_slug,
        external_id=item.external_id,
        canonical_url=canonicalize_url(item.url),
        title=item.title,
        normalized_title=normalize_title(item.title),
        author=item.author,
        published_at=item.published_at,
        summary=item.content[:240],
        content=item.content,
        metadata=item.metadata,
    )
