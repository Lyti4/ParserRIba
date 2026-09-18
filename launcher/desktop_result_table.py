"""Result table shaping for desktop and browser launcher previews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from launcher.desktop_product_filtering import locally_applicable_found_filters, product_matches_export_filters
from launcher.desktop_state_readers import product_items, report_summary
from launcher.desktop_ui_text import REPORT_TABLE_HEADERS, RESULT_TABLE_HEADERS, display_stock_label
from models.launcher_state import LauncherAppState
from utils.product_display_fields import product_supplier_name, product_type_name

ResultTableModel = dict[str, list[list[str]] | list[str]]


def build_result_table(state: LauncherAppState) -> ResultTableModel:
    """Build a normalized result table model for the current launcher state."""
    products = product_items(state)
    if products:
        return _table_from_products(products, state)
    if _is_empty_product_export(state):
        return {"headers": [], "rows": [], "product_ids": []}
    json_table = _table_from_json_export(state.result.json_path, state)
    if json_table["headers"] or json_table["rows"]:
        return json_table
    return _table_from_state_summary(state)


def _is_empty_product_export(state: LauncherAppState) -> bool:
    if str(state.task.task_kind or "") != "product_export" and state.task.task_name != "store_catalog_export":
        return False
    summary = state.result.summary
    if int(summary.get("products_count") or 0) != 0:
        return False
    attempt = summary.get("attempt")
    return isinstance(attempt, dict) and bool(attempt.get("reason"))


def _table_from_json_export(json_path: str, state: LauncherAppState) -> ResultTableModel:
    path = Path(str(json_path or ""))
    if not path.exists():
        return {"headers": [], "rows": [], "product_ids": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"headers": [], "rows": [], "product_ids": []}
    products = payload.get("products")
    if not isinstance(products, list):
        return {"headers": [], "rows": [], "product_ids": []}
    return _table_from_products([item for item in products if isinstance(item, dict)], state)


def _table_from_products(products: list[dict[str, Any]], state: LauncherAppState) -> ResultTableModel:
    if not products:
        return {"headers": [], "rows": [], "product_ids": []}
    rows: list[list[str]] = []
    product_ids: list[str] = []
    found_filters = locally_applicable_found_filters(products, state.filters.found_filters)
    for item in products:
        if not isinstance(item, dict):
            continue
        if not product_matches_export_filters(item, state, found_filters):
            continue
        rows.append(_product_row(item))
        product_ids.append(str(item.get("id") or item.get("product_id") or "").strip())
    return {"headers": RESULT_TABLE_HEADERS, "rows": rows, "product_ids": product_ids}


def _product_row(item: dict[str, Any]) -> list[str]:
    price = item.get("price")
    price_value = str(price["current"]) if isinstance(price, dict) and price.get("current") is not None else ""
    return [
        str(item.get("category") or ""),
        str(item.get("name") or ""),
        product_supplier_name(item),
        product_type_name(item),
        price_value,
        display_stock_label(bool(item.get("in_stock"))),
        str(item.get("product_link") or ""),
    ]


def _table_from_state_summary(state: LauncherAppState) -> ResultTableModel:
    summary = report_summary(state)
    if not summary:
        return {"headers": [], "rows": [], "product_ids": []}
    category_counts = summary.get("category_counts")
    supplier_counts = summary.get("supplier_counts")
    if not isinstance(category_counts, dict):
        return {"headers": [], "rows": [], "product_ids": []}
    rows = [[str(category_name), str(int(count)), _top_count_label(supplier_counts)] for category_name, count in category_counts.items()]
    return {"headers": REPORT_TABLE_HEADERS, "rows": rows, "product_ids": []}


def _top_count_label(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    pairs = sorted(((str(name), int(count)) for name, count in value.items()), key=lambda item: (-item[1], item[0]))
    name, count = pairs[0]
    return f"{name} ({count})"
