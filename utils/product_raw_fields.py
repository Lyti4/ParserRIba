"""Helpers for extracting useful raw product-card fields."""

from __future__ import annotations

import re
from typing import Any

from utils.interception import iter_dicts
from utils.product_raw_field_config import (
    ATTRIBUTE_CONTAINER_KEYS,
    ATTRIBUTE_FIELD_ALIASES,
    PRODUCT_FORM_KEYWORDS,
    PRODUCT_STATE_KEYWORDS,
    RAW_PRODUCT_FIELD_ALIASES,
    RAW_PRODUCT_FIELD_KEYS,
)
from utils.product_name_branding import derive_supplier_from_product_name


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
        canonical_key = canonical_attribute_key(key)
        if canonical_key != key and canonical_key not in raw_data and value not in ("", [], {}):
            raw_data[canonical_key] = value
    for key, value in derive_fields_from_product_name(first_raw_field_value(item, "name")).items():
        raw_data.setdefault(key, value)
    supplier = derive_supplier_from_product_name(first_raw_field_value(item, "name"))
    if supplier:
        raw_data.setdefault("supplier", supplier)
    return raw_data


def derive_fields_from_product_name(value: Any) -> dict[str, str]:
    """Derive useful filter fields from a product name when API fields are sparse."""
    name = str(value or "").strip()
    if not name:
        return {}
    raw_data: dict[str, str] = {}
    product_type = _product_type_from_name(name)
    if product_type:
        raw_data["product_type"] = product_type
    fat_percent = _first_match(r"(?<!\d)(\d{1,2}(?:[,.]\d)?)\s*%", name)
    if fat_percent:
        raw_data["fat_percent"] = f"{fat_percent.replace(',', '.')}%"
    weight = _measure_from_name(name, ("кг", "г", "гр"))
    if weight:
        raw_data["weight"] = weight
    volume = _measure_from_name(name, ("л", "мл"))
    if volume:
        raw_data["volume"] = volume
    product_state = _first_keyword_label(name, PRODUCT_STATE_KEYWORDS)
    if product_state:
        raw_data["product_state"] = product_state
    product_form = _first_keyword_label(name, PRODUCT_FORM_KEYWORDS)
    if product_form:
        raw_data["product_form"] = product_form
    return raw_data


def first_raw_field_value(item: dict[str, Any], key: str) -> Any:
    """Return the first useful value for a raw field from nested payload data."""
    for alias in _field_aliases(key):
        value = raw_filter_value(item.get(alias))
        if value not in ("", [], {}):
            return value
    for nested in iter_dicts(item):
        if nested is item:
            continue
        for alias in _field_aliases(key):
            if alias not in nested:
                continue
            value = raw_filter_value(nested.get(alias))
            if value not in ("", [], {}):
                return value
    return ""


def canonical_attribute_key(key: str) -> str:
    """Return the canonical raw field key for common human-readable attributes."""
    normalized = " ".join(str(key or "").casefold().replace("_", " ").replace("-", " ").split())
    return ATTRIBUTE_FIELD_ALIASES.get(normalized, str(key or "").strip())


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
        or value.get("field")
        or value.get("property")
    )
    raw_value = raw_filter_value(
        value.get("value")
        or value.get("values")
        or value.get("text")
        or value.get("description")
        or value.get("displayValue")
        or value.get("display_value")
    )
    if not name or raw_value in ("", [], {}):
        return _named_pairs_from_mapping(value)
    return [(str(name), raw_value)]


def _named_pairs_from_mapping(value: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return name/value pairs from compact attribute maps."""
    result: list[tuple[str, Any]] = []
    for raw_name, raw_value in value.items():
        name = str(raw_name or "").strip()
        if not name or name in {
            "name",
            "title",
            "label",
            "key",
            "code",
            "field",
            "property",
            "value",
            "values",
            "text",
            "description",
            "displayValue",
            "display_value",
        }:
            continue
        rendered = raw_filter_value(raw_value)
        if rendered not in ("", [], {}):
            result.append((name, rendered))
    return result


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


def _product_type_from_name(name: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)?", name)
    if len(words) < 2:
        return ""
    first = words[0]
    if first.casefold() in {"product", "товар"}:
        return ""
    if first.casefold() in {"мини", "mini"} and len(words) > 1:
        return f"{first} {words[1]}"
    return first

def _first_keyword_label(name: str, keywords: tuple[tuple[str, str], ...]) -> str:
    folded = name.casefold().replace("ё", "е")
    for keyword, label in keywords:
        if keyword.casefold().replace("ё", "е") in folded:
            return label
    return ""


def _measure_from_name(name: str, units: tuple[str, ...]) -> str:
    units_pattern = "|".join(re.escape(unit) for unit in units)
    match = re.search(rf"(?<!\d)(\d+(?:[,.]\d+)?)\s*({units_pattern})\b", name, flags=re.IGNORECASE)
    if not match:
        return ""
    number = match.group(1).replace(",", ".")
    unit = match.group(2).casefold()
    if unit == "гр":
        unit = "г"
    return f"{number} {unit}"


def _first_match(pattern: str, value: str) -> str:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _field_aliases(key: str) -> tuple[str, ...]:
    return (key, *RAW_PRODUCT_FIELD_ALIASES.get(key, ()))
