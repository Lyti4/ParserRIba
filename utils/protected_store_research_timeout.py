"""Bounded active-research helpers for protected store catalog discovery."""

from __future__ import annotations

from typing import Any

from models.catalog_discovery import CatalogDiscoveryResult
from utils.catalog_discovery import build_catalog_discovery_result
from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals
from utils.human_behavior import browse_category_page

PROTECTED_ACTIVE_RESEARCH_MIN_SECONDS = 45
PROTECTED_ACTIVE_RESEARCH_MAX_SECONDS = 120


async def run_protected_active_research(
    *,
    page: Any,
    site_url: str,
    initial_response: object | None,
    listen_seconds: int,
    behavior_profile: Any,
    research_runner: Any,
) -> Any:
    await browse_category_page(page, behavior_profile)
    return await research_runner(
        page=page,
        site_url=site_url,
        initial_response=initial_response,
        listen_seconds=listen_seconds,
    )


def protected_active_research_timeout_seconds(listen_seconds: int) -> int:
    return max(
        PROTECTED_ACTIVE_RESEARCH_MIN_SECONDS,
        min(PROTECTED_ACTIVE_RESEARCH_MAX_SECONDS, int(listen_seconds) * 2),
    )


async def build_timeout_research_result(*, page: Any, site_url: str) -> CatalogDiscoveryResult:
    html = ""
    try:
        html = await page.content()
    except Exception:
        html = ""
    final_url = str(getattr(page, "url", "") or site_url)
    signals = collect_catalog_surface_signals(site_url=site_url, final_url=final_url, status_code=0, html=html)
    result = build_catalog_discovery_result(
        site_url=site_url,
        final_url=final_url,
        status_code=0,
        signals=signals,
        discovery_source="mixed",
    )
    result.notes.append("active_research_timeout")
    if not result.category_links:
        result.surface_type = "challenge" if result.challenge_hint else "unknown"
        result.validation_state = "challenge" if result.challenge_hint else "empty"
    return result
