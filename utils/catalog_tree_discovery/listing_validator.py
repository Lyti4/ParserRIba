"""Simple surface classification primitives for discovery flows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from models.catalog_discovery import CatalogSurfaceType, RouteHint, ValidationState
from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals
from utils.catalog_tree_discovery.surface_collectors import SurfaceSignals


class ValidationProbeResult(BaseModel):
    """Classification result for one discovered catalog surface."""

    surface_type: CatalogSurfaceType
    validation_state: ValidationState
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)


async def validate_listing_candidate(page: Any, url: str, wait_ms: int = 2500) -> ValidationProbeResult:
    """Open one candidate URL, collect DOM surface signals, and classify them."""
    response = await page.goto(url, wait_until="domcontentloaded")
    if wait_ms > 0:
        await page.wait_for_timeout(wait_ms)
    html = await page.content()
    status_code = int(getattr(response, "status", 0) or 0)
    final_url = str(getattr(page, "url", "") or url)
    signals = collect_catalog_surface_signals(
        site_url=url,
        final_url=final_url,
        status_code=status_code,
        html=html,
    )
    return classify_catalog_surface(signals)


def classify_catalog_surface(signals: SurfaceSignals) -> ValidationProbeResult:
    """Classify the observed surface into a launcher-friendly category."""
    if signals.pdf_hint:
        return ValidationProbeResult(surface_type="pdf_flipbook", validation_state="pdf_flipbook")
    if signals.challenge_hint:
        return ValidationProbeResult(
            surface_type="challenge",
            validation_state="challenge",
            protection_signals=["challenge"],
        )
    if signals.blocked_hint:
        return ValidationProbeResult(
            surface_type="blocked",
            validation_state="blocked",
            protection_signals=["blocked"],
        )
    if signals.dom_categories:
        return ValidationProbeResult(surface_type="category_tree", validation_state="menu_only")
    if signals.dom_products:
        return ValidationProbeResult(surface_type="product_listing", validation_state="listing_valid")
    if signals.api_hints:
        return ValidationProbeResult(
            surface_type="api_backed",
            validation_state="listing_valid",
            route_hints=[RouteHint(kind=item.kind, value=item.value, source="dom") for item in signals.api_hints],
        )
    if signals.region_hint:
        return ValidationProbeResult(surface_type="region_gate", validation_state="region_gate")
    return ValidationProbeResult(surface_type="unknown", validation_state="unknown")
