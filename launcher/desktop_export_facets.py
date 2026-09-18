"""Build launcher filter facets directly from one fresh export JSON snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from launcher.desktop_filter_aliases import add_legacy_filter_count_aliases
from utils.product_display_fields import product_alcohol_type_name, product_brand_name, product_supplier_name
from utils.product_filter_facets import (
    build_found_filter_counts,
    counted_values,
    filter_text_value,
    is_attribute_container,
    iter_filter_values,
    iter_named_filter_values,
    iter_nested_filter_values,
    merge_filter_option_maps,
    option_pairs,
    raw_filter_data,
    text_value,
)


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
    subcategory_counts = _counted_values(_text_value(item.get("subcategory")) for item in product_dicts)
    counts = {
        "suppliers": _counted_values(_supplier(item) for item in product_dicts),
        "brands": _counted_values(product_brand_name(item) for item in product_dicts),
        "categories": _counted_values(_text_value(item.get("category")) for item in product_dicts),
        "subcategories": subcategory_counts,
        "alcohol_types": _counted_values(_alcohol_type(item) for item in product_dicts),
        "sugar_classes": _counted_values(_sugar_class(item) for item in product_dicts),
        "colors": _counted_values(_color(item) for item in product_dicts),
    }
    counts = add_legacy_filter_count_aliases(counts)
    found_filters = build_found_filter_counts(product_dicts)
    if found_filters:
        counts["found_filters"] = found_filters
    return counts


def _supplier(item: dict[str, Any]) -> str:
    return product_supplier_name(item)


def _alcohol_type(item: dict[str, Any]) -> str:
    return product_alcohol_type_name(item)


def _sugar_class(item: dict[str, Any]) -> str:
    raw_dict = raw_filter_data(item)
    return text_value(raw_dict.get("sugar_class") or item.get("sugar_class"))


def _color(item: dict[str, Any]) -> str:
    raw_dict = raw_filter_data(item)
    return text_value(raw_dict.get("color") or item.get("color"))


def _counted_values(values: Any) -> dict[str, int]:
    return counted_values(values)


def _option_pairs(raw_options: Any) -> list[tuple[str, int | None]]:
    return option_pairs(raw_options)


def _text_value(value: Any) -> str:
    return text_value(value)


def _build_found_filters(products: list[Any]) -> dict[str, dict[str, int]]:
    return build_found_filter_counts(products)


def _iter_filter_values(value: Any) -> list[str]:
    return iter_filter_values(value)


def _iter_named_filter_values(field_name: str, value: Any) -> list[tuple[str, str]]:
    return iter_named_filter_values(field_name, value)


def _iter_nested_filter_values(value: dict[str, Any]) -> list[tuple[str, str]]:
    return iter_nested_filter_values(value)


def _is_attribute_container(field_name: str) -> bool:
    return is_attribute_container(field_name)


def _filter_text_value(value: Any) -> str:
    return filter_text_value(value)


def _raw_filter_data(item: dict[str, Any]) -> dict[str, Any]:
    return raw_filter_data(item)
