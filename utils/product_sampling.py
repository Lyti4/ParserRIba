"""Product-card sampling helpers for visual smoke diagnostics."""

from __future__ import annotations

from typing import Any

from loguru import logger


async def query_first_text(root: Any, selectors: list[str]) -> str:
    """Return text from the first matching selector."""
    for selector in selectors:
        try:
            element = await root.query_selector(selector)
            if element:
                text = await element.inner_text()
                if text.strip():
                    return text.strip()
        except Exception as exc:
            logger.debug("Selector failed: {} ({})", selector, exc)
    return ""


async def query_first_attribute(root: Any, selectors: list[str], attr: str) -> str:
    """Return attribute from the first matching selector."""
    for selector in selectors:
        try:
            element = await root.query_selector(selector)
            if element:
                value = await element.get_attribute(attr)
                if value:
                    return value
        except Exception as exc:
            logger.debug("Selector failed: {} ({})", selector, exc)
    return ""


async def find_cards(page: Any, selectors: list[str]) -> list[Any]:
    """Find product cards using configured selectors."""
    for selector in selectors:
        try:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Product cards found by selector '{}': {}", selector, len(cards))
                return cards
        except Exception as exc:
            logger.debug("Card selector failed: {} ({})", selector, exc)
    return []


async def extract_sample_products(
    cards: list[Any],
    name_selectors: list[str],
    price_selectors: list[str],
    link_selectors: list[str],
    *,
    base_url: str = "https://5ka.ru",
    limit: int = 10,
) -> list[dict[str, str]]:
    """Extract a small product sample from rendered cards."""
    products: list[dict[str, str]] = []
    for index, card in enumerate(cards[:limit], start=1):
        name = await query_first_text(card, name_selectors)
        price = await query_first_text(card, price_selectors)
        link = await query_first_attribute(card, link_selectors, "href")
        if link and link.startswith("/"):
            link = f"{base_url}{link}"
        if name or price:
            products.append({"index": str(index), "name": name, "price": price, "link": link})
    return products
