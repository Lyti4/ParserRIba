"""Build launcher filter facets directly from one fresh export JSON snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_available_filter_counts_from_export_json(json_path: str) -> dict[str, dict[str, int]]:
    """Read one export JSON file and build launcher filter counts from its products."""
    path = Path(str(json_path or ""))
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    products = payload.get("products")
    if not isinstance(products, list):
        return {}
    return build_available_filter_counts_from_products(products)


def build_available_filter_counts_from_products(products: list[Any]) -> dict[str, dict[str, int]]:
    """Build launcher filter counts directly from collected product cards."""
    product_dicts = [item for item in products if isinstance(item, dict)]
    if not product_dicts:
        return {}
    counts = {
        "suppliers": _counted_values(_supplier(item) for item in product_dicts),
        "brands": _counted_values(_text_value(item.get("brand")) for item in product_dicts),
        "categories": _counted_values(_text_value(item.get("category")) for item in product_dicts),
        "wine_styles": _counted_values(_text_value(item.get("subcategory")) for item in product_dicts),
        "alcohol_types": _counted_values(_alcohol_type(item) for item in product_dicts),
        "sugar_classes": _counted_values(_sugar_class(item) for item in product_dicts),
        "colors": _counted_values(_color(item) for item in product_dicts),
    }
    found_filters = _build_found_filters(product_dicts)
    if found_filters:
        counts["found_filters"] = found_filters
    return counts


def _supplier(item: dict[str, Any]) -> str:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    for key in ("supplier", "producer", "manufacturer", "vendor", "brand"):
        value = _text_value(raw_dict.get(key))
        if value:
            return value
    return _text_value(item.get("brand"))


def _alcohol_type(item: dict[str, Any]) -> str:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    return _text_value(raw_dict.get("alcohol_type") or item.get("alcohol_type"))


def _sugar_class(item: dict[str, Any]) -> str:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    return _text_value(raw_dict.get("sugar_class") or item.get("sugar_class"))


def _color(item: dict[str, Any]) -> str:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    return _text_value(raw_dict.get("color") or item.get("color"))


def _counted_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        rendered = _text_value(value)
        if not rendered:
            continue
        counts[rendered] = counts.get(rendered, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def _text_value(value: Any) -> str:
    return str(value or "").strip()


def _build_found_filters(products: list[Any]) -> dict[str, dict[str, int]]:
    """Build dynamic facets from extra raw product fields."""
    ignored = {
        "source_id",
        "field_sources",
        "categories",
        "description",
        "composition",
        "ingredients",
        "storage_conditions",
        "shelf_life",
        "supplier",
        "producer",
        "manufacturer",
        "vendor",
        "brand",
        "alcohol_type",
        "sugar_class",
        "color",
    }
    values_by_field: dict[str, list[str]] = {}
    for item in products:
        if not isinstance(item, dict):
            continue
        raw_data = item.get("raw_data")
        raw_dict = raw_data if isinstance(raw_data, dict) else {}
        for field_name, value in raw_dict.items():
            key = str(field_name or "").strip()
            if not key or key in ignored:
                continue
            for text in _iter_filter_values(value):
                values_by_field.setdefault(key, []).append(text)
    return {
        field_name: counts
        for field_name, values in sorted(values_by_field.items())
        if (counts := _counted_values(values))
    }


def _iter_filter_values(value: Any) -> list[str]:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = _text_value(value)
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_iter_filter_values(item))
        return result
    return []
