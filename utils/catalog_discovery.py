"""Store-neutral catalog surface discovery helpers."""

from __future__ import annotations

import asyncio

import aiohttp

from models.catalog_discovery import CatalogDiscoveryResult
from utils.catalog_tree_discovery import (
    SurfaceSignals,
    build_discovery_graph,
    classify_catalog_surface,
    collect_catalog_surface_signals,
)


def summarize_catalog_discovery(
    *,
    site_url: str,
    final_url: str,
    status_code: int,
    html: str,
) -> CatalogDiscoveryResult:
    """Build a typed discovery summary from one HTML response."""
    signals = collect_catalog_surface_signals(
        site_url=site_url,
        final_url=final_url,
        status_code=status_code,
        html=html,
    )
    return build_catalog_discovery_result(
        site_url=site_url,
        final_url=final_url,
        status_code=status_code,
        signals=signals,
        discovery_source="dom",
    )


def build_catalog_discovery_result(
    *,
    site_url: str,
    final_url: str,
    status_code: int,
    signals: SurfaceSignals,
    discovery_source: str = "dom",
) -> CatalogDiscoveryResult:
    """Build a typed discovery summary from pre-collected surface signals."""
    graph = build_discovery_graph(signals)
    classification = classify_catalog_surface(signals)
    return CatalogDiscoveryResult(
        reachable=200 <= int(status_code) < 400,
        status_code=int(status_code),
        final_url=final_url or site_url,
        surface_type=classification.surface_type,
        products_path_seen=signals.products_path_seen,
        pagination_hint=signals.pagination_hint,
        region_hint=signals.region_hint,
        challenge_hint=signals.challenge_hint,
        blocked_hint=signals.blocked_hint,
        csrf_meta_detected=signals.csrf_meta_detected,
        category_links=signals.dom_categories,
        product_links=signals.dom_products,
        api_hints=signals.api_hints,
        documents=signals.documents,
        discovery_source=str(discovery_source),
        validation_state=classification.validation_state,
        primary_root_ids=graph.primary_root_ids,
        nodes=graph.nodes,
        edges=graph.edges,
        notes=list(classification.protection_signals),
    )


async def discover_catalog_site(site_url: str, timeout_seconds: int = 20) -> CatalogDiscoveryResult:
    """Fetch one site page and classify the catalog surface."""
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(site_url, allow_redirects=True) as response:
                html = await response.text()
                return summarize_catalog_discovery(
                    site_url=site_url,
                    final_url=str(response.url),
                    status_code=response.status,
                    html=html,
                )
    except Exception as exc:
        return CatalogDiscoveryResult(
            reachable=False,
            status_code=0,
            final_url=site_url,
            surface_type="unknown",
            products_path_seen="/products" in site_url.casefold(),
            error=f"{type(exc).__name__}: {exc}",
        )


def discover_catalog_site_sync(site_url: str, timeout_seconds: int = 20) -> CatalogDiscoveryResult:
    """Run async discovery from synchronous onboarding code."""
    return asyncio.run(discover_catalog_site(site_url, timeout_seconds=timeout_seconds))
