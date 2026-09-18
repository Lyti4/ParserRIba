"""Local product filtering helpers for the desktop launcher workspace."""

from __future__ import annotations

from typing import Any

from models.launcher_state import LauncherAppState
from utils.product_display_fields import product_alcohol_type_name, product_supplier_name


def product_matches_export_filters(
    item: dict[str, Any],
    state: LauncherAppState,
    found_filters: dict[str, list[str]],
) -> bool:
    """Return whether a product belongs in the current filtered workspace."""
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    filters = state.filters
    style = _text_value(item.get("subcategory"))
    alcohol_type = product_alcohol_type_name(item)
    sugar_class = _text_value(raw_dict.get("sugar_class") or item.get("sugar_class"))
    color = _text_value(raw_dict.get("color") or item.get("color"))
    if not _matches_selected_values(_filter_field_values(item, "category"), filters.categories, filters.strict_missing):
        return False
    if not _matches_selected_values(_supplier_field_values(item), filters.suppliers, filters.strict_missing):
        return False
    if not _matches_selected_values(_filter_field_values(item, "brand"), filters.brands, filters.strict_missing):
        return False
    if not _matches_selected_text(style, filters.subcategories, filters.strict_missing):
        return False
    if not _matches_selected_text(alcohol_type, filters.alcohol_types, filters.strict_missing):
        return False
    if not _matches_selected_text(sugar_class, filters.sugar_classes, filters.strict_missing):
        return False
    if not _matches_selected_text(color, filters.colors, filters.strict_missing):
        return False
    if not _matches_found_filters(item, found_filters, filters.strict_missing):
        return False
    if not _matches_price_filter(item, filters.min_price, filters.max_price):
        return False
    if filters.in_stock is not None and bool(item.get("in_stock")) != filters.in_stock:
        return False
    return True


def locally_applicable_found_filters(
    products: list[dict[str, Any]],
    found_filters: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Keep only dynamic filters that can be matched against current products."""
    result: dict[str, list[str]] = {}
    for field_name, selected_values in found_filters.items():
        if not selected_values:
            continue
        if _is_known_filter_field(field_name):
            if any(_filter_field_values(item, field_name) for item in products):
                result[field_name] = selected_values
            continue
        if any(_filter_matches_field(item, field_name, selected_values) for item in products):
            result[field_name] = selected_values
    return result


def _matches_selected_text(actual_value: str, selected_values: list[str], strict_missing: bool) -> bool:
    return _matches_selected_values([actual_value] if actual_value else [], selected_values, strict_missing)


def _matches_selected_values(actual_values: list[str], selected_values: list[str], strict_missing: bool) -> bool:
    if not selected_values:
        return True
    if not actual_values:
        return not strict_missing
    return any(_value_matches(actual, selected) for actual in actual_values for selected in selected_values)


def _matches_price_filter(item: dict[str, Any], min_price: float | None, max_price: float | None) -> bool:
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


def _matches_found_filters(item: dict[str, Any], found_filters: dict[str, list[str]], strict_missing: bool) -> bool:
    if not found_filters:
        return True
    for field_name, selected_values in found_filters.items():
        if not selected_values:
            continue
        actual_values = _filter_field_values(item, field_name)
        if not actual_values:
            return False
        if not any(_value_matches(value, selected) for value in actual_values for selected in selected_values):
            return False
    return True


def _filter_field_values(item: dict[str, Any], field_name: str) -> list[str]:
    raw_data = item.get("raw_data")
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    key = str(field_name or "").strip()
    if key == "brand":
        return _dedupe_values([*_raw_values(item.get("brand")), *_raw_values(raw_dict.get("brand")), *_raw_values(item.get("name"))])
    if key in {"supplier", "producer", "manufacturer", "vendor"}:
        return _dedupe_values(
            [
                *_raw_values(raw_dict.get("supplier")),
                *_raw_values(raw_dict.get("producer")),
                *_raw_values(raw_dict.get("manufacturer")),
                *_raw_values(raw_dict.get("vendor")),
                *_raw_values(raw_dict.get("brand")),
                *_raw_values(item.get("brand")),
                *_raw_values(item.get("name")),
            ]
        )
    if key == "category":
        return _dedupe_values(
            [
                *_raw_values(item.get("category")),
                *_raw_values(item.get("subcategory")),
                *_raw_values(raw_dict.get("category")),
                *_raw_values(raw_dict.get("categories")),
            ]
        )
    if key == "special_offers":
        return _special_offer_values(item, raw_dict)
    return _dedupe_values([*_raw_values(item.get(key)), *_raw_values(raw_dict.get(key))])


def _supplier_field_values(item: dict[str, Any]) -> list[str]:
    return _dedupe_values([product_supplier_name(item)])


def _special_offer_values(item: dict[str, Any], raw_data: dict[str, Any]) -> list[str]:
    for key in ("special_offers", "discount", "has_discount", "promo", "promotion", "old_price", "discount_percent"):
        value = raw_data.get(key)
        if value is True:
            return ["Да"]
        if value not in (None, False, "", [], {}):
            return ["Да", *_raw_values(value)]
    price = item.get("price")
    if isinstance(price, dict):
        old_price = price.get("old") or price.get("regular") or price.get("previous")
        current = price.get("current")
        try:
            if old_price is not None and current is not None and float(old_price) > float(current):
                return ["Да"]
        except (TypeError, ValueError):
            return []
    return []


def _is_known_filter_field(field_name: str) -> bool:
    return field_name in {"brand", "supplier", "producer", "manufacturer", "vendor", "category", "special_offers"}


def _filter_matches_field(item: dict[str, Any], field_name: str, selected_values: list[str]) -> bool:
    actual_values = _filter_field_values(item, field_name)
    return bool(actual_values) and any(_value_matches(actual, selected) for actual in actual_values for selected in selected_values)


def _value_matches(actual_value: str, selected_value: str) -> bool:
    actual = _normalized_match_text(actual_value)
    selected = _normalized_match_text(selected_value)
    if not actual or not selected:
        return False
    return actual == selected or selected in actual


def _normalized_match_text(value: str) -> str:
    return " ".join(str(value or "").casefold().replace("ё", "е").split())


def _dedupe_values(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(values) if value]


def _raw_values(value: Any) -> list[str]:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = _text_value(value)
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_raw_values(item))
        return result
    if isinstance(value, dict):
        for key in ("name", "title", "value", "label"):
            text = _text_value(value.get(key))
            if text:
                return [text]
        result = []
        for item in value.values():
            result.extend(_raw_values(item))
        return list(dict.fromkeys(result))
    return []


def _text_value(value: Any) -> str:
    return str(value or "").strip()
