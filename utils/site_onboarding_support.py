"""Helpers for guided site onboarding orchestration."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence, DiscoveryNode
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


def build_full_catalog_tree(discovery: CatalogDiscoveryResult) -> list[DiscoveredCategoryNode]:
    """Build the full discovered catalog tree from profile graph nodes."""
    if discovery.nodes:
        nodes_by_id = {node.node_id: node for node in discovery.nodes}
        root_ids = list(discovery.primary_root_ids) or [
            node.node_id for node in discovery.nodes if not node.parent_ids
        ]
        roots = [
            _node_to_category_tree(nodes_by_id[node_id], nodes_by_id)
            for node_id in root_ids
            if node_id in nodes_by_id
        ]
        return _wrap_flat_catalog_roots(roots, discovery.final_url)
    roots = [DiscoveredCategoryNode(name=item.name or item.url, url=item.url) for item in discovery.category_links]
    return _wrap_flat_catalog_roots(roots, discovery.final_url)


def build_full_catalog_links(discovery: CatalogDiscoveryResult) -> list[dict[str, str]]:
    """Build a flat full-catalog link list with hierarchy metadata."""
    if discovery.nodes:
        return [
            {
                "name": node.label_ru or node.label_original or node.canonical_url,
                "url": node.canonical_url,
                "node_id": node.node_id,
                "parent_ids": ",".join(node.parent_ids),
                "child_ids": ",".join(node.child_ids),
                "source": node.source,
                "payload_type": node.payload_type,
            }
            for node in discovery.nodes
        ]
    return [
        {
            "name": item.name or item.url,
            "url": item.url,
            "node_id": "",
            "parent_ids": "",
            "child_ids": "",
            "source": item.source,
            "payload_type": "",
        }
        for item in discovery.category_links
    ]


def category_evidence_map(category_links: list[CategoryEvidence]) -> dict[str, str]:
    """Normalize category evidence into a simple name-to-url mapping."""
    return {(item.name or item.url): item.url for item in category_links}


def _node_to_category_tree(
    node: DiscoveryNode,
    nodes_by_id: dict[str, DiscoveryNode],
) -> DiscoveredCategoryNode:
    children = [
        _node_to_category_tree(nodes_by_id[child_id], nodes_by_id)
        for child_id in node.child_ids
        if child_id in nodes_by_id
    ]
    return DiscoveredCategoryNode(
        name=node.label_ru or node.label_original or node.canonical_url,
        url=node.canonical_url,
        children=children,
    )


def _wrap_flat_catalog_roots(
    roots: list[DiscoveredCategoryNode],
    catalog_url: str,
) -> list[DiscoveredCategoryNode]:
    if len(roots) <= 1:
        return roots
    if any(node.children for node in roots):
        return roots
    return [DiscoveredCategoryNode(name="Каталог", url=catalog_url, children=roots)]


def persist_research_profile(*, root_dir: Path, artifacts, research) -> str:
    """Persist one discovery profile version and JSON snapshot."""
    repository = SQLiteDiscoveryProfileRepository(root_dir / "data" / "products.db")
    repository.save_profile_version(research.profile)
    snapshot_writer = DiscoveryProfileSnapshotWriter(Path(artifacts.runtime_report_dir).parent)
    return str(snapshot_writer.write_snapshot(research.profile))


def load_latest_profile_metadata(root_dir: Path, shop_slug: str, site_url: str) -> dict[str, str]:
    """Load the latest stored profile identifiers for a shop/site pair."""
    return OnboardingStorage(root_dir / "data" / "products.db").get_latest_profile_metadata(shop_slug, site_url)
