"""Browser-backed catalog discovery for launcher research flows."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from camoufox.async_api import AsyncCamoufox

from scripts.discover_pyaterochka_api import PROFILE_DIR
from utils.antibot import wait_for_pyaterochka_state
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.catalog_discovery import summarize_catalog_discovery
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile
from utils.kb_loader import KBLoader
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls

PROXY_ENV = "PARSER_PROXY"


@dataclass(frozen=True)
class BrowserCatalogResearchContext:
    """Lightweight browser research metadata kept alongside discovery results."""

    shop: str
    final_url: str
    status_code: int
    manual_wait_used: bool


async def discover_catalog_site_via_browser(
    site_url: str,
    *,
    shop: str | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
    ):
    """Open one site in Camoufox and summarize the rendered catalog surface."""
    if str(shop or "").casefold() == "pyaterochka":
        return await _discover_pyaterochka_catalog_site(
            site_url,
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
        )

    configure_windows_console()
    launch_options = build_camoufox_options(
        headless=headless if headless is not None else False,
        block_images=False,
        block_webgl=False,
        humanize=True,
        fingerprint_os="windows",
    )
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_wait:
            await asyncio.to_thread(
                input,
                "Исследование магазина: дождись загрузки каталога в Camoufox и нажми Enter...",
            )
        else:
            await page.wait_for_timeout(max(1, int(listen_seconds)) * 1000)
        await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(1200)
        html = await page.content()
        final_url = page.url or site_url
        status_code = response.status if response is not None else 0
    return summarize_catalog_discovery(
        site_url=site_url,
        final_url=final_url,
        status_code=status_code,
        html=html,
    )


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
        ),
    )


async def _discover_pyaterochka_catalog_site(
    site_url: str,
    *,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
):
    """Run launcher research through the same protected Camoufox path as live capture."""
    configure_windows_console()
    load_dotenv_file(".env")
    kb = KBLoader("knowledge_base").load_shop("pyaterochka")
    proxy_urls = load_proxy_urls(
        primary=os.environ.get(PROXY_ENV, ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    launch_options = build_camoufox_options(
        headless=headless if headless is not None else False,
        proxy_url=proxy_url,
        geoip=geoip_enabled,
        block_images=False,
        block_webgl=False,
        humanize=True,
        fingerprint_os="windows",
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
        await page.wait_for_timeout(max(1, int(listen_seconds)) * 1000)
        html = await page.content()
        final_url = page.url or site_url
        status_code = response.status if response is not None else 0
    return summarize_catalog_discovery(
        site_url=site_url,
        final_url=final_url,
        status_code=status_code,
        html=html,
    )


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
