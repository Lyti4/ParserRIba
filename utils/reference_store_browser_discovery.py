"""Browser discovery path for the first runtime-ready protected store adapter."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any

from models.browser_runtime import BrowserRuntimeKind, BrowserRuntimeLaunchRequest
from models.catalog_discovery import CatalogDiscoveryResult
from utils.antibot import collect_page_diagnostics
from utils.browser_runtime import launch_research_browser
from utils.camoufox_launcher import configure_windows_console
from utils.env import load_dotenv_file
from utils.human_behavior import browse_category_page, build_category_behavior_profile
from utils.kb_loader import KBLoader
from utils.protected_store_discovery_helpers import (
    ProtectedStoreNavigationError,
    build_blocked_store_research_result,
    build_navigation_error_research_result,
    goto_protected_store_page,
    should_open_store_catalog_root,
    store_catalog_root_url,
)
from utils.protected_store_manual_gate import wait_for_manual_store_page, wait_for_quiet_store_surface
from utils.protected_store_observable_surface import wait_for_observable_store_surface
from utils.protected_store_profiles import (
    REFERENCE_STORE_MANUAL_GATE_PROFILE,
    REFERENCE_STORE_OBSERVABLE_SURFACE_WAIT_SECONDS,
    REFERENCE_STORE_PROFILE_DIR,
    REFERENCE_STORE_RESEARCH_STATE_SETTLE_SECONDS,
)
from utils.protected_store_proxy_fallback import mark_proxy_fallback, should_retry_without_proxy
from utils.protected_store_research_timeout import (
    build_timeout_research_result,
    protected_active_research_timeout_seconds,
    run_protected_active_research,
)
from utils.proxy import choose_proxy_for_attempt, load_proxy_config_from_env

ResearchRunner = Callable[..., Awaitable[Any]]


async def discover_reference_store_catalog_site(
    site_url: str,
    *,
    browser_runtime: BrowserRuntimeKind = "camoufox",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
    research_runner: ResearchRunner,
) -> CatalogDiscoveryResult:
    """Run protected startup for the runtime-ready reference store adapter."""
    configure_windows_console()
    load_dotenv_file(".env")
    proxy_urls = load_proxy_config_from_env(os.environ).urls
    proxy_url = choose_proxy_for_attempt(proxy_urls, 1)
    result = await _discover_reference_store_catalog_site_once(
        site_url,
        browser_runtime=browser_runtime,
        headless=headless,
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
        proxy_url=proxy_url,
        research_runner=research_runner,
    )
    if should_retry_without_proxy(result, proxy_url=proxy_url):
        return mark_proxy_fallback(
            await _discover_reference_store_catalog_site_once(
                site_url,
                browser_runtime=browser_runtime,
                headless=headless,
                manual_wait=manual_wait,
                listen_seconds=listen_seconds,
                proxy_url="",
                research_runner=research_runner,
            )
        )
    return result


async def _discover_reference_store_catalog_site_once(
    site_url: str,
    *,
    browser_runtime: BrowserRuntimeKind,
    headless: bool | str | None,
    manual_wait: bool,
    listen_seconds: int,
    proxy_url: str,
    research_runner: ResearchRunner,
) -> CatalogDiscoveryResult:
    kb = KBLoader("knowledge_base").load_shop("pyaterochka")
    manual_headed = _is_manual_headed_browser(manual_wait=manual_wait, headless=headless)
    launch_request = BrowserRuntimeLaunchRequest(
        kind=browser_runtime,
        headless=headless if headless is not None else False,
        proxy_url=proxy_url,
        geoip=_geoip_enabled_from_env(),
        user_data_dir=_reference_store_profile_dir(browser_runtime),
    )
    behavior_profile = build_category_behavior_profile("\u0420\u044b\u0431\u0430")
    async with launch_research_browser(launch_request) as browser:
        page = await browser.new_page()
        if kb.headers.custom:
            await page.set_extra_http_headers(kb.headers.custom)
        if _should_prewarm_reference_store_home(site_url=site_url, browser_runtime=browser_runtime):
            try:
                home_response = await _goto_reference_store_page(
                    page,
                    "https://5ka.ru/",
                    manual_wait=manual_wait,
                    headless=headless,
                )
            except ProtectedStoreNavigationError as exc:
                return await build_navigation_error_research_result(page=page, site_url=site_url, error=exc)
            await wait_for_observable_store_surface(
                page,
                max_wait_seconds=REFERENCE_STORE_RESEARCH_STATE_SETTLE_SECONDS,
                profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
                collect_diagnostics=lambda current_page: collect_page_diagnostics(current_page, home_response),
            )
        try:
            response = await _goto_reference_store_page(
                page,
                site_url,
                manual_wait=manual_wait,
                headless=headless,
            )
        except ProtectedStoreNavigationError as exc:
            return await build_navigation_error_research_result(page=page, site_url=site_url, error=exc)
        if manual_wait and not manual_headed:
            await wait_for_manual_store_page(
                page,
                listen_seconds=listen_seconds,
                profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
                collect_diagnostics=collect_page_diagnostics,
            )
        elif not manual_wait:
            await wait_for_observable_store_surface(
                page,
                max_wait_seconds=REFERENCE_STORE_OBSERVABLE_SURFACE_WAIT_SECONDS,
                profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
                collect_diagnostics=lambda current_page: collect_page_diagnostics(current_page, response),
            )
        if should_open_store_catalog_root(str(getattr(page, "url", "") or "")):
            try:
                response = await _goto_reference_store_page(
                    page,
                    store_catalog_root_url(site_url),
                    manual_wait=manual_wait,
                    headless=headless,
                )
            except ProtectedStoreNavigationError as exc:
                return await build_navigation_error_research_result(page=page, site_url=site_url, error=exc)
            if manual_wait and not manual_headed:
                await wait_for_quiet_store_surface(
                    page,
                    listen_seconds=listen_seconds,
                    profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
                    collect_diagnostics=collect_page_diagnostics,
                )
        if not manual_headed:
            diagnostics = await wait_for_observable_store_surface(
                page,
                max_wait_seconds=REFERENCE_STORE_RESEARCH_STATE_SETTLE_SECONDS,
                profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
                collect_diagnostics=lambda current_page: collect_page_diagnostics(current_page, response),
            )
            if diagnostics.blocked:
                return await build_blocked_store_research_result(
                    page=page,
                    site_url=site_url,
                    diagnostics=diagnostics,
                )
        try:
            if manual_headed:
                await _prepare_manual_headed_research_page(
                    page=page,
                    listen_seconds=listen_seconds,
                    behavior_profile=behavior_profile,
                )
                walker_result = await research_runner(
                    page=page,
                    site_url=site_url,
                    initial_response=response,
                    listen_seconds=listen_seconds,
                )
            else:
                walker_result = await asyncio.wait_for(
                    run_protected_active_research(
                        page=page,
                        site_url=site_url,
                        initial_response=response,
                        listen_seconds=listen_seconds,
                        behavior_profile=behavior_profile,
                        research_runner=research_runner,
                    ),
                    timeout=protected_active_research_timeout_seconds(listen_seconds),
                )
        except TimeoutError:
            return await build_timeout_research_result(page=page, site_url=site_url)
    walker_result.discovery.phase_events = list(getattr(walker_result, "phase_events", []) or [])
    return walker_result.discovery


async def _goto_reference_store_page(page: Any, url: str, *, manual_wait: bool, headless: bool | str | None) -> Any:
    if _is_manual_headed_browser(manual_wait=manual_wait, headless=headless):
        try:
            return await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            if str(getattr(page, "url", "") or "").startswith(("http://", "https://")):
                return None
            raise ProtectedStoreNavigationError(url, "navigation_error") from exc
    return await goto_protected_store_page(page, url)


def _is_manual_headed_browser(*, manual_wait: bool, headless: bool | str | None) -> bool:
    return manual_wait and headless in (False, "false", "False", "0")


def _geoip_enabled_from_env() -> bool:
    return os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}


def _reference_store_profile_dir(browser_runtime: BrowserRuntimeKind) -> Any:
    if browser_runtime == "chromium":
        return None
    return REFERENCE_STORE_PROFILE_DIR


def _should_prewarm_reference_store_home(*, site_url: str, browser_runtime: BrowserRuntimeKind) -> bool:
    return browser_runtime == "chromium" and "/catalog" in site_url.lower()


async def _prepare_manual_headed_research_page(
    *,
    page: Any,
    listen_seconds: int,
    behavior_profile: Any,
) -> None:
    await wait_for_manual_store_page(
        page,
        listen_seconds=listen_seconds,
        profile=REFERENCE_STORE_MANUAL_GATE_PROFILE,
        collect_diagnostics=collect_page_diagnostics,
        max_wait_seconds=_manual_headed_ready_wait_seconds(listen_seconds),
    )
    await browse_category_page(page, behavior_profile)


def _manual_headed_ready_wait_seconds(listen_seconds: int) -> int:
    return max(180, min(900, int(listen_seconds) * 10))
