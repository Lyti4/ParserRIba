"""Catalog entrypoint collection helpers for research runs."""

from __future__ import annotations

from models.catalog_discovery import CategoryEvidence
from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals


def collect_catalog_entrypoints_from_html(site_url: str, html: str) -> list[CategoryEvidence]:
    """Collect category-like entrypoints from one rendered page snapshot."""
    signals = collect_catalog_surface_signals(
        site_url=site_url,
        final_url=site_url,
        status_code=200,
        html=html,
    )
    return signals.dom_categories
