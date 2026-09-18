"""Live Pyaterochka category capture for full product export."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, AsyncContextManager, cast

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.browser_runtime import BrowserRuntimeKind, BrowserRuntimeLaunchRequest
from utils.antibot import PageDiagnostics, collect_page_diagnostics
from utils.browser_runtime import launch_research_browser
from utils.camoufox_launcher import configure_windows_console
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile
from utils.kb_loader import KBLoader
from utils.protected_store_manual_gate import ProtectedStoreManualGateProfile, wait_for_manual_store_page
from utils.proxy import choose_proxy_for_attempt, load_proxy_config_from_env, mask_proxy_url
from utils.pyaterochka_runtime import DEFAULT_CATEGORY, PROFILE_DIR, collect_dom_product_links
from utils.site_filter_facets import collect_site_filter_facets, extract_site_filter_facets_from_payload, merge_site_filter_facets


MAX_PRODUCT_SETTLE_SECONDS = 8
MANUAL_CHALLENGE_MIN_SECONDS, MANUAL_CHALLENGE_MAX_SECONDS = 300, 900
PYATEROCHKA_HARD_BLOCK_REASONS = ("pyaterochka_antibot_redirect", "pyaterochka_antibot_query", "pyaterochka_vpn_connection_block", "pyaterochka_loading_challenge")
PYATEROCHKA_MANUAL_GATE_PROFILE = ProtectedStoreManualGateProfile(
    challenge_paths=("/xpvnsulc/", "/exhkqyad"),
    loading_title_prefix="loading https://5ka.ru/",
    hard_block_reasons=PYATEROCHKA_HARD_BLOCK_REASONS,
    catalog_url_marker="",
)


async def capture_pyaterochka_catalog(
    *,
    category_name: str = DEFAULT_CATEGORY,
    category_url: str = "",
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    browser_runtime: BrowserRuntimeKind = "camoufox",
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
    proxy_urls = load_proxy_config_from_env(os.environ).urls
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    browser_headless = headless if headless is not None else (False if sys.platform == "win32" else "virtual")
    launch_request = BrowserRuntimeLaunchRequest(
        kind=browser_runtime,
        headless=browser_headless,
        proxy_url=proxy_url,
        geoip=geoip_enabled,
        user_data_dir=PROFILE_DIR,
    )
    collector = _RawProductCollector()
    behavior_profile = build_category_behavior_profile(category_name)
    async with cast(AsyncContextManager[Any], launch_research_browser(launch_request)) as browser:
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
        response = await page.goto(resolved_category_url, wait_until="domcontentloaded", timeout=60_000)
        diagnostics = await collect_page_diagnostics(page, response)
        if diagnostics.blocked and not manual_wait:
            return _blocked_capture_result(
                category_name=category_name,
                category_url=resolved_category_url,
                proxy_url=proxy_url,
                geoip_enabled=geoip_enabled,
                reason=diagnostics.reason,
                html_size=diagnostics.html_size,
                final_url=diagnostics.final_url,
            )
        if manual_wait:
            diagnostics = await _wait_for_manual_challenge(
                page,
                initial_diagnostics=diagnostics,
                max_seconds=_manual_challenge_wait_seconds(listen_seconds),
            )
            if diagnostics.blocked:
                return _blocked_capture_result(
                    category_name=category_name,
                    category_url=resolved_category_url,
                    proxy_url=proxy_url,
                    geoip_enabled=geoip_enabled,
                    reason=diagnostics.reason,
                    html_size=diagnostics.html_size,
                    final_url=diagnostics.final_url,
                )
            if _should_restore_category_after_manual_challenge(diagnostics.final_url, resolved_category_url):
                response = await page.goto(resolved_category_url, wait_until="domcontentloaded", timeout=60_000)
                diagnostics = await collect_page_diagnostics(page, response)
                if diagnostics.blocked:
                    return _blocked_capture_result(
                        category_name=category_name,
                        category_url=resolved_category_url,
                        proxy_url=proxy_url,
                        geoip_enabled=geoip_enabled,
                        reason=diagnostics.reason,
                        html_size=diagnostics.html_size,
                        final_url=diagnostics.final_url,
                    )
        else:
            await page.wait_for_timeout(5_000)
        settle_seconds = _product_settle_seconds(listen_seconds)
        for _ in range(_capture_browse_rounds(manual_wait=manual_wait, browse_rounds=browse_rounds)):
            await browse_category_page(page, behavior_profile)
            await page.wait_for_timeout(settle_seconds * 1000)
        collector.dom_link_evidence = await collect_dom_product_links(page, limit=300)
        collector.site_filter_facets = merge_site_filter_facets(
            collector.site_filter_facets,
            await collect_site_filter_facets(page),
        )
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
        "site_filter_facets": collector.site_filter_facets,
    }


def _blocked_capture_result(
    *,
    category_name: str,
    category_url: str,
    proxy_url: str,
    geoip_enabled: bool,
    reason: str,
    html_size: int,
    final_url: str,
) -> dict[str, Any]:
    return {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "attempt": {
            "status": "blocked",
            "reason": reason,
        },
        "raw_product_items": [],
        "dom_link_evidence": {"links_by_id": {}},
        "captured_product_urls": [],
        "site_filter_facets": {},
        "block_diagnostics": {
            "reason": reason,
            "html_size": html_size,
            "final_url": final_url,
        },
    }


async def _wait_for_manual_challenge(page: Any, *, initial_diagnostics: Any, max_seconds: int) -> Any:
    try:
        await wait_for_manual_store_page(
            page,
            listen_seconds=max(1, int(max_seconds) // 10),
            profile=PYATEROCHKA_MANUAL_GATE_PROFILE,
            collect_diagnostics=_manual_mode_diagnostics,
            max_wait_seconds=max_seconds,
        )
    except RuntimeError:
        return await _manual_mode_diagnostics(page)
    return await _manual_mode_diagnostics(page)


async def _manual_mode_diagnostics(page: Any) -> PageDiagnostics:
    diagnostics = await collect_page_diagnostics(page)
    if diagnostics.blocked and _manual_catalog_reached(diagnostics):
        return PageDiagnostics(
            blocked=False,
            reason="manual_catalog_ready_after_challenge",
            final_url=diagnostics.final_url,
            title=diagnostics.title,
            html_size=diagnostics.html_size,
            status=diagnostics.status,
        )
    return diagnostics


def _manual_catalog_reached(diagnostics: PageDiagnostics) -> bool:
    final_url = diagnostics.final_url.lower()
    if not final_url.startswith(("http://", "https://")):
        return False
    if any(path in final_url for path in PYATEROCHKA_MANUAL_GATE_PROFILE.challenge_paths):
        return False
    return not diagnostics.title.lower().startswith("loading https://5ka.ru/")


def _should_restore_category_after_manual_challenge(final_url: str, category_url: str) -> bool:
    normalized_final = str(final_url or "").rstrip("/").lower()
    normalized_category = str(category_url or "").rstrip("/").lower()
    return bool(normalized_category) and normalized_final != normalized_category


def _product_settle_seconds(listen_seconds: int) -> int:
    return min(max(1, int(listen_seconds)), MAX_PRODUCT_SETTLE_SECONDS)


def _manual_challenge_wait_seconds(listen_seconds: int) -> int:
    return max(MANUAL_CHALLENGE_MIN_SECONDS, min(MANUAL_CHALLENGE_MAX_SECONDS, int(listen_seconds) * 10))


def _capture_browse_rounds(*, manual_wait: bool, browse_rounds: int) -> int:
    return 1 if manual_wait else max(1, int(browse_rounds))


class _RawProductCollector:
    def __init__(self) -> None:
        self.items_by_id: dict[str, dict[str, Any]] = {}
        self.product_urls: set[str] = set()
        self.dom_link_evidence: dict[str, Any] = {}
        self.site_filter_facets: dict[str, list[str]] = {}

    async def record_response(self, response: Any) -> None:
        url = str(response.url)
        try:
            headers = await response.all_headers()
        except Exception:
            headers = {}
        headers_lc = {str(key).lower(): value for key, value in dict(headers).items()}
        if "json" not in str(headers_lc.get("content-type", "")).lower():
            return
        try:
            payload = await response.json()
        except Exception:
            return
        self.site_filter_facets = merge_site_filter_facets(
            self.site_filter_facets,
            extract_site_filter_facets_from_payload(payload),
        )
        product_items = _extract_product_items_from_payload(payload)
        if product_items or "/product" in url.lower():
            self.product_urls.add(url)
        for item in product_items:
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
