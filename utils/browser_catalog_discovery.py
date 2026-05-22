"""Browser-backed catalog discovery for launcher research flows."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from camoufox.async_api import AsyncCamoufox

from models.catalog_discovery import CatalogDiscoveryResult, DiscoveryPhaseEvent
from scripts.discover_pyaterochka_api import PROFILE_DIR
from utils.antibot import wait_for_pyaterochka_state
from utils.camoufox_launcher import build_research_camoufox_options, configure_windows_console
from utils.catalog_tree_discovery.research_walker import CamoufoxResearchWalker
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile
from utils.kb_loader import KBLoader
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls

PROXY_ENV = "PARSER_PROXY"
MAX_REPEAT_URLS = 3
MAX_DISCOVERY_DEPTH = 3


@dataclass(frozen=True)
class BrowserCatalogResearchContext:
    """Lightweight browser research metadata kept alongside discovery results."""

    shop: str
    final_url: str
    status_code: int
    manual_wait_used: bool
    phase_events: list[DiscoveryPhaseEvent] = field(default_factory=list)
    streamed_categories: list[str] = field(default_factory=list)


async def discover_catalog_site_via_browser(
    site_url: str,
    *,
    shop: str | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> CatalogDiscoveryResult:
    """Open one site in Camoufox and actively research the catalog surface."""
    if str(shop or "").casefold() == "pyaterochka":
        return await _discover_pyaterochka_catalog_site(
            site_url,
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
        )

    configure_windows_console()
    launch_options = build_research_camoufox_options(
        headless=headless if headless is not None else False,
    )
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_wait:
            await asyncio.to_thread(
                input,
                "Исследование магазина: дождись загрузки каталога в Camoufox и нажми Enter...",
            )
        walker_result = await _run_active_browser_research(
            page=page,
            site_url=site_url,
            initial_response=response,
            listen_seconds=listen_seconds,
        )
    return _attach_browser_research_metadata(walker_result.discovery, walker_result)


async def discover_catalog_research_context_via_browser(
    site_url: str,
    *,
    shop: str | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> tuple[CatalogDiscoveryResult, BrowserCatalogResearchContext]:
    """Run browser discovery and return lightweight runtime metadata too."""
    result = await discover_catalog_site_via_browser(
        site_url,
        shop=shop,
        headless=headless,
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
    )
    return (
        result,
        BrowserCatalogResearchContext(
            shop=str(shop or ""),
            final_url=result.final_url,
            status_code=int(result.status_code),
            manual_wait_used=bool(manual_wait),
            phase_events=list(result.phase_events),
            streamed_categories=[
                item.name or item.url for item in result.category_links[:8]
            ],
        ),
    )


async def _discover_pyaterochka_catalog_site(
    site_url: str,
    *,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> CatalogDiscoveryResult:
    """Run launcher research through protected startup, then use the active walker."""
    configure_windows_console()
    load_dotenv_file(".env")
    kb = KBLoader("knowledge_base").load_shop("pyaterochka")
    proxy_urls = load_proxy_urls(
        primary=os.environ.get(PROXY_ENV, ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    launch_options = build_research_camoufox_options(
        headless=headless if headless is not None else False,
        proxy_url=proxy_url,
        geoip=geoip_enabled,
        user_data_dir=PROFILE_DIR,
    )
    behavior_profile = build_category_behavior_profile("Рыба")
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        if kb.headers.custom:
            await page.set_extra_http_headers(kb.headers.custom)
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_wait:
            await asyncio.to_thread(
                input,
                "Исследование магазина: дождись загрузки каталога в Camoufox, реши капчу при необходимости и нажми Enter...",
            )
        else:
            await page.wait_for_timeout(5_000)
        await wait_for_pyaterochka_state(page, response, seconds=max(10, min(int(listen_seconds), 60)))
        await browse_category_page(page, behavior_profile)
        walker_result = await _run_active_browser_research(
            page=page,
            site_url=site_url,
            initial_response=response,
            listen_seconds=listen_seconds,
        )
    return _attach_browser_research_metadata(walker_result.discovery, walker_result)


def discover_catalog_site_via_browser_sync(
    site_url: str,
    *,
    shop: str | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
):
    """Run browser-backed discovery from synchronous launcher onboarding code."""
    return asyncio.run(
        discover_catalog_site_via_browser(
            site_url,
            shop=shop,
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
        )
    )


async def _run_active_browser_research(
    *,
    page: object,
    site_url: str,
    initial_response: object | None,
    listen_seconds: int,
):
    walker = CamoufoxResearchWalker(
        listen_seconds=listen_seconds,
        max_repeat_urls=MAX_REPEAT_URLS,
        max_depth=MAX_DISCOVERY_DEPTH,
    )
    return await walker.run(
        site_url=site_url,
        page=page,
        initial_response=initial_response,
    )


def _attach_browser_research_metadata(
    result: CatalogDiscoveryResult,
    walker_result: object,
) -> CatalogDiscoveryResult:
    result.phase_events = list(getattr(walker_result, "phase_events", []) or [])
    return result
