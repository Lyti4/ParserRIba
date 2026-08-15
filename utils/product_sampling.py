"""Product-card sampling helpers for visual smoke diagnostics."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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
            logger.debug("Selector failed: %s (%s)", selector, exc)
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
            logger.debug("Selector failed: %s (%s)", selector, exc)
    return ""


async def find_cards(page: Any, selectors: list[str]) -> list[Any]:
    """Find product cards using configured selectors."""
    for selector in selectors:
        try:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Product cards found by selector '%s': %s", selector, len(cards))
                return cards
        except Exception as exc:
            logger.debug("Card selector failed: %s (%s)", selector, exc)
    return []


_RUBLE_PRICE_RE = re.compile(r"(\d{1,3}(?:[\s\u00a0\u202f]\d{3})*(?:[,.]\d{2})?)\s*₽")
_WHOLE_PRICE_RE = re.compile(r"^\d{1,3}(?:[\s\u00a0\u202f]\d{3})*$")
_FRACTION_PRICE_RE = re.compile(r"^\d{2}$")


def extract_ruble_price(card_text: str) -> str:
    """Return an explicit RUB price without treating unrelated numbers as prices."""
    lines = [" ".join(line.split()) for line in card_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        direct = _RUBLE_PRICE_RE.search(line)
        if direct:
            return f"{' '.join(direct.group(1).split())} ₽"
        if "₽" not in line:
            continue
        if index >= 2 and _FRACTION_PRICE_RE.fullmatch(lines[index - 1]):
            whole = lines[index - 2]
            if _WHOLE_PRICE_RE.fullmatch(whole):
                return f"{' '.join(whole.split())},{lines[index - 1]} ₽"
        if index >= 1 and _WHOLE_PRICE_RE.fullmatch(lines[index - 1]):
            return f"{' '.join(lines[index - 1].split())} ₽"
    return ""


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
        image_name = (await query_first_attribute(card, ["img[alt]"], "alt")).strip()
        name = image_name or await query_first_text(card, name_selectors)
        price = await query_first_text(card, price_selectors)
        if not price:
            try:
                price = extract_ruble_price(await card.inner_text())
            except Exception:
                price = ""
        link = await query_first_attribute(card, link_selectors, "href")
        if link and link.startswith("/"):
            link = f"{base_url}{link}"
        if name or price:
            products.append({"index": str(index), "name": name, "price": price, "link": link})
    return products
