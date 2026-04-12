from datetime import UTC, datetime

import httpx
import pytest

from fetchnews.models import Source
from fetchnews.sources.real_connectors import (
    FetchedSourceBatch,
    GitHubReleasesConnector,
    HuggingFacePapersConnector,
    PapersWithCodeConnector,
)


def test_github_connector_returns_incremental_cursor_and_snapshots() -> None:
    source = Source(
        slug="github-openai-releases",
        label="GitHub OpenAI Releases",
        platform="github",
        priority="P0",
        kind="api",
        enabled=True,
        config={
            "url": "https://api.github.com/repos/openai/openai-python/releases",
            "fixture_releases": [
                {
                    "id": 101,
                    "tag_name": "v1.2.3",
                    "name": "OpenAI Python v1.2.3",
                    "html_url": "https://github.com/openai/openai-python/releases/tag/v1.2.3",
                    "published_at": "2026-04-04T09:00:00Z",
                    "author": {"login": "openai"},
                    "body": "Release notes for the OpenAI Python SDK.",
                }
            ],
            "fixture_next_cursor": "github-cursor-2",
        },
    )

    result = GitHubReleasesConnector().fetch(source)

    assert isinstance(result, FetchedSourceBatch)
    assert result.next_cursor == "github-cursor-2"
    assert result.items[0].metadata["snapshot"]["tag_name"] == "v1.2.3"
    assert result.items[0].metadata["snapshot"]["id"] == 101


def test_huggingface_connector_returns_incremental_cursor_and_snapshots() -> None:
    source = Source(
        slug="hf-daily",
        label="Hugging Face Daily",
        platform="huggingface",
        priority="P1",
        kind="html",
        enabled=True,
        config={
            "url": "https://huggingface.co/papers",
            "fixture_entries": [
                {
                    "id": "hf-paper-1",
                    "title": "Agent planning benchmark reaches Hugging Face Papers",
                    "url": "https://huggingface.co/papers/agent-planning-benchmark",
                    "author": "Hugging Face",
                    "published_at": "2026-04-04T10:00:00Z",
                    "summary": "A benchmark summary appears on Hugging Face Papers.",
                    "upvotes": 320,
                }
            ],
            "fixture_next_cursor": "hf-cursor-2",
        },
    )

    result = HuggingFacePapersConnector().fetch(source)

    assert isinstance(result, FetchedSourceBatch)
    assert result.next_cursor == "hf-cursor-2"
    assert result.items[0].metadata["snapshot"]["id"] == "hf-paper-1"
    assert result.items[0].metadata["snapshot"]["upvotes"] == 320


def test_paperswithcode_connector_returns_incremental_cursor_and_snapshots() -> None:
    source = Source(
        slug="paperswithcode-latest",
        label="Papers with Code Latest",
        platform="paperswithcode",
        priority="P1",
        kind="api",
        enabled=True,
        config={
            "url": "https://paperswithcode.com/api/v1/papers",
            "fixture_papers": [
                {
                    "id": "pwc-1",
                    "title": "Reasoning benchmark tops Papers with Code",
                    "url": "https://paperswithcode.com/paper/reasoning-benchmark",
                    "published_at": "2026-04-04T11:00:00Z",
                    "authors": ["Alice", "Bob"],
                    "abstract": "A reasoning benchmark appears on Papers with Code.",
                }
            ],
            "fixture_next_cursor": "pwc-cursor-2",
        },
    )

    result = PapersWithCodeConnector().fetch(source)

    assert isinstance(result, FetchedSourceBatch)
    assert result.next_cursor == "pwc-cursor-2"
    assert result.items[0].published_at == datetime(2026, 4, 4, 11, 0, tzinfo=UTC)
    assert result.items[0].metadata["snapshot"]["id"] == "pwc-1"


def test_github_connector_live_fetch_filters_items_using_incremental_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubResponse:
        headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "id": 201,
                    "tag_name": "v1.2.4",
                    "name": "OpenAI Python v1.2.4",
                    "html_url": "https://github.com/openai/openai-python/releases/tag/v1.2.4",
                    "published_at": "2026-04-04T09:00:00Z",
                    "author": {"login": "openai"},
                    "body": "Older release that should be skipped.",
                },
                {
                    "id": 202,
                    "tag_name": "v1.2.5",
                    "name": "OpenAI Python v1.2.5",
                    "html_url": "https://github.com/openai/openai-python/releases/tag/v1.2.5",
                    "published_at": "2026-04-04T10:00:00Z",
                    "author": {"login": "openai"},
                    "body": "Newer release that should be ingested.",
                },
            ]

    source = Source(
        slug="github-openai-releases",
        label="GitHub OpenAI Releases",
        platform="github",
        priority="P0",
        kind="api",
        enabled=True,
        config={
            "url": "https://api.github.com/repos/openai/openai-python/releases",
        },
        incremental_cursor="2026-04-04T09:30:00+00:00",
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", lambda *args, **kwargs: StubResponse())

    result = GitHubReleasesConnector().fetch(source)

    assert len(result.items) == 1
    assert result.items[0].external_id == "202"
    assert result.next_cursor == "2026-04-04T10:00:00+00:00"


def test_github_connector_uses_auth_header_when_token_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return []

    def fake_get(url: str, *, timeout: float, headers: dict[str, str]) -> StubResponse:
        captured["url"] = url
        captured["timeout"] = timeout
        captured["headers"] = headers
        return StubResponse()

    source = Source(
        slug="github-openai-releases",
        label="GitHub OpenAI Releases",
        platform="github",
        priority="P0",
        kind="api",
        enabled=True,
        config={
            "url": "https://api.github.com/repos/openai/openai-python/releases",
            "auth_token": "gh-token",
        },
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", fake_get)

    GitHubReleasesConnector().fetch(source)

    assert captured["url"] == "https://api.github.com/repos/openai/openai-python/releases"
    assert captured["timeout"] == 10.0
    assert captured["headers"] == {
        "User-Agent": "FetchNews/0.1",
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer gh-token",
    }


def test_github_connector_live_fetch_uses_mock_transport_and_github_accept_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json=[
                {
                    "id": 301,
                    "tag_name": "v2.0.0",
                    "name": "OpenAI Python v2.0.0",
                    "html_url": "https://github.com/openai/openai-python/releases/tag/v2.0.0",
                    "published_at": "2026-04-04T12:00:00Z",
                    "author": {"login": "openai"},
                    "body": "Major release.",
                }
            ],
            request=request,
        )

    transport = httpx.MockTransport(handler)

    def fake_get(url: str, *, timeout: float, headers: dict[str, str]) -> httpx.Response:
        with httpx.Client(transport=transport, timeout=timeout, headers=headers) as client:
            return client.get(url)

    source = Source(
        slug="github-openai-releases",
        label="GitHub OpenAI Releases",
        platform="github",
        priority="P0",
        kind="api",
        enabled=True,
        config={"url": "https://api.github.com/repos/openai/openai-python/releases"},
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", fake_get)

    result = GitHubReleasesConnector().fetch(source)

    assert len(result.items) == 1
    headers = captured["headers"]
    assert headers["host"] == "api.github.com"
    assert headers["accept"] == "application/vnd.github+json"
    assert headers["user-agent"] == "FetchNews/0.1"


def test_huggingface_connector_falls_back_to_anchor_scan_when_cards_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        @property
        def text(self) -> str:
            return """
            <main>
              <div class="paper-link"><a href="/papers/hf-paper-9">Paper 9</a></div>
            </main>
            """

    source = Source(
        slug="hf-daily",
        label="Hugging Face Daily",
        platform="huggingface",
        priority="P1",
        kind="html",
        enabled=True,
        config={"url": "https://huggingface.co/papers"},
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", lambda *args, **kwargs: StubResponse())

    result = HuggingFacePapersConnector().fetch(source)

    assert len(result.items) == 1
    assert result.items[0].external_id == "/papers/hf-paper-9"
    assert result.next_cursor == "/papers/hf-paper-9"


def test_paperswithcode_connector_prefers_api_next_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "id": "pwc-2",
                        "title": "Fresh paper",
                        "url": "https://paperswithcode.com/paper/fresh-paper",
                        "published_at": "2026-04-04T12:00:00Z",
                        "authors": ["Alice"],
                        "abstract": "Fresh abstract.",
                    }
                ],
                "next": "https://paperswithcode.com/api/v1/papers?page=2",
            }

    source = Source(
        slug="paperswithcode-latest",
        label="Papers with Code Latest",
        platform="paperswithcode",
        priority="P1",
        kind="api",
        enabled=True,
        config={"url": "https://paperswithcode.com/api/v1/papers"},
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", lambda *args, **kwargs: StubResponse())

    result = PapersWithCodeConnector().fetch(source)

    assert len(result.items) == 1
    assert result.next_cursor == "https://paperswithcode.com/api/v1/papers?page=2"

def test_huggingface_connector_falls_back_to_full_page_when_cursor_rolled_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        @property
        def text(self) -> str:
            return """
            <main>
              <article><a href="/papers/hf-paper-3">Paper 3</a></article>
              <article><a href="/papers/hf-paper-2">Paper 2</a></article>
            </main>
            """

    source = Source(
        slug="hf-daily",
        label="Hugging Face Daily",
        platform="huggingface",
        priority="P1",
        kind="html",
        enabled=True,
        config={"url": "https://huggingface.co/papers"},
        incremental_cursor="/papers/hf-paper-1",
    )

    monkeypatch.setattr("fetchnews.sources.real_connectors.httpx.get", lambda *args, **kwargs: StubResponse())

    result = HuggingFacePapersConnector().fetch(source)

    assert [item.external_id for item in result.items] == [
        "/papers/hf-paper-3",
        "/papers/hf-paper-2",
    ]
    assert result.next_cursor == "/papers/hf-paper-3"
    for item in result.items:
        assert item.metadata["published_at_is_synthetic"] is True
        assert "fetched_at" in item.metadata
