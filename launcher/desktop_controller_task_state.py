"""Task-state helpers for the desktop launcher controller."""

from __future__ import annotations

from models.launcher_state import LauncherAppState

SUCCESS_MANIFEST_STATUSES = frozenset({"ok", "succeeded", "runtime_ready"})


def launcher_task_status_from_manifest(status: object) -> str:
    """Map manifest status to the launcher task state shown to the user."""
    return "succeeded" if str(status or "").strip().lower() in SUCCESS_MANIFEST_STATUSES else "failed"


def mark_product_export_started(state: LauncherAppState, *, total_targets: int) -> None:
    """Mark one product export run before the subprocess boundary starts."""
    state.task.task_kind = "product_export"
    state.task.phase = "collect_products"
    state.task.progress_total = total_targets
    state.products.items = []
    state.products.products_count = 0
    state.products.source_categories = list(state.selection.categories)
    state.products.selected_product_ids = []
    state.products.json_path = ""
    state.products.excel_path = ""
    state.products.discovered_fields = {}
    state.selection.selected_product_ids = []
    state.filters = state.filters.__class__()
    state.dynamic_filters.available_filters = {}
    state.dynamic_filters.applied_values = {}
    state.dynamic_filters.counts = {}
    state.dynamic_filters.ranges = {}
    state.dynamic_filters.missing_fields = []
    state.dynamic_filters.updated_at = ""
    state.result.products_count = 0
    state.result.summary = {}
    state.result.excel_path = ""
    state.result.json_path = ""
    state.result.report_dir = ""
    state.result.launcher_view = {}
