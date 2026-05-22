"""Guided site onboarding controller for launcher integration."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from models.catalog_discovery import CatalogDiscoveryResult
from models.onboarding import OnboardingResult
from utils.browser_catalog_discovery import discover_catalog_site_via_browser_sync
from utils.catalog_discovery import discover_catalog_site_sync
from utils.catalog_tree_discovery.runner import CatalogTreeDiscoveryRunResult, run_catalog_tree_discovery
from utils.onboarding_artifacts import get_artifact_generator
from utils.onboarding_storage import OnboardingStorage
from utils.protection_strategies import get_protection_strategy
from utils.site_onboarding_support import (
    build_category_tree,
    derive_shop_slug,
    load_kb_categories,
    load_latest_profile_metadata,
    persist_research_profile,
    resolve_known_site_categories,
)
from utils.store_catalog_registry import (
    KnownStoreSite,
    match_known_store_site,
)


def run_site_onboarding(
    *,
    site_url: str,
    intent: str = "fish_catalog",
    root_dir: Path,
    require_operator_confirmation: bool = False,
    selected_categories: list[str] | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> OnboardingResult:
    """Create or resume a guided onboarding session for one site."""
    site_profile = match_known_store_site(site_url)
    shop_slug = site_profile.shop if site_profile else derive_shop_slug(site_url)
    artifacts = get_artifact_generator("default")(root_dir, shop_slug)
    protection = get_protection_strategy("pause_for_operator")
    if require_operator_confirmation and protection.pause_for_operator:
        profile_metadata = load_latest_profile_metadata(root_dir, shop_slug, site_url)
        result = OnboardingResult(
            session_id=str(uuid.uuid4()),
            shop_slug=shop_slug,
            site_url=site_url,
            intent=intent,
            status="needs_operator",
            selected_categories=list(selected_categories or []),
            active_profile_id=str(profile_metadata.get("profile_id") or ""),
            active_profile_version_id=str(profile_metadata.get("profile_version_id") or ""),
            artifact_paths=artifacts,
            diagnostics_summary={
                "protection_strategy": protection.name,
                "known_backend": bool(site_profile),
                "runtime_export_ready": bool(site_profile and site_profile.export_backend_shop),
            },
        )
        _persist_onboarding_result(root_dir, result)
        return result

    result = _build_onboarding_result(
        site_url=site_url,
        intent=intent,
        root_dir=root_dir,
        site_profile=site_profile,
        selected_categories=selected_categories,
        headless=headless,
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
    )
    _persist_onboarding_result(root_dir, result)
    return result


def resume_site_onboarding(*, session_id: str, root_dir: Path) -> OnboardingResult:
    """Resume a paused onboarding session and continue discovery."""
    storage = OnboardingStorage(root_dir / "data" / "products.db")
    saved = storage.get_onboarding_session(session_id)
    if not saved:
        raise ValueError(f"Unknown onboarding session: {session_id}")
    site_url = str(saved.get("site_url") or "")
    intent = str(saved.get("intent") or "fish_catalog")
    site_profile = match_known_store_site(site_url)
    result = _build_onboarding_result(
        site_url=site_url,
        intent=intent,
        root_dir=root_dir,
        site_profile=site_profile,
        session_id=session_id,
    )
    _persist_onboarding_result(root_dir, result)
    return result


def _build_onboarding_result(
    *,
    site_url: str,
    intent: str,
    root_dir: Path,
    site_profile: KnownStoreSite | None,
    session_id: str | None = None,
    selected_categories: list[str] | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> OnboardingResult:
    shop_slug = site_profile.shop if site_profile else derive_shop_slug(site_url)
    artifacts = get_artifact_generator("default")(root_dir, shop_slug)
    if not site_profile:
        return OnboardingResult(
            session_id=session_id or str(uuid.uuid4()),
            shop_slug=shop_slug,
            site_url=site_url,
            intent=intent,
            status="scaffold_ready",
            category_tree=[],
            selected_categories=list(selected_categories or []),
            artifact_paths=artifacts,
            diagnostics_summary={
                "known_backend": False,
                "runtime_export_ready": False,
                "category_count": 0,
                "protection_strategy": "pause_for_operator",
            },
        )

    research = _run_catalog_research_sync(
        site_url,
        site_profile,
        headless=headless,
        manual_wait=manual_wait,
        listen_seconds=listen_seconds,
    )
    discovery = research.catalog_discovery
    kb_categories = load_kb_categories(root_dir, site_profile.kb_shop)
    target_categories = resolve_known_site_categories(
        root_dir=root_dir,
        site_profile=site_profile,
        intent=intent,
        discovery=discovery,
    )
    category_tree = build_category_tree(target_categories, kb_categories, discovery)
    profile_snapshot_path = persist_research_profile(
        root_dir=root_dir,
        artifacts=artifacts,
        research=research,
    )
    diagnostics = {
        "known_backend": True,
        "runtime_export_ready": bool(site_profile.export_backend_shop),
        "category_count": len(category_tree),
        "category_source": _category_source(discovery, category_tree),
        "protection_strategy": "pause_for_operator",
        "catalog_discovery": discovery.model_dump(mode="json"),
        "phase_events": [event.model_dump(mode="json") for event in research.phase_events],
        "profile_notes": list(research.profile.notes),
        "partial_research": bool(research.partial),
    }
    if profile_snapshot_path:
        diagnostics["profile_snapshot_path"] = profile_snapshot_path
    if not kb_categories and category_tree:
        diagnostics["intent_category_candidates"] = [node.name for node in category_tree]
        diagnostics["intent_category_links"] = [
            {"name": node.name, "url": node.url}
            for node in category_tree
        ]
    return OnboardingResult(
        session_id=session_id or str(uuid.uuid4()),
        shop_slug=shop_slug,
        site_url=site_url,
        intent=intent,
        status=site_profile.onboarding_status,
        category_tree=category_tree,
        selected_categories=list(selected_categories or []),
        active_profile_id=research.profile.profile_id,
        active_profile_version_id=research.profile.version_id,
        streamed_categories=list(research.streamed_categories),
        research_mode=research.mode,
        current_phase=research.current_phase,
        artifact_paths=artifacts,
        diagnostics_summary=diagnostics,
    )


def _persist_onboarding_result(root_dir: Path, result: OnboardingResult) -> None:
    session_path = Path(result.artifact_paths.session_state_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    OnboardingStorage(root_dir / "data" / "products.db").save_onboarding_session(result)


def discover_catalog_for_onboarding(site_url: str) -> CatalogDiscoveryResult:
    """Discover one site surface for onboarding diagnostics."""
    return discover_catalog_site_sync(site_url)


def _run_catalog_research_sync(
    site_url: str,
    site_profile: KnownStoreSite,
    *,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> CatalogTreeDiscoveryRunResult:
    return asyncio.run(
        run_catalog_tree_discovery(
            site_url,
            shop=site_profile.shop,
            mode="live",
            headless=headless,
            manual_wait=manual_wait,
            listen_seconds=listen_seconds,
        )
    )


def _category_source(discovery: CatalogDiscoveryResult, category_tree: list[object]) -> str:
    """Describe how the category tree was resolved for diagnostics."""
    if discovery.category_links:
        return "browser_discovery"
    return "kb_fallback" if category_tree else "none"
