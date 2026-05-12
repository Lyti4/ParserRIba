"""Smoke test for Pyaterochka parsing through AsyncCamoufox.

This script intentionally avoids the current parser inheritance layer because
it is being repaired separately. It validates the important path first:
Knowledge Base -> Camoufox browser -> Pyaterochka category page -> product cards.
"""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.antibot import (
    classify_navigation_error,
    collect_page_diagnostics,
    wait_for_pyaterochka_challenge,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile, hover_product_cards
from utils.kb_loader import KBLoader, SelectorConfig
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url
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


async def _browser_external_ip(page: Any) -> str:
    """Return the external IP observed from inside the browser page."""
    try:
        value = await page.evaluate(
            """async () => {
                const response = await fetch("https://api.ipify.org?format=json", {
                    cache: "no-store"
                });
                const payload = await response.json();
                return payload.ip || "";
            }"""
        )
        return str(value or "")
    except Exception as exc:
        logger.warning("Browser IP check failed: {}", exc)
        return ""


def _build_network_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact network summary for smoke diagnostics."""
    status_counts: dict[str, int] = {}
    error_samples: list[dict[str, Any]] = []
    for event in events:
        status = event.get("status")
        status_key = str(status) if status is not None else "unknown"
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        if isinstance(status, int) and status >= 400 and len(error_samples) < 10:
            error_samples.append(event)
    return {
        "responses": len(events),
        "status_counts": status_counts,
        "error_samples": error_samples,
    }


async def smoke_parse_pyaterochka(
    category_name: str = DEFAULT_CATEGORY,
    attempts: int = 3,
    headless: bool | str | None = None,
    pause: bool = False,
    block_images: bool = True,
) -> dict[str, Any]:
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

    proxy_urls = load_proxy_urls(
        primary=os.environ.get(PROXY_ENV, ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    browser_headless = headless
    if browser_headless is None:
        browser_headless = False if sys.platform == "win32" else "virtual"

    final_result: dict[str, Any] | None = None
    attempt_results: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        proxy_url = choose_proxy_for_attempt(proxy_urls, attempt)
        if proxy_url:
            logger.info("Smoke attempt {} uses proxy {}", attempt, mask_proxy_url(proxy_url))
        else:
            logger.info("Smoke attempt {} runs without proxy", attempt)

        launch_options = build_camoufox_options(
            headless=browser_headless,
            proxy_url=proxy_url,
            geoip=geoip_enabled,
            block_images=block_images,
            block_webgl=False,
            humanize=True,
            fingerprint_os="windows",
        )
        try:
            final_result = await _run_smoke_attempt(
                kb=kb,
                category_name=category_name,
                category_url=category_url,
                launch_options=launch_options,
                proxy_url=proxy_url,
                geoip_enabled=geoip_enabled,
                attempt=attempt,
                attempts=attempts,
                pause=pause,
            )
        except Exception as exc:
            logger.warning("Smoke attempt {} failed: {}", attempt, exc)
            final_result = _failed_attempt_result(category_name, category_url, attempt, attempts, exc)
        attempt_results.append(
            {
                "attempt": attempt,
                "blocked": final_result.get("blocked"),
                "block_reason": final_result.get("block_reason"),
                "cards_found": final_result.get("cards_found", 0),
                "proxy": final_result.get("proxy", ""),
            }
        )
        if final_result.get("cards_found", 0) > 0 and not final_result.get("blocked"):
            break

    result = final_result or _failed_attempt_result(
        category_name, category_url, 0, attempts, RuntimeError("no attempts executed")
    )
    result["attempts"] = attempt_results

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
    for product in result.get("products_sample", [])[:5]:
        logger.info("{} | {} | {}", product["name"], product["price"], product["link"])
    return result


async def _run_smoke_attempt(
    kb: Any,
    category_name: str,
    category_url: str,
    launch_options: dict[str, Any],
    proxy_url: str,
    geoip_enabled: bool,
    attempt: int,
    attempts: int,
    pause: bool,
) -> dict[str, Any]:
    """Run one browser/proxy smoke attempt."""
    card_selectors = _split_selectors(kb.selectors.get("product_card"))
    name_selectors = _split_selectors(kb.selectors.get("product_name"))
    price_selectors = _split_selectors(kb.selectors.get("price_current"))
    link_selectors = _split_selectors(kb.selectors.get("product_link"))
    behavior_profile = build_category_behavior_profile(category_name)
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        network_events: list[dict[str, Any]] = []
        page.on(
            "response",
            lambda item: network_events.append(
                {
                    "status": item.status,
                    "url": item.url[:220],
                }
            ),
        )
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
        if not navigation_error:
            await wait_for_pyaterochka_challenge(page)
            await browse_category_page(page, behavior_profile)
            await wait_for_pyaterochka_challenge(page)
        diagnostics = await collect_page_diagnostics(page, response)
        block_reason = diagnostics.reason
        blocked = diagnostics.blocked
        navigation_reason = classify_navigation_error(navigation_error)
        if navigation_reason:
            block_reason = navigation_reason
            blocked = True
        external_ip = await _browser_external_ip(page)
        page_html = await page.content()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        screenshot_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.png"
        html_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.html"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page_html, encoding="utf-8")

        cards = [] if navigation_error else await _find_cards(page, card_selectors)
        if cards:
            await hover_product_cards(page, cards, behavior_profile)
        products = await _extract_sample_products(cards, name_selectors, price_selectors, link_selectors)
        if pause:
            logger.info("Pause enabled; leave this PowerShell window open to inspect Camoufox")
            while True:
                await page.wait_for_timeout(60_000)

    return {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "attempt": attempt,
        "max_attempts": attempts,
        "http_status": diagnostics.status,
        "page_title": diagnostics.title,
        "final_url": diagnostics.final_url,
        "html_size": diagnostics.html_size,
        "blocked": blocked,
        "block_reason": block_reason,
        "navigation_error": navigation_error,
        "proxy_enabled": bool(proxy_url),
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "fingerprint": {
            "engine": "camoufox-browserforge",
            "os": launch_options.get("os", ""),
            "locale": launch_options.get("locale", ""),
            "humanize": launch_options.get("humanize", False),
        },
        "behavior_profile": behavior_profile.summary(),
        "browser_external_ip": external_ip,
        "screenshot_path": str(screenshot_path),
        "html_path": str(html_path),
        "cards_found": len(cards),
        "products_sample": products,
        "network": _build_network_summary(network_events),
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }


async def _extract_sample_products(
    cards: list[Any],
    name_selectors: list[str],
    price_selectors: list[str],
    link_selectors: list[str],
) -> list[dict[str, str]]:
    """Extract a small product sample from cards."""
    products: list[dict[str, str]] = []
    for index, card in enumerate(cards[:10], start=1):
        name = await _query_first_text(card, name_selectors)
        price = await _query_first_text(card, price_selectors)
        link = await _query_first_attribute(card, link_selectors, "href")
        if link and link.startswith("/"):
            link = f"https://5ka.ru{link}"
        if name or price:
            products.append({"index": str(index), "name": name, "price": price, "link": link})
    return products


def _failed_attempt_result(
    category_name: str,
    category_url: str,
    attempt: int,
    attempts: int,
    exc: Exception,
) -> dict[str, Any]:
    """Build a smoke result for a failed attempt."""
    return {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "attempt": attempt,
        "max_attempts": attempts,
        "blocked": True,
        "block_reason": "attempt_failed",
        "navigation_error": str(exc),
        "cards_found": 0,
        "products_sample": [],
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }


def _parse_args() -> argparse.Namespace:
    """Parse smoke-test CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Pyaterochka Camoufox smoke test")
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    parser.add_argument("--pause", action="store_true", help="Keep browser open after the smoke attempt")
    parser.add_argument("--load-images", action="store_true", help="Allow images for visual captcha checks")
    return parser.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        warnings.filterwarnings("ignore", category=ResourceWarning)
    args = _parse_args()
    asyncio.run(
        smoke_parse_pyaterochka(
            category_name=args.category,
            attempts=args.attempts,
            headless=args.headless,
            pause=args.pause,
            block_images=not args.load_images,
        )
    )
