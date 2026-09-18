"""Structured-first read helpers for Launcher V2 UI surfaces."""

from __future__ import annotations

from typing import Any

from launcher.desktop_filter_aliases import with_legacy_filter_count_aliases

from launcher.desktop_product_filtering import locally_applicable_found_filters, product_matches_export_filters
from models.launcher_state import LauncherAppState
from utils.product_breakdown_summary import with_product_breakdown_alias


def report_summary(state: LauncherAppState) -> dict[str, Any]:
    """Return the latest report summary from structured state first."""
    summary = state.result.summary.get("report_summary")
    if isinstance(summary, dict):
        return with_product_breakdown_alias(summary)
    view_summary = state.result.launcher_view.get("report_summary")
    return with_product_breakdown_alias(view_summary) if isinstance(view_summary, dict) else {}


def diagnostics_summary(state: LauncherAppState) -> dict[str, Any]:
    """Return diagnostics from profile/summary before compatibility view data."""
    if state.profile.diagnostics:
        return dict(state.profile.diagnostics)
    diagnostics = state.result.summary.get("diagnostics_summary")
    if isinstance(diagnostics, dict):
        return dict(diagnostics)
    view_diagnostics = state.result.launcher_view.get("diagnostics_summary")
    return dict(view_diagnostics) if isinstance(view_diagnostics, dict) else {}


def category_tree(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return selected research category tree from structured sources first."""
    tree = _dict_list(state.result.summary.get("category_tree"))
    if tree:
        return tree
    if state.catalog.full_tree:
        return list(state.catalog.full_tree)
    return _dict_list(state.result.launcher_view.get("category_tree"))


def full_catalog_tree(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return full catalog tree from catalog state before fallback view data."""
    if state.catalog.full_tree:
        return list(state.catalog.full_tree)
    tree = _dict_list(state.result.summary.get("full_catalog_tree"))
    if tree:
        return tree
    return _dict_list(state.result.launcher_view.get("full_catalog_tree"))


def full_catalog_links(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return full catalog link list from catalog state before fallback view data."""
    if state.catalog.full_links:
        return list(state.catalog.full_links)
    links = _dict_list(state.result.summary.get("full_catalog_links"))
    if links:
        return links
    return _dict_list(state.result.launcher_view.get("full_catalog_links"))


def catalog_discovery(state: LauncherAppState) -> dict[str, Any]:
    """Return catalog discovery metadata from structured summary first."""
    discovery = state.result.summary.get("catalog_discovery")
    if isinstance(discovery, dict):
        return dict(discovery)
    view_discovery = state.result.launcher_view.get("catalog_discovery")
    return dict(view_discovery) if isinstance(view_discovery, dict) else {}


def available_filter_counts(state: LauncherAppState) -> dict[str, Any]:
    """Return dynamic filter counts from structured state before fallback view data."""
    if state.dynamic_filters.counts:
        return _with_filter_aliases(state.dynamic_filters.counts)
    counts = state.result.summary.get("available_filter_counts")
    if isinstance(counts, dict):
        return _with_filter_aliases(counts)
    view_counts = state.result.launcher_view.get("available_filter_counts")
    return _with_filter_aliases(view_counts) if isinstance(view_counts, dict) else {}


def found_filter_fields(state: LauncherAppState) -> dict[str, Any]:
    """Return dynamic product fields from structured product state first."""
    if state.products.discovered_fields:
        return dict(state.products.discovered_fields)
    fields = state.result.summary.get("found_filters")
    if isinstance(fields, dict):
        return dict(fields)
    view_fields = state.result.launcher_view.get("found_filters")
    return dict(view_fields) if isinstance(view_fields, dict) else {}


def product_items(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return collected product cards from structured state first."""
    if state.products.items and _product_workspace_is_current(state):
        return list(state.products.items)
    products = state.result.summary.get("products")
    if isinstance(products, list):
        return _dict_list(products)
    view_products = state.result.launcher_view.get("products")
    return _dict_list(view_products)


def _product_workspace_is_current(state: LauncherAppState) -> bool:
    if state.task.task_name not in {"site_onboarding_discovery", "load_profile_session"}:
        return True
    return bool(state.products.products_count or state.products.json_path or state.result.json_path)


def filtered_product_items(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return the current product table workspace after local filters."""
    products = product_items(state)
    if not products:
        return []
    found_filters = locally_applicable_found_filters(products, state.filters.found_filters)
    return [item for item in products if product_matches_export_filters(item, state, found_filters)]


def report_product_items(state: LauncherAppState) -> list[dict[str, Any]]:
    """Return products that should define the report columns and export scope."""
    selected_ids = {str(item).strip() for item in state.selection.selected_product_ids if str(item).strip()}
    products = product_items(state)
    if selected_ids:
        selected_products = [item for item in products if _product_id(item) in selected_ids]
        return selected_products
    return filtered_product_items(state)


def _product_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("product_id") or "").strip()


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _with_filter_aliases(counts: dict[str, Any]) -> dict[str, Any]:
    return with_legacy_filter_count_aliases(counts)
