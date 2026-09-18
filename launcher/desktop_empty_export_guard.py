"""Guards against stale UI filters after empty product exports."""

from __future__ import annotations

from typing import Any

from models.launcher_state import LauncherFilterState


def clear_stale_filters_for_empty_export(state: Any) -> None:
    """Clear in-memory filters when the latest product export has no products."""
    task_kind = str(getattr(getattr(state, "task", None), "task_kind", "") or "")
    if task_kind != "product_export":
        return
    products = getattr(state, "products", None)
    result = getattr(state, "result", None)
    products_count = int(getattr(products, "products_count", 0) or 0)
    result_count = int(getattr(result, "products_count", 0) or 0)
    if products_count or result_count or list(getattr(products, "items", []) or []):
        return
    state.filters = LauncherFilterState()
    state.products.discovered_fields = {}
    state.dynamic_filters.available_filters = {}
    state.dynamic_filters.counts = {}
    state.dynamic_filters.ranges = {}
    state.dynamic_filters.missing_fields = []
    state.dynamic_filters.applied_values = {}
