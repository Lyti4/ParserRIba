"""Protected-store helpers for browser catalog discovery."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from models.catalog_discovery import CatalogDiscoveryResult
from utils.catalog_discovery import build_catalog_discovery_result
from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals


PROTECTED_STORE_NAVIGATION_TIMEOUT_MS = 30_000
PROTECTED_STORE_NAVIGATION_GUARD_SECONDS = 35


class ProtectedStoreNavigationError(RuntimeError):
    """Raised when a protected-store browser navigation does not complete."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{reason}:{url}")
        self.url = url
        self.reason = reason


async def goto_protected_store_page(page: Any, url: str) -> Any:
    """Navigate with a hard guard so visual browser runs cannot hang forever."""
    try:
        return await asyncio.wait_for(
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PROTECTED_STORE_NAVIGATION_TIMEOUT_MS,
            ),
            timeout=PROTECTED_STORE_NAVIGATION_GUARD_SECONDS,
        )
    except TimeoutError as exc:
        raise ProtectedStoreNavigationError(url, "navigation_timeout") from exc
    except Exception as exc:
        raise ProtectedStoreNavigationError(url, "navigation_error") from exc


async def build_blocked_store_research_result(
    *,
    page: Any,
    site_url: str,
    diagnostics: Any,
) -> CatalogDiscoveryResult:
    html = ""
    try:
        html = await page.content()
    except Exception:
        html = ""
    final_url = str(diagnostics.final_url or site_url)
    status_code = int(diagnostics.status or 0)
    signals = collect_catalog_surface_signals(site_url=site_url, final_url=final_url, status_code=status_code, html=html)
    result = build_catalog_discovery_result(
        site_url=site_url, final_url=final_url, status_code=status_code, signals=signals,
        discovery_source="protection_signal",
    )
    result.surface_type = "challenge"
    result.validation_state = "challenge"
    result.challenge_hint = True
    result.notes = [*result.notes, "blocked_before_active_research", str(diagnostics.reason or "blocked")]
    return result


async def build_navigation_error_research_result(
    *,
    page: Any | None,
    site_url: str,
    error: ProtectedStoreNavigationError,
) -> CatalogDiscoveryResult:
    html = ""
    if page is not None:
        try:
            html = await page.content()
        except Exception:
            html = ""
    final_url = str(getattr(page, "url", "") or site_url) if page is not None else site_url
    signals = collect_catalog_surface_signals(site_url=site_url, final_url=final_url, status_code=0, html=html)
    result = build_catalog_discovery_result(
        site_url=site_url,
        final_url=final_url,
        status_code=0,
        signals=signals,
        discovery_source="mixed",
    )
    result.notes.extend(["navigation_before_research_failed", error.reason])
    if not result.category_links:
        result.surface_type = "unknown"
        result.validation_state = "empty"
        result.error = error.reason
    return result


def should_open_store_catalog_root(current_url: str, *, catalog_marker: str = "/catalog") -> bool:
    normalized = str(current_url or "").lower()
    if protected_store_antibot_url(normalized):
        return False
    return normalized.startswith(("http://", "https://")) and catalog_marker not in normalized


def store_catalog_root_url(site_url: str) -> str:
    parsed = urlparse(str(site_url or "https://5ka.ru"))
    scheme = parsed.scheme or "https"
    host = parsed.netloc or "5ka.ru"
    return f"{scheme}://{host}/catalog/"


def protected_store_antibot_url(current_url: str) -> bool:
    return "/xpvnsulc/" in current_url or "/exhkqyad" in current_url
