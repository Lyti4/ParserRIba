"""Pure helpers for desktop launcher controller orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.local_task_adapter import LocalTaskProcessResult, build_local_task_process_result


def discovered_category_names(launcher_view: dict[str, Any]) -> list[str]:
    """Read category names from onboarding results when they exist."""
    category_tree = launcher_view.get("category_tree")
    if not isinstance(category_tree, list):
        return []
    names: list[str] = []
    for node in category_tree:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def combine_export_results(
    results: list[LocalTaskProcessResult],
    selected_categories: list[str],
) -> LocalTaskProcessResult:
    """Combine sequential single-category exports into one launcher result."""
    if len(results) == 1:
        return results[0]
    last_result = results[-1]
    total_products = 0
    combined_categories: list[str] = []
    for result in results:
        export_summary = result.export_summary or {}
        total_products += int(export_summary.get("products_count") or 0)
        for category_name in export_summary.get("categories") or []:
            rendered = str(category_name)
            if rendered not in combined_categories:
                combined_categories.append(rendered)
    summary = dict(last_result.manifest.summary or {})
    summary["products_count"] = total_products
    summary["categories"] = combined_categories or list(selected_categories)
    summary["selected_categories"] = list(selected_categories)
    summary["export_summary"] = {
        **dict(last_result.export_summary or {}),
        "products_count": total_products,
        "categories": combined_categories or list(selected_categories),
    }
    manifest = last_result.manifest.model_copy(update={"summary": summary})
    return build_local_task_process_result(
        manifest=manifest,
        stdout=last_result.stdout,
        stderr=last_result.stderr,
    )


def report_dir_from_artifacts(artifacts: dict[str, str], *, existing_report_dir: str) -> str:
    """Derive one user-openable output directory from task artifacts."""
    excel_path = str(artifacts.get("excel_path") or "")
    if excel_path:
        return str(Path(excel_path).parent)
    json_path = str(artifacts.get("json_path") or "")
    if json_path:
        return str(Path(json_path).parent)
    runtime_report_dir = str(artifacts.get("runtime_report_dir") or "")
    return runtime_report_dir or existing_report_dir


def artifact_or_existing(artifact_value: str | None, existing_value: str) -> str:
    """Keep the current artifact path when a task returns no replacement."""
    value = str(artifact_value or "")
    return value or existing_value


def has_rich_filter_counts(available_filter_counts: Any) -> bool:
    """Return whether supplier/brand/style filters already contain useful data."""
    if not isinstance(available_filter_counts, dict):
        return False
    for key in ("suppliers", "brands", "wine_styles", "alcohol_types", "sugar_classes", "colors"):
        facet = available_filter_counts.get(key)
        if isinstance(facet, dict) and facet:
            return True
    return False


def merge_launcher_view(current_view: dict[str, Any], new_view: dict[str, Any]) -> dict[str, Any]:
    """Merge launcher views without losing meaningful prior task results."""
    carry_forward_keys = {
        "categories",
        "selected_categories",
        "category_tree",
        "report_summary",
        "export_summary",
        "available_filter_counts",
        "diagnostics_summary",
        "catalog_discovery",
        "intent_category_links",
    }
    merged = dict(current_view)
    for key, value in new_view.items():
        if value is None:
            continue
        if key in carry_forward_keys and value in ({}, [], ""):
            continue
        merged[key] = value
    return merged


def reset_result_state_for_onboarding(launcher_view: dict[str, Any]) -> dict[str, Any]:
    """Keep only onboarding-relevant launcher view fields."""
    allowed = {
        "category_tree",
        "selected_categories",
        "diagnostics_summary",
        "catalog_discovery",
        "intent_category_links",
    }
    return {key: value for key, value in launcher_view.items() if key in allowed}


def onboarding_result_message(summary: dict[str, Any]) -> str:
    """Build one onboarding completion message from task summary data."""
    category_count = int(summary.get("category_count") or 0)
    return f"Исследование магазина завершено. Найдено разделов: {category_count}"


def default_category_name(intent: str) -> str:
    """Return one fallback category name for the selected launcher intent."""
    return "Вино" if intent == "wine_catalog" else "Рыба"


def selected_export_categories(categories: list[str], intent: str) -> list[str]:
    """Normalize selected categories and provide one intent-aware fallback."""
    selected = [str(item).strip() for item in categories if str(item).strip()]
    return selected or [default_category_name(intent)]


def result_message(result: LocalTaskProcessResult) -> str:
    """Build one completion message for a normalized local task result."""
    if result.summary_text:
        return result.summary_text
    if result.manifest.task_name == "site_onboarding_discovery":
        return onboarding_result_message(dict(result.manifest.summary or {}))
    return f"Завершено: {result.manifest.task_name}"
