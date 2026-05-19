"""Guided site onboarding controller for launcher integration."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.parse import urlparse

from models.onboarding import DiscoveredCategoryNode, OnboardingResult
from utils.kb_loader import KBLoader
from utils.onboarding_artifacts import get_artifact_generator
from utils.onboarding_storage import OnboardingStorage
from utils.protection_strategies import get_protection_strategy
from utils.store_catalog_registry import StoreExportBackend, match_store_export_backend


def run_site_onboarding(
    *,
    site_url: str,
    intent: str = "fish_catalog",
    root_dir: Path,
    require_operator_confirmation: bool = False,
) -> OnboardingResult:
    """Create or resume a guided onboarding session for one site."""
    backend = match_store_export_backend(site_url)
    shop_slug = backend.shop if backend else _derive_shop_slug(site_url)
    artifacts = get_artifact_generator("default")(root_dir, shop_slug)
    protection = get_protection_strategy("pause_for_operator")
    if require_operator_confirmation and protection.pause_for_operator:
        result = OnboardingResult(
            session_id=str(uuid.uuid4()),
            shop_slug=shop_slug,
            site_url=site_url,
            intent=intent,
            status="needs_operator",
            artifact_paths=artifacts,
            diagnostics_summary={"protection_strategy": protection.name, "known_backend": bool(backend)},
        )
        _persist_onboarding_result(root_dir, result)
        return result

    result = _build_onboarding_result(site_url=site_url, intent=intent, root_dir=root_dir, backend=backend)
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
    backend = match_store_export_backend(site_url)
    result = _build_onboarding_result(site_url=site_url, intent=intent, root_dir=root_dir, backend=backend, session_id=session_id)
    _persist_onboarding_result(root_dir, result)
    return result


def _build_onboarding_result(
    *,
    site_url: str,
    intent: str,
    root_dir: Path,
    backend: StoreExportBackend | None,
    session_id: str | None = None,
) -> OnboardingResult:
    shop_slug = backend.shop if backend else _derive_shop_slug(site_url)
    artifacts = get_artifact_generator("default")(root_dir, shop_slug)
    if backend:
        kb = KBLoader(str(root_dir / "knowledge_base")).load_shop(backend.shop)
        target_categories = backend.resolve_categories(backend.default_category, kb.categories)
        category_tree = [
            DiscoveredCategoryNode(name=name, url=str(kb.categories.get(name) or ""))
            for name in target_categories
        ]
        status = "runtime_ready"
        diagnostics = {"known_backend": True, "category_count": len(category_tree), "protection_strategy": "pause_for_operator"}
    else:
        category_tree = []
        status = "scaffold_ready"
        diagnostics = {"known_backend": False, "category_count": 0, "protection_strategy": "pause_for_operator"}
    return OnboardingResult(
        session_id=session_id or str(uuid.uuid4()),
        shop_slug=shop_slug,
        site_url=site_url,
        intent=intent,
        status=status,
        category_tree=category_tree,
        selected_categories=[],
        artifact_paths=artifacts,
        diagnostics_summary=diagnostics,
    )


def _persist_onboarding_result(root_dir: Path, result: OnboardingResult) -> None:
    session_path = Path(result.artifact_paths.session_state_path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    storage = OnboardingStorage(root_dir / "data" / "products.db")
    storage.save_onboarding_session(result)


def _derive_shop_slug(site_url: str) -> str:
    host = urlparse(site_url).netloc.casefold().replace("www.", "")
    return host.replace(".", "_") or "unknown_store"
