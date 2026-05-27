"""Launcher V2 workspace-state synchronization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.launcher_state import LauncherAppState
from utils.local_task_adapter import LocalTaskProcessResult


def sync_workspace_state(state: LauncherAppState, result: LocalTaskProcessResult) -> None:
    """Mirror normalized task results into structured Launcher V2 workspace state."""
    summary = dict(result.manifest.summary or {})
    artifacts = dict(result.manifest.artifact_paths or {})
    view = dict(state.result.launcher_view or {})
    _sync_result_state(state, result, summary, artifacts)
    _sync_profile_state(state, result, summary, view)
    _sync_catalog_state(state, summary, view)
    _sync_product_state(state, summary, artifacts, view)
    _sync_dynamic_filter_state(state, view)


def _sync_result_state(
    state: LauncherAppState,
    result: LocalTaskProcessResult,
    summary: dict[str, Any],
    artifacts: dict[str, Any],
) -> None:
    state.result.summary = dict(summary)
    state.result.artifact_paths = {
        str(key): str(value)
        for key, value in artifacts.items()
        if value is not None
    }
    state.result.products_count = _int_value(
        summary.get("products_count"),
        _int_value(state.result.launcher_view.get("products_count"), state.result.products_count),
    )
    state.result.source_profile_id = str(
        summary.get("active_profile_id")
        or state.result.launcher_view.get("active_profile_id")
        or state.result.source_profile_id
        or ""
    )
    if result.manifest.task_name == "store_report_export":
        state.result.filter_snapshot = dict(state.filters.model_dump(mode="json"))
    else:
        state.result.filter_snapshot = {}


def _sync_profile_state(
    state: LauncherAppState,
    result: LocalTaskProcessResult,
    summary: dict[str, Any],
    view: dict[str, Any],
) -> None:
    profile_id = summary.get("active_profile_id") or view.get("active_profile_id")
    version_id = summary.get("active_profile_version_id") or view.get("active_profile_version_id")
    if profile_id:
        state.profile.profile_id = str(profile_id)
    if version_id:
        state.profile.profile_version_id = str(version_id)
    if result.manifest.shop:
        state.profile.shop = str(result.manifest.shop)
    site_url = summary.get("site_url") or view.get("site_url")
    if site_url:
        state.profile.site_url = str(site_url)
    domain = summary.get("domain") or view.get("domain")
    if domain:
        state.profile.domain = str(domain)
    display_name = summary.get("display_name") or view.get("display_name")
    if display_name:
        state.profile.display_name = str(display_name)
    diagnostics = summary.get("diagnostics_summary") or view.get("diagnostics_summary")
    if isinstance(diagnostics, dict):
        state.profile.diagnostics = dict(diagnostics)


def _sync_catalog_state(
    state: LauncherAppState,
    summary: dict[str, Any],
    view: dict[str, Any],
) -> None:
    full_tree = _dict_list(summary.get("full_catalog_tree") or view.get("full_catalog_tree"))
    category_tree = _dict_list(summary.get("category_tree") or view.get("category_tree"))
    full_links = _dict_list(summary.get("full_catalog_links") or view.get("full_catalog_links"))
    selected_nodes = _dict_list(state.selection.selected_catalog_nodes)
    if full_tree:
        state.catalog.full_tree = full_tree
    elif category_tree:
        state.catalog.full_tree = category_tree
    if full_links:
        state.catalog.full_links = full_links
    if selected_nodes:
        state.catalog.selected_nodes = selected_nodes
        state.catalog.selected_node_urls = [
            str(item.get("url"))
            for item in selected_nodes
            if str(item.get("url", "")).strip()
        ]
    catalog_type = summary.get("catalog_type") or view.get("catalog_type")
    if catalog_type:
        state.catalog.catalog_type = str(catalog_type)


def _sync_product_state(
    state: LauncherAppState,
    summary: dict[str, Any],
    artifacts: dict[str, Any],
    view: dict[str, Any],
) -> None:
    state.products.products_count = _int_value(
        summary.get("products_count"),
        _int_value(view.get("products_count"), state.products.products_count),
    )
    categories = _str_list(
        summary.get("categories")
        or view.get("categories")
        or summary.get("selected_categories")
        or view.get("selected_categories")
        or state.selection.categories
    )
    if categories:
        state.products.source_categories = categories
    state.products.selected_product_ids = list(state.selection.selected_product_ids)
    state.products.json_path = str(artifacts.get("json_path") or state.result.json_path or "")
    state.products.excel_path = str(artifacts.get("excel_path") or state.result.excel_path or "")
    product_items = _products_from_summary(summary)
    json_items, json_loaded = _products_from_json_path(state.products.json_path)
    if not product_items and json_loaded:
        product_items = json_items
    if product_items or "products" in summary or json_loaded:
        state.products.items = product_items
        state.products.products_count = len(product_items)
    found_fields = view.get("found_filters") or summary.get("found_filters")
    if isinstance(found_fields, dict):
        state.products.discovered_fields = dict(found_fields)


def _sync_dynamic_filter_state(state: LauncherAppState, view: dict[str, Any]) -> None:
    available = view.get("available_filter_counts")
    found = view.get("found_filters")
    state.dynamic_filters.available_filters = {}
    state.dynamic_filters.counts = {}
    state.dynamic_filters.ranges = {}
    state.dynamic_filters.missing_fields = []
    if isinstance(available, dict) and available:
        state.dynamic_filters.counts = dict(available)
        state.dynamic_filters.available_filters = {
            str(key): {"kind": "facet", "source": "available_filter_counts"}
            for key in available
        }
    if isinstance(found, dict) and found:
        state.dynamic_filters.available_filters.update(
            {
                str(key): {"kind": "found_field", "source": "found_filters"}
                for key in found
            }
        )
        state.dynamic_filters.applied_values = dict(state.filters.model_dump(mode="json"))
        state.dynamic_filters.missing_fields = [
            str(key)
            for key, value in found.items()
            if isinstance(value, dict) and not value
        ]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _products_from_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return _dict_list(summary.get("products"))


def _products_from_json_path(json_path: str) -> tuple[list[dict[str, Any]], bool]:
    path = Path(str(json_path or ""))
    if not path.exists():
        return [], False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], False
    products = payload.get("products")
    return _dict_list(products), isinstance(products, list)


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
