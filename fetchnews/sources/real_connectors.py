from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from selectolax.parser import HTMLParser

from fetchnews.models import Source
from fetchnews.schemas import RawIngestedItem


@dataclass(slots=True)
class FetchedSourceBatch:
    items: list[RawIngestedItem]
    next_cursor: str | None = None


class GitHubReleasesConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        releases = source.config.get("fixture_releases")
        if releases is None:
            releases = self._fetch_releases(source)

        items = [
            RawIngestedItem(
                source_slug=source.slug,
                external_id=str(release.get("id") or release.get("tag_name") or release.get("html_url")),
                title=str(release.get("name") or release.get("tag_name") or "GitHub release"),
                url=str(release.get("html_url") or _required_source_url(source)),
                author=_coerce_author(release.get("author")),
                published_at=_coerce_datetime(release.get("published_at")),
                content=str(release.get("body") or release.get("name") or release.get("tag_name") or "GitHub release"),
                metadata={"snapshot": dict(release), "source_type": "github_release"},
            )
            for release in releases
        ]
        return FetchedSourceBatch(items=items, next_cursor=_coerce_cursor(source.config.get("fixture_next_cursor")))

    def _fetch_releases(self, source: Source) -> list[dict[str, Any]]:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers={"User-Agent": "FetchNews/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected GitHub releases payload for {source.slug}")
        return [dict(item) for item in payload]


class HuggingFacePapersConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        entries = source.config.get("fixture_entries")
        if entries is None:
            entries = self._fetch_entries(source)

        items = [
            RawIngestedItem(
                source_slug=source.slug,
                external_id=str(entry.get("id") or entry.get("url") or entry.get("title")),
                title=str(entry.get("title") or "Hugging Face paper"),
                url=str(entry.get("url") or _required_source_url(source)),
                author=str(entry.get("author") or "Hugging Face"),
                published_at=_coerce_datetime(entry.get("published_at")),
                content=str(entry.get("summary") or entry.get("title") or "Hugging Face paper"),
                metadata={"snapshot": dict(entry), "source_type": "huggingface_paper"},
            )
            for entry in entries
        ]
        return FetchedSourceBatch(items=items, next_cursor=_coerce_cursor(source.config.get("fixture_next_cursor")))

    def _fetch_entries(self, source: Source) -> list[dict[str, Any]]:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers={"User-Agent": "FetchNews/0.1"},
        )
        response.raise_for_status()
        root = HTMLParser(response.text)
        entries: list[dict[str, Any]] = []
        for card in root.css("article, section"):
            anchor = card.css_first("a")
            title = anchor.text(strip=True) if anchor is not None else ""
            href = anchor.attributes.get("href", "") if anchor is not None else ""
            if not title or not href:
                continue
            entries.append(
                {
                    "id": href,
                    "title": title,
                    "url": href if href.startswith("http") else f"https://huggingface.co{href}",
                    "summary": title,
                    "published_at": datetime.now(UTC).isoformat(),
                }
            )
        return entries


class PapersWithCodeConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        papers = source.config.get("fixture_papers")
        if papers is None:
            papers = self._fetch_papers(source)

        items = [
            RawIngestedItem(
                source_slug=source.slug,
                external_id=str(paper.get("id") or paper.get("url") or paper.get("title")),
                title=str(paper.get("title") or "Papers with Code paper"),
                url=str(paper.get("url") or _required_source_url(source)),
                author=", ".join(str(author) for author in paper.get("authors", [])) or None,
                published_at=_coerce_datetime(paper.get("published_at")),
                content=str(paper.get("abstract") or paper.get("title") or "Papers with Code paper"),
                metadata={"snapshot": dict(paper), "source_type": "paperswithcode_paper"},
            )
            for paper in papers
        ]
        return FetchedSourceBatch(items=items, next_cursor=_coerce_cursor(source.config.get("fixture_next_cursor")))

    def _fetch_papers(self, source: Source) -> list[dict[str, Any]]:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers={"User-Agent": "FetchNews/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            results = payload.get("results", [])
            if isinstance(results, list):
                return [dict(item) for item in results]
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        raise RuntimeError(f"Unexpected Papers with Code payload for {source.slug}")


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
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _coerce_author(value: object) -> str | None:
    if isinstance(value, dict):
        login = value.get("login")
        return str(login) if login else None
    if value is None:
        return None
    return str(value)


def _coerce_cursor(value: object) -> str | None:
    if value is None:
        return None
    cursor = str(value).strip()
    return cursor or None
