"""Workspace reset helpers for launcher task boundaries."""

from __future__ import annotations

from models.launcher_state import LauncherAppState


def clear_product_workspace_for_research(state: LauncherAppState) -> None:
    """Clear stale product/filter/report workspace when a new catalog research starts."""
    state.catalog.selected_nodes = []
    state.catalog.selected_node_urls = []
    state.products.products_count = 0
    state.products.items = []
    state.products.source_categories = []
    state.products.selected_product_ids = []
    state.products.json_path = ""
    state.products.excel_path = ""
    state.products.discovered_fields = {}
    state.dynamic_filters.available_filters = {}
    state.dynamic_filters.applied_values = {}
    state.dynamic_filters.counts = {}
    state.dynamic_filters.ranges = {}
    state.dynamic_filters.missing_fields = []
    state.dynamic_filters.updated_at = ""
    state.filters = state.filters.__class__()
    state.report.available_columns = []
    state.report.selected_columns = []
    state.report.column_titles = {}
    state.report.columns_touched = False
    state.result.products_count = 0
    state.result.summary = {}
    state.result.artifact_paths = {}
    state.result.filter_snapshot = {}
