"""Store-neutral browser discovery for protected runtime backends."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from models.browser_runtime import BrowserRuntimeKind, BrowserRuntimeLaunchRequest
from models.catalog_discovery import CatalogDiscoveryResult
from utils.browser_runtime import launch_research_browser
from utils.camoufox_launcher import configure_windows_console
from utils.catalog_tree_discovery.research_walker import CamoufoxResearchWalker
from utils.env import load_dotenv_file
from utils.protected_store_manual_gate import (
    ProtectedStoreManualGateProfile,
    collect_generic_page_diagnostics,
    wait_for_manual_store_page,
)
from utils.proxy import choose_proxy_for_attempt, load_proxy_config_from_env

MAX_REPEAT_URLS = 3
MAX_DISCOVERY_DEPTH = 3
PROTECTED_MANUAL_GATE_MIN_SECONDS = 180
PROTECTED_MANUAL_GATE_MAX_SECONDS = 900
GENERIC_MANUAL_GATE_PROFILE = ProtectedStoreManualGateProfile()


async def discover_catalog_site_with_protected_runtime(
    site_url: str,
    *,
    browser_runtime: BrowserRuntimeKind,
    headless: bool | str | None,
    manual_wait: bool,
    listen_seconds: int,
) -> CatalogDiscoveryResult:
    """Run store-neutral protected-site catalog discovery with a selected browser runtime."""
    configure_windows_console()
    load_dotenv_file(".env")
    proxy_urls = load_proxy_config_from_env(os.environ).urls
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    manual_checkpoint = _manual_checkpoint_factory(
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
    )
    launch_request = BrowserRuntimeLaunchRequest(
        kind=browser_runtime,
        headless=headless if headless is not None else False,
        proxy_url=proxy_url,
        geoip=_geoip_enabled_from_env(),
        user_data_dir=_site_browser_profile_dir(browser_runtime, site_url),
    )
    async with launch_research_browser(launch_request) as browser:
        page = await browser.new_page()
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_checkpoint is not None:
            await manual_checkpoint(page)
        walker_result = await _run_store_neutral_research(
            page=page,
            site_url=site_url,
            initial_response=response,
            listen_seconds=listen_seconds,
            after_navigation=manual_checkpoint,
        )
    walker_result.discovery.phase_events = list(walker_result.phase_events)
    return walker_result.discovery


async def _run_store_neutral_research(
    *,
    page: object,
    site_url: str,
    initial_response: object | None,
    listen_seconds: int,
    after_navigation: Callable[[Any], Awaitable[None]] | None,
):
    walker = CamoufoxResearchWalker(
        listen_seconds=listen_seconds,
        max_repeat_urls=MAX_REPEAT_URLS,
        max_depth=MAX_DISCOVERY_DEPTH,
        use_browser_waits=False,
        after_navigation=after_navigation,
        capture_network=False,
    )
    return await walker.run(
        site_url=site_url,
        page=page,
        initial_response=initial_response,
    )


def _geoip_enabled_from_env() -> bool:
    return os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}


def _manual_checkpoint_factory(
    *,
    manual_wait: bool,
    listen_seconds: int,
) -> Callable[[Any], Awaitable[None]] | None:
    if not manual_wait:
        return None

    async def _checkpoint(page: Any) -> None:
        await wait_for_manual_store_page(
            page,
            listen_seconds=listen_seconds,
            profile=GENERIC_MANUAL_GATE_PROFILE,
            collect_diagnostics=collect_generic_page_diagnostics,
            max_wait_seconds=_protected_manual_gate_wait_seconds(listen_seconds),
            use_browser_waits=False,
        )

    return _checkpoint


def _site_browser_profile_dir(browser_runtime: BrowserRuntimeKind, site_url: str) -> Path | None:
    if browser_runtime != "cloak":
        return None
    return Path("profiles") / "browser_sessions" / str(browser_runtime) / _site_profile_slug(site_url)


def _protected_manual_gate_wait_seconds(listen_seconds: int) -> int:
    return max(
        PROTECTED_MANUAL_GATE_MIN_SECONDS,
        min(PROTECTED_MANUAL_GATE_MAX_SECONDS, int(listen_seconds) * 10),
    )


def _site_profile_slug(site_url: str) -> str:
    parsed = urlparse(site_url)
    host = (parsed.netloc or parsed.path or "site").lower()
    safe = "".join(char if char.isalnum() else "-" for char in host).strip("-")
    return safe[:80] or "site"
