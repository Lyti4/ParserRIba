"""Live Pyaterochka category capture for full product export."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.discover_pyaterochka_api import DEFAULT_CATEGORY, PROFILE_DIR, _collect_dom_product_links
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile
from utils.kb_loader import KBLoader
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url

PROXY_ENV = "PARSER_PROXY"


async def capture_pyaterochka_catalog(
    *,
    category_name: str = DEFAULT_CATEGORY,
    category_url: str = "",
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    browse_rounds: int = 4,
) -> dict[str, Any]:
    """Capture full raw product items from live category browsing."""
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    resolved_category_url = str(category_url or "").strip() or str(kb.categories.get(category_name) or "").strip()
    if not resolved_category_url and not str(category_name or "").strip():
        category_name, category_url = next(iter(kb.categories.items()))
        resolved_category_url = category_url
    if not resolved_category_url:
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": "",
            "proxy": "",
            "geoip_enabled": False,
            "attempt": {
                "status": "empty",
                "reason": "unknown_category_url",
            },
            "raw_product_items": [],
            "dom_link_evidence": {"links_by_id": {}},
            "captured_product_urls": [],
        }
    proxy_urls = load_proxy_urls(primary=os.environ.get(PROXY_ENV, ""), pool=os.environ.get("PARSER_PROXIES", ""))
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    browser_headless = headless if headless is not None else (False if sys.platform == "win32" else "virtual")
    launch_options = build_camoufox_options(
        headless=browser_headless,
        proxy_url=proxy_url,
        geoip=geoip_enabled,
        block_images=False,
        block_webgl=False,
        humanize=True,
        fingerprint_os="windows",
        user_data_dir=PROFILE_DIR,
    )
    collector = _RawProductCollector()
    behavior_profile = build_category_behavior_profile(category_name)
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        tasks: set[asyncio.Task[None]] = set()

        def track_response(response: Any) -> None:
            task = asyncio.create_task(collector.record_response(response))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        page.on("response", track_response)
        if kb.headers.custom:
            await page.set_extra_http_headers(kb.headers.custom)
        logger.info("Opening {}", resolved_category_url)
        await page.goto(resolved_category_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_wait:
            await asyncio.to_thread(input, "Press Enter after captcha is solved and products are visible...")
        else:
            await page.wait_for_timeout(5_000)
        for _ in range(max(1, browse_rounds)):
            await browse_category_page(page, behavior_profile)
            await page.wait_for_timeout(listen_seconds * 1000)
        collector.dom_link_evidence = await _collect_dom_product_links(page, limit=300)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    success = bool(collector.items_by_id)
    return {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": resolved_category_url,
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "attempt": {
            "status": "ok" if success else "empty",
            "reason": "product_payload_captured" if success else "no_product_payload",
        },
        "raw_product_items": list(collector.items_by_id.values()),
        "dom_link_evidence": collector.dom_link_evidence,
        "captured_product_urls": sorted(collector.product_urls),
    }


class _RawProductCollector:
    def __init__(self) -> None:
        self.items_by_id: dict[str, dict[str, Any]] = {}
        self.product_urls: set[str] = set()
        self.dom_link_evidence: dict[str, Any] = {}

    async def record_response(self, response: Any) -> None:
        url = str(response.url)
        if "/products" not in url.lower():
            return
        try:
            headers = await response.all_headers()
        except Exception:
            headers = {}
        if "json" not in str(headers.get("content-type", "")).lower():
            return
        try:
            payload = await response.json()
        except Exception:
            return
        self.product_urls.add(url)
        for item in _extract_product_items_from_payload(payload):
            product_id = str(item.get("plu") or "").strip()
            if product_id:
                self.items_by_id[product_id] = item


def _extract_product_items_from_payload(payload: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for value in payload.values():
            items.extend(_extract_product_items_from_payload(value))
        if {"plu", "name", "prices"}.issubset(payload):
            items.append(payload)
    elif isinstance(payload, list):
        for value in payload:
            items.extend(_extract_product_items_from_payload(value))
    return items
