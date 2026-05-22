"""Adaptive browser research runner for catalog tree discovery."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from models.catalog_discovery import CatalogDiscoveryResult, DiscoveryPhaseEvent, SiteProfileVersion
from utils.browser_catalog_discovery import discover_catalog_research_context_via_browser
from utils.catalog_tree_discovery.phase_events import make_phase_event
from utils.store_catalog_registry import resolve_catalog_research_site

MAX_REPEAT_URLS = 3
MAX_EMPTY_BRANCHES = 5
MAX_DISCOVERY_DEPTH = 8


class CatalogTreeDiscoveryRunResult(BaseModel):
    """Serializable research result returned by the adaptive runner."""

    profile: SiteProfileVersion
    phase_events: list[DiscoveryPhaseEvent] = Field(default_factory=list)
    streamed_categories: list[str] = Field(default_factory=list)
    current_phase: str = ""
    mode: str = "live"
    partial: bool = False
    catalog_discovery: CatalogDiscoveryResult
    limits: dict[str, int] = Field(default_factory=dict)


async def run_catalog_tree_discovery(
    site_url: str,
    *,
    shop: str | None = None,
    mode: str = "live",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> CatalogTreeDiscoveryRunResult:
    """Run adaptive catalog research through the existing browser discovery path."""
    resolved_site = resolve_catalog_research_site(site_url, shop)
    resolved_shop = resolved_site.shop if resolved_site else str(shop or "")
    run_id = f"research-{uuid4().hex[:12]}"
    profile_id = _build_profile_id(resolved_shop or "unknown", site_url)
    phase_events = [
        make_phase_event("open_site", "running", "Открытие сайта"),
        make_phase_event("collect_surface", "running", "Поиск структуры каталога"),
    ]
    discovery, context = await discover_catalog_research_context_via_browser(
        site_url,
        shop=resolved_shop or None,
        headless=headless,
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
    )
    category_names = _limit_category_names([item.name or item.url for item in discovery.category_links])
    phase_events.append(
        make_phase_event(
            "validate_nodes",
            "completed",
            "Проверка разделов",
            category_names if mode == "live" else [],
        )
    )
    notes = list(discovery.notes)
    if context.manual_wait_used:
        notes.append("manual_wait_used")
    partial = False
    if discovery.surface_type in {"challenge", "blocked"}:
        partial = True
        notes.append("partial_research_due_to_challenge")
    if not category_names:
        notes.append("empty_research_branch")
    notes.append(f"adaptive_limits:{MAX_REPEAT_URLS}/{MAX_EMPTY_BRANCHES}/{MAX_DISCOVERY_DEPTH}")
    profile = SiteProfileVersion(
        profile_id=profile_id,
        version_id=run_id,
        shop_slug=resolved_shop or "unknown",
        site_url=context.final_url or site_url,
        run_id=run_id,
        primary_root_ids=list(discovery.primary_root_ids),
        nodes=list(discovery.nodes),
        edges=list(discovery.edges),
        notes=notes,
    )
    phase_events.append(make_phase_event("persist_profile", "completed", "Сохранение профиля"))
    phase_events.append(
        make_phase_event(
            "build_tree",
            "completed",
            "Подготовка дерева",
            category_names,
        )
    )
    return CatalogTreeDiscoveryRunResult(
        profile=profile,
        phase_events=phase_events if mode == "live" else [phase_events[-1]],
        streamed_categories=category_names if mode == "live" else [],
        current_phase="build_tree",
        mode=mode,
        partial=partial,
        catalog_discovery=discovery,
        limits={
            "max_repeat_urls": MAX_REPEAT_URLS,
            "max_empty_branches": MAX_EMPTY_BRANCHES,
            "max_discovery_depth": MAX_DISCOVERY_DEPTH,
        },
    )


def _build_profile_id(shop_slug: str, site_url: str) -> str:
    normalized = "".join(char if char.isalnum() else "-" for char in str(site_url).casefold()).strip("-")
    return f"{shop_slug or 'unknown'}:{normalized or 'site'}"


def _limit_category_names(category_names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    limited: list[str] = []
    for name in category_names:
        count = seen.get(name, 0)
        if count >= MAX_REPEAT_URLS:
            continue
        seen[name] = count + 1
        limited.append(name)
    return limited
