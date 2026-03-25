from fetchnews.sources.catalog import DEFAULT_SOURCE_SPECS, priority_order


def test_default_catalog_contains_expected_p0_sources() -> None:
    names = {spec.slug for spec in DEFAULT_SOURCE_SPECS}
    assert "github-trending" in names
    assert "arxiv-cs-ai" in names
    assert "openai-blog" in names
    assert "x-allowlist" in names


def test_priority_order_places_p0_first() -> None:
    ordered = priority_order(DEFAULT_SOURCE_SPECS)
    assert ordered[0].priority == "P0"
    assert ordered[-1].priority in {"P1", "P2"}
