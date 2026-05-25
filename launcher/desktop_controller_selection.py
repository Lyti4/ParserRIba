"""Selection state helpers for the desktop launcher controller."""

from __future__ import annotations

from typing import Any

from models.launcher_state import LauncherSelectionState


def update_selection_state(
    selection: LauncherSelectionState,
    *,
    shop: str | None = None,
    intent: str | None = None,
    categories: list[str] | None = None,
    selected_catalog_nodes: list[dict[str, Any]] | None = None,
    selected_product_ids: list[str] | None = None,
) -> None:
    """Apply one partial launcher selection update."""
    if shop is not None:
        selection.shop = shop
        selection.selected_catalog_nodes = []
        selection.selected_product_ids = []
    if intent is not None:
        selection.intent = intent
        selection.selected_catalog_nodes = []
        selection.selected_product_ids = []
    if categories is not None:
        selection.categories = list(categories)
        if selected_catalog_nodes is None:
            selection.selected_catalog_nodes = []
        selection.selected_product_ids = []
    if selected_catalog_nodes is not None:
        selection.selected_catalog_nodes = [dict(item) for item in selected_catalog_nodes if isinstance(item, dict)]
    if selected_product_ids is not None:
        selection.selected_product_ids = [str(item).strip() for item in selected_product_ids if str(item).strip()]
