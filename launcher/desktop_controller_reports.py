"""Report and filter task orchestration for the desktop controller."""

from __future__ import annotations

from typing import Any

from launcher.desktop_controller_helpers import has_rich_filter_counts
from launcher.desktop_export_facets import build_available_filter_counts_from_export_json
from launcher.desktop_user_messages import empty_filter_options_message
from utils.local_task_adapter import LocalTaskProcessResult


def run_selected_report_export(controller: Any) -> LocalTaskProcessResult:
    """Build the selected local Excel report from stored products."""
    runner = (
        controller.wine_report_runner
        if controller.state.selection.intent == "wine_catalog"
        else controller.fish_report_runner
    )
    output_name = (
        "pyaterochka_wine_report"
        if controller.state.selection.intent == "wine_catalog"
        else "pyaterochka_fish_report"
    )
    return controller._run_task(
        task_name="store_report_export",
        runner=runner,
        root_dir=controller.root_dir,
        categories=controller.state.selection.categories,
        selected_product_ids=controller.state.selection.selected_product_ids,
        filters=controller.state.filters.model_dump(mode="json"),
        output_name=output_name,
        timeout_seconds=120,
    )


def load_filter_options(controller: Any) -> LocalTaskProcessResult:
    """Load post-capture filter options for the current selection."""
    runner = (
        controller.wine_filter_options_runner
        if controller.state.selection.intent == "wine_catalog"
        else controller.fish_filter_options_runner
    )
    result = controller._run_task(
        task_name="store_report_filter_options",
        runner=runner,
        root_dir=controller.root_dir,
        categories=controller.state.selection.categories,
        timeout_seconds=120,
    )
    if not has_rich_filter_counts(controller.state.dynamic_filters.counts):
        controller.state.task.message = empty_filter_options_message()
        controller.save_state()
    return result


def refresh_filter_counts_after_export(controller: Any, categories: list[str]) -> None:
    """Refresh launcher filter counts after a product export task."""
    runner = (
        controller.wine_filter_options_runner
        if controller.state.selection.intent == "wine_catalog"
        else controller.fish_filter_options_runner
    )
    try:
        filter_result = runner(root_dir=controller.root_dir, categories=categories, timeout_seconds=120)
    except Exception:
        return
    counts = dict(filter_result.available_filter_counts or {})
    if not counts:
        return
    found_filters = counts.pop("found_filters", {})
    _apply_filter_counts(controller, counts, found_filters)


def apply_filter_counts_from_export_json(controller: Any) -> None:
    """Merge filter counts discovered in the current export JSON artifact."""
    filter_counts = build_available_filter_counts_from_export_json(controller.state.result.json_path)
    if not filter_counts:
        return
    found_filters = filter_counts.pop("found_filters", {})
    _apply_filter_counts(controller, filter_counts, found_filters)


def _apply_filter_counts(
    controller: Any,
    filter_counts: dict[str, dict[str, int]],
    found_filters: Any,
) -> None:
    """Mirror discovered filter counts into structured state and compatibility view."""
    controller.state.result.launcher_view["available_filter_counts"] = filter_counts
    controller.state.dynamic_filters.counts = dict(filter_counts)
    controller.state.dynamic_filters.available_filters = {
        str(key): {"kind": "facet", "source": "available_filter_counts"}
        for key in filter_counts
    }
    if isinstance(found_filters, dict) and found_filters:
        controller.state.result.launcher_view["found_filters"] = found_filters
        controller.state.products.discovered_fields = dict(found_filters)
        controller.state.dynamic_filters.available_filters.update(
            {
                str(key): {"kind": "found_field", "source": "found_filters"}
                for key in found_filters
            }
        )
