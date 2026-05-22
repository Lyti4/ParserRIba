"""Simple surface classification primitives for discovery flows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.catalog_discovery import CatalogSurfaceType, RouteHint, ValidationState
from utils.catalog_tree_discovery.surface_collectors import SurfaceSignals


class ValidationProbeResult(BaseModel):
    """Classification result for one discovered catalog surface."""

    surface_type: CatalogSurfaceType
    validation_state: ValidationState
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)


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
