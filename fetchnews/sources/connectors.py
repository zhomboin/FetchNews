from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urljoin

import feedparser
import httpx
from selectolax.parser import HTMLParser

from fetchnews.models import Source
from fetchnews.schemas import RawIngestedItem


class SourceConnector(Protocol):
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        ...


class RssConnector:
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        url = _required_source_url(source)
        parsed = feedparser.parse(url)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise RuntimeError(f"Unable to parse feed for {source.slug}")

        items: list[RawIngestedItem] = []
        for entry in parsed.entries:
            link = entry.get("link") or url
            content_parts = []
            if entry.get("summary"):
                content_parts.append(entry["summary"])
            for content in entry.get("content", []):
                value = content.get("value")
                if value:
                    content_parts.append(value)
            tags = [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")]
            items.append(
                RawIngestedItem(
                    source_slug=source.slug,
                    external_id=entry.get("id") or entry.get("guid") or link,
                    title=entry.get("title") or link,
                    url=link,
                    author=entry.get("author"),
                    published_at=_coerce_datetime(entry.get("published") or entry.get("updated")),
                    content="\n\n".join(content_parts) or entry.get("title") or link,
                    metadata={"feed_title": parsed.feed.get("title"), "tags": tags},
                )
            )
        return items


class GitHubTrendingConnector:
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        url = _required_source_url(source)
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "FetchNews/0.1"},
        )
        response.raise_for_status()

        root = HTMLParser(response.text)
        items: list[RawIngestedItem] = []
        for article in root.css("article.Box-row"):
            anchor = article.css_first("h2 a")
            if anchor is None:
                continue
            href = anchor.attributes.get("href", "")
            repo_name = " ".join(anchor.text().split()).replace(" / ", "/").replace(" ", "")
            summary_node = article.css_first("p")
            stars_node = article.css_first("a[href$='/stargazers']")
            summary = summary_node.text(strip=True) if summary_node is not None else repo_name
            items.append(
                RawIngestedItem(
                    source_slug=source.slug,
                    external_id=repo_name or href or f"repo-{len(items) + 1}",
                    title=f"{repo_name} trends on GitHub",
                    url=urljoin("https://github.com", href) if href else url,
                    author=repo_name.split("/", 1)[0] if "/" in repo_name else None,
                    published_at=datetime.now(UTC),
                    content=summary,
                    metadata={
                        "repository": repo_name,
                        "stars": _parse_count(stars_node.text(strip=True)) if stars_node is not None else None,
                    },
                )
            )
        return items


class XAllowlistConnector:
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        static_items = source.config.get("static_items", [])
        if static_items:
            return [RawIngestedItem.model_validate(item) for item in static_items]
        raise RuntimeError("X allowlist connector is not configured")


def build_default_connector_registry() -> dict[str, SourceConnector]:
    rss_connector = RssConnector()
    return {
        "github": GitHubTrendingConnector(),
        "arxiv": rss_connector,
        "rss": rss_connector,
        "feed": rss_connector,
        "x": XAllowlistConnector(),
    }


def _required_source_url(source: Source) -> str:
    url = source.config.get("url")
    if not url:
        raise RuntimeError(f"Source {source.slug} is missing a configured url")
    return str(url)


def _coerce_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            parsed = None
        if parsed is not None:
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _parse_count(value: str) -> int | None:
    cleaned = value.replace(",", "").strip().lower()
    if not cleaned:
        return None
    multiplier = 1
    if cleaned.endswith("k"):
        multiplier = 1000
        cleaned = cleaned[:-1]
    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return None
