"""Structured-first read helpers for Launcher V2 UI surfaces."""

from __future__ import annotations

from typing import Any

from models.launcher_state import LauncherAppState


def report_summary(state: LauncherAppState) -> dict[str, Any]:
    """Return the latest report summary from structured state first."""
    summary = state.result.summary.get("report_summary")
    if isinstance(summary, dict):
        return dict(summary)
    view_summary = state.result.launcher_view.get("report_summary")
    return dict(view_summary) if isinstance(view_summary, dict) else {}


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
        return dict(state.dynamic_filters.counts)
    counts = state.result.summary.get("available_filter_counts")
    if isinstance(counts, dict):
        return dict(counts)
    view_counts = state.result.launcher_view.get("available_filter_counts")
    return dict(view_counts) if isinstance(view_counts, dict) else {}


def found_filter_fields(state: LauncherAppState) -> dict[str, Any]:
    """Return dynamic product fields from structured product state first."""
    if state.products.discovered_fields:
        return dict(state.products.discovered_fields)
    fields = state.result.summary.get("found_filters")
    if isinstance(fields, dict):
        return dict(fields)
    view_fields = state.result.launcher_view.get("found_filters")
    return dict(view_fields) if isinstance(view_fields, dict) else {}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
