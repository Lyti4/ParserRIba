"""Quiet manual-challenge readiness checks for protected store browser flows."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals

POST_CHALLENGE_MIN_WAIT_SECONDS = 30
POST_CHALLENGE_MAX_WAIT_SECONDS = 180
MANUAL_GATE_EMPTY_PAGE_MAX_WAIT_SECONDS = 20


@dataclass(frozen=True)
class ProtectedStoreManualGateProfile:
    challenge_paths: tuple[str, ...] = ()
    loading_title_prefix: str = ""
    hard_block_reasons: tuple[str, ...] = ()
    catalog_url_marker: str = "/catalog"


@dataclass(frozen=True)
class ManualGateSnapshot:
    diagnostics: Any
    category_count: int
    product_count: int
    raw_href_count: int


async def wait_for_manual_store_page(
    page: Any,
    *,
    listen_seconds: int,
    profile: ProtectedStoreManualGateProfile,
    collect_diagnostics: Callable[[Any], Awaitable[Any]],
    max_wait_seconds: int | None = None,
    use_browser_waits: bool = True,
) -> None:
    """Wait until a manually solved challenge becomes a usable store page."""
    if sys.stdin.isatty():
        await asyncio.to_thread(input, "Press Enter after the store page is visible in the browser...")
        await wait_for_quiet_store_surface(
            page,
            listen_seconds=listen_seconds,
            profile=profile,
            collect_diagnostics=collect_diagnostics,
            max_wait_seconds=max_wait_seconds,
            use_browser_waits=use_browser_waits,
        )
        return
    wait_limit = _resolve_wait_seconds(listen_seconds, max_wait_seconds=max_wait_seconds)
    last_snapshot: ManualGateSnapshot | None = None
    empty_page_seconds = 0
    for _ in range(wait_limit):
        snapshot = await manual_gate_snapshot(page, collect_diagnostics=collect_diagnostics)
        last_snapshot = snapshot
        if snapshot is not None and manual_gate_snapshot_ready(snapshot, profile=profile):
            return
        if snapshot is not None and manual_gate_blank_page(snapshot):
            empty_page_seconds += 1
            if empty_page_seconds >= MANUAL_GATE_EMPTY_PAGE_MAX_WAIT_SECONDS:
                raise RuntimeError("manual_page_not_loaded")
        else:
            empty_page_seconds = 0
        if snapshot is None and manual_gate_page_ready(str(getattr(page, "url", "") or ""), profile=profile):
            return
        await _quiet_wait(page, use_browser_waits=use_browser_waits)
    if last_snapshot is None:
        last_snapshot = await manual_gate_snapshot(page, collect_diagnostics=collect_diagnostics)
    if last_snapshot is not None and bool(getattr(last_snapshot.diagnostics, "blocked", False)):
        reason = getattr(last_snapshot.diagnostics, "reason", "blocked")
        raise RuntimeError(f"manual_captcha_not_resolved:{reason}")
    raise RuntimeError("manual_catalog_not_ready")


async def wait_for_quiet_store_surface(
    page: Any,
    *,
    listen_seconds: int,
    profile: ProtectedStoreManualGateProfile,
    collect_diagnostics: Callable[[Any], Awaitable[Any]],
    max_wait_seconds: int | None = None,
    use_browser_waits: bool = True,
) -> None:
    """Wait for DOM readiness without sending additional navigation requests."""
    wait_limit = _resolve_wait_seconds(listen_seconds, max_wait_seconds=max_wait_seconds)
    for _ in range(wait_limit):
        snapshot = await manual_gate_snapshot(page, collect_diagnostics=collect_diagnostics)
        if snapshot is not None and manual_gate_snapshot_ready(snapshot, profile=profile):
            return
        await _quiet_wait(page, use_browser_waits=use_browser_waits)


async def manual_gate_snapshot(
    page: Any,
    *,
    collect_diagnostics: Callable[[Any], Awaitable[Any]],
) -> ManualGateSnapshot | None:
    if not all(hasattr(page, name) for name in ("title", "content")):
        return None
    diagnostics = await collect_diagnostics(page)
    html = await _safe_page_content(page)
    final_url = str(getattr(diagnostics, "final_url", "") or "")
    signals = collect_catalog_surface_signals(
        site_url=final_url,
        final_url=final_url,
        status_code=int(getattr(diagnostics, "status", 0) or 0),
        html=html,
    )
    return ManualGateSnapshot(
        diagnostics=diagnostics,
        category_count=len(signals.dom_categories),
        product_count=len(signals.dom_products),
        raw_href_count=len(signals.raw_hrefs),
    )


async def collect_generic_page_diagnostics(page: Any) -> Any:
    title = await page.title()
    html = await _safe_page_content(page)
    return SimpleNamespace(
        blocked=False,
        reason="ok",
        final_url=str(getattr(page, "url", "") or ""),
        title=title,
        html_size=len(html),
        status=None,
    )


def manual_gate_snapshot_ready(snapshot: ManualGateSnapshot, *, profile: ProtectedStoreManualGateProfile) -> bool:
    diagnostics = snapshot.diagnostics
    final_url = str(getattr(diagnostics, "final_url", "") or "")
    title = str(getattr(diagnostics, "title", "") or "")
    reason = str(getattr(diagnostics, "reason", "") or "")
    blocked = bool(getattr(diagnostics, "blocked", False))
    if not manual_gate_page_ready(final_url, profile=profile):
        return False
    if profile.loading_title_prefix and title.lower().startswith(profile.loading_title_prefix.lower()):
        return False
    if reason in profile.hard_block_reasons:
        return False
    if not blocked:
        if profile.catalog_url_marker and profile.catalog_url_marker in final_url.lower():
            return manual_gate_surface_has_catalog(snapshot, profile=profile)
        return True
    return manual_gate_surface_has_catalog(snapshot, profile=profile)


def manual_gate_surface_has_catalog(snapshot: ManualGateSnapshot, *, profile: ProtectedStoreManualGateProfile) -> bool:
    final_url = str(getattr(snapshot.diagnostics, "final_url", "") or "").lower()
    if profile.catalog_url_marker and profile.catalog_url_marker in final_url:
        return snapshot.category_count > 0 or snapshot.product_count > 0
    return snapshot.category_count >= 2


def manual_gate_blank_page(snapshot: ManualGateSnapshot) -> bool:
    diagnostics = snapshot.diagnostics
    final_url = str(getattr(diagnostics, "final_url", "") or "").lower()
    if final_url.startswith(("http://", "https://")):
        return False
    title = str(getattr(diagnostics, "title", "") or "").strip()
    html_size = int(getattr(diagnostics, "html_size", 0) or 0)
    return not title and html_size == 0


def manual_gate_page_ready(current_url: str, *, profile: ProtectedStoreManualGateProfile) -> bool:
    if not current_url.startswith(("http://", "https://")):
        return False
    lowered = current_url.lower()
    return not any(path and path.lower() in lowered for path in profile.challenge_paths)


def post_challenge_wait_seconds(listen_seconds: int) -> int:
    return max(
        POST_CHALLENGE_MIN_WAIT_SECONDS,
        min(POST_CHALLENGE_MAX_WAIT_SECONDS, int(listen_seconds) * 10),
    )


def _resolve_wait_seconds(listen_seconds: int, *, max_wait_seconds: int | None) -> int:
    if max_wait_seconds is not None:
        return max(1, int(max_wait_seconds))
    return post_challenge_wait_seconds(listen_seconds)


async def _quiet_wait(page: Any, *, use_browser_waits: bool = True) -> None:
    wait_for_timeout = getattr(page, "wait_for_timeout", None)
    if use_browser_waits and wait_for_timeout is not None:
        await wait_for_timeout(1_000)
        return
    await asyncio.sleep(1)


async def _safe_page_content(page: Any) -> str:
    try:
        return str(await page.content())
    except Exception:
        return ""
