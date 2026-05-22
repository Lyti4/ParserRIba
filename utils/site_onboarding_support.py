"""Helpers for guided site onboarding orchestration."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence
from models.onboarding import DiscoveredCategoryNode
from utils.category_intents import get_category_intent_resolver
from utils.discovery_profile_repository import SQLiteDiscoveryProfileRepository
from utils.discovery_profile_snapshot import DiscoveryProfileSnapshotWriter
from utils.kb_loader import KBLoader
from utils.onboarding_storage import OnboardingStorage
from utils.store_catalog_registry import KnownStoreSite


def derive_shop_slug(site_url: str) -> str:
    """Derive one stable local shop slug from a site URL."""
    host = urlparse(site_url).netloc.casefold().replace("www.", "")
    return host.replace(".", "_") or "unknown_store"


def load_kb_categories(root_dir: Path, shop_slug: str | None) -> dict[str, str]:
    """Load KB categories for a known shop slug when they exist."""
    if not shop_slug:
        return {}
    kb_path = root_dir / "knowledge_base" / f"{shop_slug}.md"
    if not kb_path.exists():
        return {}
    kb = KBLoader(str(root_dir / "knowledge_base")).load_shop(shop_slug)
    return kb.categories


def resolve_known_site_categories(
    *,
    root_dir: Path,
    site_profile: KnownStoreSite,
    intent: str,
    discovery: CatalogDiscoveryResult,
) -> list[str]:
    """Resolve intent-aware categories from discovery evidence and KB."""
    kb_categories = load_kb_categories(root_dir, site_profile.kb_shop)
    if discovery.category_links:
        discovered_categories = {item.name or item.url: item.url for item in discovery.category_links}
        if not kb_categories:
            return list(discovered_categories)
        return get_category_intent_resolver(intent)("Рыба", discovered_categories)
    if kb_categories:
        return get_category_intent_resolver(intent)("Рыба", kb_categories)
    return []


def build_category_tree(
    target_categories: list[str],
    kb_categories: dict[str, str],
    discovery: CatalogDiscoveryResult,
) -> list[DiscoveredCategoryNode]:
    """Build launcher category nodes from discovery-first evidence."""
    discovery_map = category_evidence_map(discovery.category_links)
    if discovery_map:
        return [DiscoveredCategoryNode(name=name, url=discovery_map.get(name, "")) for name in target_categories]
    if kb_categories:
        return [DiscoveredCategoryNode(name=name, url=str(kb_categories.get(name) or "")) for name in target_categories]
    return []


def category_evidence_map(category_links: list[CategoryEvidence]) -> dict[str, str]:
    """Normalize category evidence into a simple name-to-url mapping."""
    return {(item.name or item.url): item.url for item in category_links}


def persist_research_profile(*, root_dir: Path, artifacts, research) -> str:
    """Persist one discovery profile version and JSON snapshot."""
    repository = SQLiteDiscoveryProfileRepository(root_dir / "data" / "products.db")
    repository.save_profile_version(research.profile)
    snapshot_writer = DiscoveryProfileSnapshotWriter(Path(artifacts.runtime_report_dir).parent)
    return str(snapshot_writer.write_snapshot(research.profile))


def load_latest_profile_metadata(root_dir: Path, shop_slug: str, site_url: str) -> dict[str, str]:
    """Load the latest stored profile identifiers for a shop/site pair."""
    return OnboardingStorage(root_dir / "data" / "products.db").get_latest_profile_metadata(shop_slug, site_url)
