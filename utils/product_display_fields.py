"""Shared product display fields for launcher tables and filters."""

from __future__ import annotations

from typing import Any

from utils.product_classification import classify_product_alcohol_type
from utils.product_name_branding import derive_supplier_from_product_name


def product_supplier_name(item: dict[str, Any]) -> str:
    """Return the best local supplier/brand label for one product row."""
    raw = _raw_dict(item)
    for key in ("supplier", "producer", "manufacturer", "vendor", "brand"):
        value = _text(raw.get(key))
        if value:
            return value
    return _text(item.get("brand")) or derive_supplier_from_product_name(item.get("name"))


def product_brand_name(item: dict[str, Any]) -> str:
    """Return a visible brand value, falling back to the supplier label."""
    raw = _raw_dict(item)
    return _text(item.get("brand")) or _text(raw.get("brand")) or product_supplier_name(item)


def product_alcohol_type_name(item: dict[str, Any]) -> str:
    """Return a readable alcohol type, deriving it when stored raw data is broken."""
    raw = _raw_dict(item)
    value = _text(raw.get("alcohol_type") or item.get("alcohol_type"))
    if value and not _looks_mojibake(value):
        return value
    return classify_product_alcohol_type(str(item.get("name") or ""), str(item.get("category") or ""))


def product_type_name(item: dict[str, Any]) -> str:
    """Return a readable mini-catalog/type value for a product row."""
    raw = _raw_dict(item)
    subcategory = _text(item.get("subcategory"))
    if subcategory and not _looks_mojibake(subcategory):
        return subcategory
    return _text(raw.get("product_type"))


def _raw_dict(item: dict[str, Any]) -> dict[str, Any]:
    raw_data = item.get("raw_data")
    return raw_data if isinstance(raw_data, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _looks_mojibake(value: str) -> bool:
    return "Р" in value and any(marker in value for marker in ("Рђ", "Р‘", "СЊ", "С‹", "СЂ"))
