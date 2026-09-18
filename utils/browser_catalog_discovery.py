"""Browser-backed catalog discovery for launcher research flows."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from models.browser_runtime import BrowserRuntimeKind, BrowserRuntimeLaunchRequest
from models.catalog_discovery import CatalogDiscoveryResult, DiscoveryPhaseEvent
from utils.browser_runtime import launch_research_browser
from utils.camoufox_launcher import configure_windows_console
from utils.catalog_tree_discovery.research_walker import CamoufoxResearchWalker
from utils.protected_browser_runtime_discovery import discover_catalog_site_with_protected_runtime
from utils.protected_store_manual_gate import ProtectedStoreManualGateProfile, collect_generic_page_diagnostics, wait_for_manual_store_page
from utils.reference_store_browser_discovery import discover_reference_store_catalog_site

MAX_REPEAT_URLS = 3
MAX_DISCOVERY_DEPTH = 3
GENERIC_MANUAL_GATE_PROFILE = ProtectedStoreManualGateProfile()


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
    browser_runtime: BrowserRuntimeKind = "camoufox",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> CatalogDiscoveryResult:
    """Open one site in Camoufox and actively research the catalog surface."""
    if browser_runtime == "cloak":
        return await discover_catalog_site_with_protected_runtime(
            site_url,
            browser_runtime=browser_runtime,
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
        )

    if str(shop or "").casefold() == "pyaterochka":
        return await discover_reference_store_catalog_site(
            site_url,
            browser_runtime=browser_runtime,
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
            research_runner=_run_active_browser_research,
        )

    configure_windows_console()
    launch_request = BrowserRuntimeLaunchRequest(
        kind=browser_runtime,
        headless=headless if headless is not None else False,
    )
    async with launch_research_browser(launch_request) as browser:
        page = await browser.new_page()
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        if manual_wait:
            await wait_for_manual_store_page(
                page,
                listen_seconds=listen_seconds,
                profile=GENERIC_MANUAL_GATE_PROFILE,
                collect_diagnostics=collect_generic_page_diagnostics,
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
    browser_runtime: BrowserRuntimeKind = "camoufox",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> tuple[CatalogDiscoveryResult, BrowserCatalogResearchContext]:
    """Run browser discovery and return lightweight runtime metadata too."""
    result = await discover_catalog_site_via_browser(
        site_url,
        shop=shop,
        browser_runtime=browser_runtime,
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
            streamed_categories=[item.name or item.url for item in result.category_links[:8]],
        ),
    )


def discover_catalog_site_via_browser_sync(
    site_url: str,
    *,
    shop: str | None = None,
    browser_runtime: BrowserRuntimeKind = "camoufox",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
):
    """Run browser-backed discovery from synchronous launcher onboarding code."""
    return asyncio.run(
        discover_catalog_site_via_browser(
            site_url,
            shop=shop,
            browser_runtime=browser_runtime,
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
    use_browser_waits: bool = True,
    after_navigation: Callable[[Any], Awaitable[None]] | None = None,
    capture_network: bool = True,
):
    walker = CamoufoxResearchWalker(
        listen_seconds=listen_seconds,
        max_repeat_urls=MAX_REPEAT_URLS,
        max_depth=MAX_DISCOVERY_DEPTH,
        use_browser_waits=use_browser_waits,
        after_navigation=after_navigation,
        capture_network=capture_network,
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
