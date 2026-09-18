"""Fallback policy for protected store proxy routes."""

from __future__ import annotations

from models.catalog_discovery import CatalogDiscoveryResult

PROXY_ROUTE_BLOCK_REASONS = {
    "navigation_error",
    "navigation_timeout",
    "pyaterochka_antibot_html",
    "pyaterochka_antibot_query",
    "pyaterochka_antibot_redirect",
    "pyaterochka_captcha",
    "pyaterochka_loading_challenge",
    "pyaterochka_rotate_image_captcha",
}
PROXY_FALLBACK_NOTE = "retried_without_proxy_after_proxy_route_block"


def should_retry_without_proxy(result: CatalogDiscoveryResult, *, proxy_url: str) -> bool:
    """Return whether a proxy-backed protected-store research should retry direct."""
    if not proxy_url:
        return False
    if result.category_links or result.product_links:
        return False
    notes = {str(note) for note in result.notes}
    if "navigation_before_research_failed" in notes:
        return bool(notes & PROXY_ROUTE_BLOCK_REASONS)
    if result.surface_type != "challenge" and result.validation_state != "challenge":
        return False
    return bool(notes & PROXY_ROUTE_BLOCK_REASONS)


def mark_proxy_fallback(result: CatalogDiscoveryResult) -> CatalogDiscoveryResult:
    """Annotate a result produced by direct retry after a proxy-route block."""
    if PROXY_FALLBACK_NOTE not in result.notes:
        result.notes = [*result.notes, PROXY_FALLBACK_NOTE]
    return result
