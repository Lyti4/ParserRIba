"""Helpers for extracting useful raw product-card fields."""

from __future__ import annotations

from typing import Any

from utils.interception import iter_dicts

RAW_PRODUCT_FIELD_KEYS = (
    "brand",
    "supplier",
    "producer",
    "manufacturer",
    "vendor",
    "country",
    "country_of_origin",
    "origin_country",
    "composition",
    "description",
    "weight",
    "volume",
    "unit",
    "packaging",
    "fat",
    "protein",
    "carbohydrate",
    "calories",
    "shelf_life",
    "storage_conditions",
)

ATTRIBUTE_CONTAINER_KEYS = (
    "attributes",
    "characteristics",
    "properties",
    "parameters",
    "features",
    "specs",
    "product_properties",
    "productProperties",
)


def extract_raw_product_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Extract filterable and detail-worthy raw fields from one product payload."""
    raw_data: dict[str, Any] = {}
    for key in RAW_PRODUCT_FIELD_KEYS:
        value = first_raw_field_value(item, key)
        if value not in ("", [], {}):
            raw_data[key] = value
    for key, value in iter_named_attribute_fields(item):
        if key not in raw_data and value not in ("", [], {}):
            raw_data[key] = value
    return raw_data


def first_raw_field_value(item: dict[str, Any], key: str) -> Any:
    """Return the first useful value for a raw field from nested payload data."""
    value = raw_filter_value(item.get(key))
    if value not in ("", [], {}):
        return value
    for nested in iter_dicts(item):
        if nested is item or key not in nested:
            continue
        value = raw_filter_value(nested.get(key))
        if value not in ("", [], {}):
            return value
    return ""


def iter_named_attribute_fields(item: dict[str, Any]) -> list[tuple[str, Any]]:
    """Extract name/value attributes from common product-card containers."""
    result: list[tuple[str, Any]] = []
    for container_key in ATTRIBUTE_CONTAINER_KEYS:
        result.extend(named_attribute_pairs(item.get(container_key)))
    for nested in iter_dicts(item):
        if nested is item:
            continue
        for container_key in ATTRIBUTE_CONTAINER_KEYS:
            result.extend(named_attribute_pairs(nested.get(container_key)))
    return result


def named_attribute_pairs(value: Any) -> list[tuple[str, Any]]:
    """Return normalized name/value pairs from an attribute object or list."""
    if isinstance(value, list):
        result: list[tuple[str, Any]] = []
        for item in value:
            result.extend(named_attribute_pairs(item))
        return result
    if not isinstance(value, dict):
        return []
    name = raw_filter_value(
        value.get("name")
        or value.get("title")
        or value.get("label")
        or value.get("key")
        or value.get("code")
    )
    raw_value = raw_filter_value(
        value.get("value")
        or value.get("values")
        or value.get("text")
        or value.get("description")
    )
    if not name or raw_value in ("", [], {}):
        return []
    return [(str(name), raw_value)]


def raw_filter_value(value: Any) -> Any:
    """Return a compact scalar/list value suitable for raw card fields."""
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        result = []
        for item in value:
            rendered = raw_filter_value(item)
            if rendered not in ("", [], {}):
                result.append(rendered)
        return result
    if isinstance(value, dict):
        for key in ("name", "title", "value", "label"):
            if key in value:
                return raw_filter_value(value[key])
    return ""
