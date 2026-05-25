"""Pure helpers for desktop launcher controller orchestration."""

from __future__ import annotations

import json
from datetime import datetime
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
    captured_payloads: list[dict[str, Any]] | None = None,
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
    artifact_paths = dict(last_result.manifest.artifact_paths or {})
    combined_json_path = write_combined_export_payload(
        last_result=last_result,
        selected_categories=selected_categories,
        captured_payloads=list(captured_payloads or []),
    )
    if combined_json_path:
        artifact_paths["json_path"] = combined_json_path
    manifest = last_result.manifest.model_copy(update={"summary": summary, "artifact_paths": artifact_paths})
    return build_local_task_process_result(
        manifest=manifest,
        stdout=last_result.stdout,
        stderr=last_result.stderr,
    )


def capture_export_payload(result: LocalTaskProcessResult) -> dict[str, Any] | None:
    """Read one export JSON payload while it still represents the finished category."""
    artifacts = dict(result.manifest.artifact_paths or {})
    path = Path(str(artifacts.get("json_path") or ""))
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_combined_export_payload(
    *,
    last_result: LocalTaskProcessResult,
    selected_categories: list[str],
    captured_payloads: list[dict[str, Any]],
) -> str:
    """Write one launcher-visible JSON for a multi-category export."""
    products = _merged_payload_products(captured_payloads)
    if not products:
        return ""
    artifacts = dict(last_result.manifest.artifact_paths or {})
    last_json_path = Path(str(artifacts.get("json_path") or ""))
    if not last_json_path.parent.exists():
        return ""
    payload = dict(captured_payloads[-1])
    payload["category"] = ", ".join(selected_categories)
    payload["categories"] = list(selected_categories)
    payload["products"] = products
    payload["products_count"] = len(products)
    payload["combined_export"] = True
    payload["combined_from_categories"] = list(selected_categories)
    payload["exported_at"] = datetime.now().isoformat(timespec="seconds")
    export_summary = dict(payload.get("export_summary") or {})
    export_summary["products_count"] = len(products)
    export_summary["categories"] = list(selected_categories)
    payload["export_summary"] = export_summary
    target_path = last_json_path.with_name(f"{last_json_path.stem}_selected.json")
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target_path)


def _merged_payload_products(captured_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for payload in captured_payloads:
        raw_products = payload.get("products")
        if not isinstance(raw_products, list):
            continue
        for item in raw_products:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("product_id") or item.get("product_link") or "").strip()
            if not key:
                key = f"row:{len(products)}"
            if key in seen:
                continue
            seen.add(key)
            products.append(dict(item))
    return products


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
        "full_catalog_tree",
        "full_catalog_links",
        "full_catalog_count",
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
        "full_catalog_tree",
        "full_catalog_links",
        "full_catalog_count",
        "diagnostics_summary",
        "catalog_discovery",
        "intent_category_links",
    }
    return {key: value for key, value in launcher_view.items() if key in allowed}


def onboarding_result_message(summary: dict[str, Any]) -> str:
    """Build one onboarding completion message from task summary data."""
    category_count = int(summary.get("category_count") or 0)
    full_catalog_count = int(summary.get("full_catalog_count") or 0)
    if full_catalog_count:
        return (
            "Исследование магазина завершено. "
            f"Выбранных разделов: {category_count}. "
            f"Полный каталог: {full_catalog_count} URL."
        )
    return f"Исследование магазина завершено. Найдено разделов: {category_count}"


def default_category_name(intent: str) -> str:
    """Return one fallback category name for the selected launcher intent."""
    return "Вино" if intent == "wine_catalog" else "Рыба"


def selected_export_categories(categories: list[str], intent: str) -> list[str]:
    """Normalize selected categories for discovery-first export actions."""
    del intent
    selected: list[str] = []
    for item in categories:
        category_name = str(item).strip()
        if category_name and category_name not in selected:
            selected.append(category_name)
    return selected


def selected_export_targets(
    categories: list[str],
    selected_catalog_nodes: list[dict[str, Any]],
    intent: str,
) -> list[dict[str, str]]:
    """Build explicit export targets with catalog URLs when the tree has them."""
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for node in selected_catalog_nodes:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "").strip()
        url = str(node.get("url") or "").strip()
        if not name:
            continue
        key = url or name
        if key in seen:
            continue
        seen.add(key)
        selected.append({"name": name, "url": url})
    if selected:
        return selected
    return [{"name": name, "url": ""} for name in selected_export_categories(categories, intent)]


def result_message(result: LocalTaskProcessResult) -> str:
    """Build one completion message for a normalized local task result."""
    if result.summary_text:
        return result.summary_text
    if result.manifest.task_name == "site_onboarding_discovery":
        return onboarding_result_message(dict(result.manifest.summary or {}))
    return f"Завершено: {result.manifest.task_name}"
