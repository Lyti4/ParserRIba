"""Result table shaping for desktop and browser launcher previews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from launcher.desktop_ui_text import REPORT_TABLE_HEADERS, RESULT_TABLE_HEADERS, display_stock_label
from launcher.desktop_state_readers import full_catalog_tree, product_items, report_summary
from models.launcher_state import LauncherAppState

ResultTableModel = dict[str, list[list[str]] | list[str]]


def build_result_table(state: LauncherAppState) -> ResultTableModel:
    """Build a normalized result table model for the current launcher state."""
    state_table = _table_from_products(product_items(state), state)
    if state_table["rows"]:
        return state_table
    json_table = _table_from_json_export(state.result.json_path, state)
    if json_table["rows"]:
        return json_table
    return _table_from_state_summary(state)


def _table_from_json_export(
    json_path: str,
    state: LauncherAppState,
) -> ResultTableModel:
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


def _table_from_products(
    products: list[dict[str, Any]],
    state: LauncherAppState,
) -> ResultTableModel:
    if not products:
        return {"headers": [], "rows": [], "product_ids": []}
    headers = RESULT_TABLE_HEADERS
    rows: list[list[str]] = []
    product_ids: list[str] = []
    for item in products:
        if not isinstance(item, dict):
            continue
        if not _matches_export_filters(item, state):
            continue
        product_id = str(item.get("id") or item.get("product_id") or "").strip()
        raw_data = item.get("raw_data")
        raw_dict = raw_data if isinstance(raw_data, dict) else {}
        price = item.get("price")
        price_value = ""
        if isinstance(price, dict) and price.get("current") is not None:
            price_value = str(price["current"])
        rows.append(
            [
                str(item.get("category") or ""),
                str(item.get("name") or ""),
                str(item.get("brand") or ""),
                str(raw_dict.get("supplier") or raw_dict.get("producer") or raw_dict.get("vendor") or item.get("brand") or ""),
                str(item.get("subcategory") or ""),
                str(raw_dict.get("alcohol_type") or ""),
                price_value,
                display_stock_label(bool(item.get("in_stock"))),
                str(item.get("product_link") or ""),
            ]
        )
        product_ids.append(product_id)
    return {"headers": headers, "rows": rows, "product_ids": product_ids}


def _table_from_state_summary(state: LauncherAppState) -> ResultTableModel:
    summary = report_summary(state)
    if not summary:
        catalog_table = _table_from_full_catalog(state)
        if catalog_table["rows"]:
            return catalog_table
        return {"headers": [], "rows": [], "product_ids": []}
    category_counts = summary.get("category_counts")
    supplier_counts = summary.get("supplier_counts")
    brand_counts = summary.get("brand_counts")
    if not isinstance(category_counts, dict):
        catalog_table = _table_from_full_catalog(state)
        if catalog_table["rows"]:
            return catalog_table
        return {"headers": [], "rows": [], "product_ids": []}
    headers = REPORT_TABLE_HEADERS
    rows: list[list[str]] = []
    for category_name, count in category_counts.items():
        rows.append(
            [
                str(category_name),
                str(int(count)),
                _top_count_label(supplier_counts),
                _top_count_label(brand_counts),
            ]
        )
    return {"headers": headers, "rows": rows, "product_ids": []}


def _table_from_full_catalog(state: LauncherAppState) -> ResultTableModel:
    tree = full_catalog_tree(state)
    if not tree:
        return {"headers": [], "rows": [], "product_ids": []}
    rows: list[list[str]] = []
    seen: set[tuple[str, str]] = set()
    _append_catalog_tree_rows(rows, tree, level=0, seen=seen)
    return {"headers": ["Уровень", "Раздел каталога", "URL", "Дочерних разделов"], "rows": rows, "product_ids": []}


def _append_catalog_tree_rows(rows: list[list[str]], nodes: list[Any], *, level: int, seen: set[tuple[str, str]]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        children = node.get("children")
        child_nodes = children if isinstance(children, list) else []
        name = str(node.get("name") or "").strip()
        url = str(node.get("url") or "").strip()
        key = (name.casefold(), url.casefold())
        if (name or url) and key not in seen:
            rows.append([str(level), name, url, str(len(child_nodes))])
            seen.add(key)
        _append_catalog_tree_rows(rows, child_nodes, level=level + 1, seen=seen)


def _top_count_label(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    pairs = sorted(((str(name), int(count)) for name, count in value.items()), key=lambda item: (-item[1], item[0]))
    name, count = pairs[0]
    return f"{name} ({count})"


def _matches_export_filters(item: dict[str, Any], state: LauncherAppState) -> bool:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    filters = state.filters
    supplier = _text_value(raw_dict.get("supplier") or raw_dict.get("producer") or raw_dict.get("vendor"))
    brand = _text_value(item.get("brand"))
    category = _text_value(item.get("category"))
    style = _text_value(item.get("subcategory"))
    alcohol_type = _text_value(raw_dict.get("alcohol_type") or item.get("alcohol_type"))
    sugar_class = _text_value(raw_dict.get("sugar_class") or item.get("sugar_class"))
    color = _text_value(raw_dict.get("color") or item.get("color"))
    if not _matches_selected_text(category, filters.categories, filters.strict_missing):
        return False
    if not _matches_selected_text(supplier, filters.suppliers, filters.strict_missing):
        return False
    if not _matches_selected_text(brand, filters.brands, filters.strict_missing):
        return False
    if not _matches_selected_text(style, filters.wine_styles, filters.strict_missing):
        return False
    if not _matches_selected_text(alcohol_type, filters.alcohol_types, filters.strict_missing):
        return False
    if not _matches_selected_text(sugar_class, filters.sugar_classes, filters.strict_missing):
        return False
    if not _matches_selected_text(color, filters.colors, filters.strict_missing):
        return False
    if not _matches_found_filters(raw_dict, filters.found_filters, filters.strict_missing):
        return False
    if not _matches_price_filter(item, filters.min_price, filters.max_price):
        return False
    if filters.in_stock is not None and bool(item.get("in_stock")) != filters.in_stock:
        return False
    return True


def _matches_selected_text(
    actual_value: str,
    selected_values: list[str],
    strict_missing: bool,
) -> bool:
    if not selected_values:
        return True
    if not actual_value:
        return not strict_missing
    return actual_value in selected_values


def _matches_price_filter(
    item: dict[str, Any],
    min_price: float | None,
    max_price: float | None,
) -> bool:
    if min_price is None and max_price is None:
        return True
    price = item.get("price")
    current = price.get("current") if isinstance(price, dict) else None
    try:
        price_value = float(current)
    except (TypeError, ValueError):
        return True
    if min_price is not None and price_value < min_price:
        return False
    if max_price is not None and price_value > max_price:
        return False
    return True


def _matches_found_filters(
    raw_data: dict[str, Any],
    found_filters: dict[str, list[str]],
    strict_missing: bool,
) -> bool:
    if not found_filters:
        return True
    for field_name, selected_values in found_filters.items():
        if not selected_values:
            continue
        actual_values = _raw_values(raw_data.get(field_name))
        if not actual_values:
            if strict_missing:
                return False
            continue
        if not any(value in selected_values for value in actual_values):
            return False
    return True


def _raw_values(value: Any) -> list[str]:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = _text_value(value)
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_raw_values(item))
        return result
    return []


def _text_value(value: Any) -> str:
    return str(value or "").strip()
