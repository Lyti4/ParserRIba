from __future__ import annotations

import pytest

from utils.catalog_tree_discovery.listing_validator import validate_listing_candidate


class _DummyResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class _DummyPage:
    def __init__(self, *, html: str, status: int = 200, final_url: str | None = None) -> None:
        self._html = html
        self._status = status
        self.url = final_url or "https://example.test/current"
        self.goto_calls: list[tuple[str, str]] = []
        self.wait_calls: list[int] = []

    async def goto(self, url: str, wait_until: str = "load") -> _DummyResponse:
        self.goto_calls.append((url, wait_until))
        return _DummyResponse(self._status)

    async def wait_for_timeout(self, wait_ms: int) -> None:
        self.wait_calls.append(wait_ms)

    async def content(self) -> str:
        return self._html


@pytest.mark.asyncio
async def test_validate_listing_candidate_classifies_listing_surface() -> None:
    page = _DummyPage(
        html='<html><body><a href="/products/fish-1">Fish</a></body></html>',
        final_url="https://example.test/catalog/fish",
    )

    result = await validate_listing_candidate(page, "https://example.test/catalog/fish", wait_ms=1200)

    assert result.surface_type == "product_listing"
    assert result.validation_state == "listing_valid"
    assert page.goto_calls == [("https://example.test/catalog/fish", "domcontentloaded")]
    assert page.wait_calls == [1200]


@pytest.mark.asyncio
async def test_validate_listing_candidate_uses_default_wait_and_classifies_category_tree() -> None:
    page = _DummyPage(
        html='<html><body><a href="/catalog/seafood">Seafood</a></body></html>',
        final_url="https://example.test/",
    )

    result = await validate_listing_candidate(page, "https://example.test/")

    assert result.surface_type == "category_tree"
    assert result.validation_state == "menu_only"
    assert page.wait_calls == [2500]


@pytest.mark.asyncio
async def test_validate_listing_candidate_supports_zero_wait() -> None:
    page = _DummyPage(
        html="<html><body>captcha challenge</body></html>",
        status=403,
        final_url="https://example.test/challenge",
    )

    result = await validate_listing_candidate(page, "https://example.test/challenge", wait_ms=0)

    assert result.surface_type == "challenge"
    assert result.validation_state == "challenge"
    assert page.wait_calls == []
