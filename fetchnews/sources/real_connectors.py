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


@dataclass(slots=True)
class _FetchedRecordPage:
    records: list[dict[str, Any]]
    next_cursor: str | None = None


class GitHubReleasesConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        releases = source.config.get("fixture_releases")
        next_cursor = _coerce_cursor(source.config.get("fixture_next_cursor"))
        if releases is None:
            releases = self._fetch_releases(source)
            releases, next_cursor = _filter_records_by_datetime(
                records=releases,
                cursor=source.incremental_cursor,
                field_name="published_at",
            )

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
        return FetchedSourceBatch(items=items, next_cursor=next_cursor)

    def _fetch_releases(self, source: Source) -> list[dict[str, Any]]:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers=_build_request_headers(source),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected GitHub releases payload for {source.slug}")
        return [dict(item) for item in payload]


class HuggingFacePapersConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        entries = source.config.get("fixture_entries")
        next_cursor = _coerce_cursor(source.config.get("fixture_next_cursor"))
        if entries is None:
            entries = self._fetch_entries(source)
            entries, next_cursor = _filter_records_by_id(
                records=entries,
                cursor=source.incremental_cursor,
                id_field="id",
            )

        items = [
            RawIngestedItem(
                source_slug=source.slug,
                external_id=str(entry.get("id") or entry.get("url") or entry.get("title")),
                title=str(entry.get("title") or "Hugging Face paper"),
                url=str(entry.get("url") or _required_source_url(source)),
                author=str(entry.get("author") or "Hugging Face"),
                published_at=_coerce_datetime(entry.get("published_at")),
                content=str(entry.get("summary") or entry.get("title") or "Hugging Face paper"),
                metadata=_build_huggingface_metadata(entry),
            )
            for entry in entries
        ]
        return FetchedSourceBatch(items=items, next_cursor=next_cursor)

    def _fetch_entries(self, source: Source) -> list[dict[str, Any]]:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers=_build_request_headers(source),
        )
        response.raise_for_status()
        root = HTMLParser(response.text)
        entries = _extract_huggingface_entries(root)
        if entries:
            return entries
        return _extract_huggingface_anchor_entries(root)


class PapersWithCodeConnector:
    def fetch(self, source: Source) -> FetchedSourceBatch:
        papers = source.config.get("fixture_papers")
        next_cursor = _coerce_cursor(source.config.get("fixture_next_cursor"))
        if papers is None:
            fetched_page = self._fetch_papers(source)
            filtered_papers, filtered_cursor = _filter_records_by_datetime(
                records=fetched_page.records,
                cursor=source.incremental_cursor,
                field_name="published_at",
            )
            papers = filtered_papers
            next_cursor = fetched_page.next_cursor or filtered_cursor

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
        return FetchedSourceBatch(items=items, next_cursor=next_cursor)

    def _fetch_papers(self, source: Source) -> _FetchedRecordPage:
        response = httpx.get(
            _required_source_url(source),
            timeout=10.0,
            headers=_build_request_headers(source),
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            results = payload.get("results", [])
            next_cursor = _coerce_cursor(payload.get("next"))
            if isinstance(results, list):
                return _FetchedRecordPage(records=[dict(item) for item in results], next_cursor=next_cursor)
        if isinstance(payload, list):
            return _FetchedRecordPage(records=[dict(item) for item in payload])
        raise RuntimeError(f"Unexpected Papers with Code payload for {source.slug}")


def _extract_huggingface_entries(root: HTMLParser) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for card in root.css("article, section"):
        anchor = card.css_first("a")
        title = anchor.text(strip=True) if anchor is not None else ""
        href = anchor.attributes.get("href", "") if anchor is not None else ""
        if not title or not href:
            continue
        entries.append(_build_huggingface_entry(title=title, href=href))
    return entries


def _extract_huggingface_anchor_entries(root: HTMLParser) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen_hrefs: set[str] = set()
    for anchor in root.css('main a[href*="/papers/"], a[href*="/papers/"]'):
        href = anchor.attributes.get("href", "")
        title = anchor.text(strip=True)
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        entries.append(_build_huggingface_entry(title=title or href, href=href))
    return entries


def _build_huggingface_entry(*, title: str, href: str) -> dict[str, Any]:
    fetched_at = datetime.now(UTC).isoformat()
    return {
        "id": href,
        "title": title,
        "url": href if href.startswith("http") else f"https://huggingface.co{href}",
        "summary": title,
        "published_at": fetched_at,
        "published_at_is_synthetic": True,
        "fetched_at": fetched_at,
    }


def _build_huggingface_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(entry)
    is_synthetic = bool(snapshot.pop("published_at_is_synthetic", False))
    fetched_at = str(snapshot.pop("fetched_at", None) or datetime.now(UTC).isoformat())
    return {
        "snapshot": snapshot,
        "source_type": "huggingface_paper",
        "fetched_at": fetched_at,
        "published_at_is_synthetic": is_synthetic,
    }


def _build_request_headers(source: Source) -> dict[str, str]:
    headers = {"User-Agent": "FetchNews/0.1"}
    if source.platform == "github" and source.kind == "api":
        headers["Accept"] = "application/vnd.github+json"
    auth_token = _coerce_cursor(source.config.get("auth_token"))
    if auth_token is not None:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


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


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _filter_records_by_datetime(
    *,
    records: list[dict[str, Any]],
    cursor: str | None,
    field_name: str,
) -> tuple[list[dict[str, Any]], str | None]:
    cursor_dt = _parse_datetime(cursor)
    latest_dt = cursor_dt
    filtered: list[dict[str, Any]] = []

    for record in records:
        record_dt = _parse_datetime(record.get(field_name))
        if record_dt is not None and (latest_dt is None or record_dt > latest_dt):
            latest_dt = record_dt
        if cursor_dt is not None and record_dt is not None and record_dt <= cursor_dt:
            continue
        filtered.append(record)

    next_cursor = latest_dt.isoformat() if latest_dt is not None else _coerce_cursor(cursor)
    return filtered, next_cursor


def _filter_records_by_id(
    *,
    records: list[dict[str, Any]],
    cursor: str | None,
    id_field: str,
) -> tuple[list[dict[str, Any]], str | None]:
    first_id = _coerce_cursor(records[0].get(id_field)) if records else _coerce_cursor(cursor)
    if cursor is None:
        return records, first_id

    filtered: list[dict[str, Any]] = []
    cursor_found = False
    for record in records:
        record_id = _coerce_cursor(record.get(id_field))
        if record_id == cursor:
            cursor_found = True
            break
        filtered.append(record)
    if cursor_found:
        return filtered, first_id
    return records, first_id


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
