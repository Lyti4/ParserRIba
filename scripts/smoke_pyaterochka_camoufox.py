"""Smoke test for Pyaterochka parsing through AsyncCamoufox.

This script intentionally avoids the current parser inheritance layer because
it is being repaired separately. It validates the important path first:
Knowledge Base -> Camoufox browser -> Pyaterochka category page -> product cards.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.antibot import collect_page_diagnostics, wait_for_pyaterochka_challenge
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.kb_loader import KBLoader, SelectorConfig
from utils.smoke_report import write_smoke_report

OUTPUT_DIR = ROOT_DIR / "data"
DEFAULT_CATEGORY = "Рыба"
PROXY_ENV = "PARSER_PROXY"


def _split_selectors(config: SelectorConfig | None) -> list[str]:
    """Return individual CSS selectors from a KB selector config."""
    if not config or not config.css:
        return []
    return [item.strip() for item in config.css.split("|") if item.strip()]


async def _query_first_text(root: Any, selectors: list[str]) -> str:
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


async def _query_first_attribute(root: Any, selectors: list[str], attr: str) -> str:
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


async def _find_cards(page: Any, selectors: list[str]) -> list[Any]:
    """Find product cards using KB selectors."""
    for selector in selectors:
        try:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Product cards found by selector '{}': {}", selector, len(cards))
                return cards
        except Exception as exc:
            logger.debug("Card selector failed: {} ({})", selector, exc)
    return []


async def smoke_parse_pyaterochka(category_name: str = DEFAULT_CATEGORY) -> dict[str, Any]:
    """Open Pyaterochka category through Camoufox and collect a small sample."""
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")

    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    category_url = kb.categories.get(category_name)
    if not category_url:
        category_name, category_url = next(iter(kb.categories.items()))

    card_selectors = _split_selectors(kb.selectors.get("product_card"))
    name_selectors = _split_selectors(kb.selectors.get("product_name"))
    price_selectors = _split_selectors(kb.selectors.get("price_current"))
    link_selectors = _split_selectors(kb.selectors.get("product_link"))

    logger.info("Starting Camoufox for Pyaterochka smoke test")
    logger.info("Category: {} -> {}", category_name, category_url)

    launch_options = build_camoufox_options(
        headless=False if sys.platform == "win32" else "virtual",
        proxy_url=os.environ.get(PROXY_ENV),
        geoip=os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"},
        block_images=True,
        block_webgl=False,
        humanize=True,
    )

    async with AsyncCamoufox(
        **launch_options,
    ) as browser:
        page = await browser.new_page()
        if kb.headers.custom:
            await page.set_extra_http_headers(kb.headers.custom)
        navigation_error = ""
        response = None
        try:
            response = await page.goto(category_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            navigation_error = str(exc)
            logger.warning("Navigation failed: {}", exc)
        await page.wait_for_timeout(5_000)
        await wait_for_pyaterochka_challenge(page)

        for _ in range(4):
            await page.mouse.wheel(0, 900)
            await page.wait_for_timeout(1_000)

        await wait_for_pyaterochka_challenge(page)

        diagnostics = await collect_page_diagnostics(page, response)
        page_html = await page.content()
        screenshot_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.png"
        html_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.html"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page_html, encoding="utf-8")

        cards = await _find_cards(page, card_selectors)

        products: list[dict[str, str]] = []
        for index, card in enumerate(cards[:10], start=1):
            name = await _query_first_text(card, name_selectors)
            price = await _query_first_text(card, price_selectors)
            link = await _query_first_attribute(card, link_selectors, "href")
            if link and link.startswith("/"):
                link = f"https://5ka.ru{link}"
            if name or price:
                products.append(
                    {
                        "index": str(index),
                        "name": name,
                        "price": price,
                        "link": link,
                    }
                )

        result = {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": category_url,
            "http_status": diagnostics.status,
            "page_title": diagnostics.title,
            "final_url": diagnostics.final_url,
            "html_size": diagnostics.html_size,
            "blocked": diagnostics.blocked,
            "block_reason": diagnostics.reason,
            "navigation_error": navigation_error,
            "screenshot_path": str(screenshot_path),
            "html_path": str(html_path),
            "cards_found": len(cards),
            "products_sample": products,
            "parsed_at": datetime.now().isoformat(timespec="seconds"),
        }

    output_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.json"
    report_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.md"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_smoke_report(result, report_path)
    logger.info("Smoke result saved: {}", output_path)
    logger.info("Smoke report saved: {}", report_path)
    logger.info("Cards found: {}", result["cards_found"])
    for product in products[:5]:
        logger.info("{} | {} | {}", product["name"], product["price"], product["link"])
    return result


if __name__ == "__main__":
    asyncio.run(smoke_parse_pyaterochka())
