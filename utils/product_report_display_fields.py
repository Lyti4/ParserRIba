"""Readable product fields shared by report builders."""

from __future__ import annotations

from typing import Any

from models.schemas import Product
from utils.product_classification import classify_product_alcohol_type


def distinct_product_brand(product: Product) -> str:
    """Return brand only when it adds information beyond supplier."""
    raw = dict(product.raw_data or {})
    brand = str(product.brand or raw.get("brand") or "").strip()
    supplier = product_supplier(product)
    return brand if brand and brand.casefold() != supplier.casefold() else ""


def product_supplier(product: Product) -> str:
    """Return normalized supplier-like text for one product."""
    raw = dict(product.raw_data or {})
    for key in ("supplier", "producer", "manufacturer", "vendor", "brand"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(product.brand or "")


def readable_alcohol_type(raw_data: dict[str, Any], name: str, category: str) -> str:
    """Return readable alcohol type, ignoring old mojibake raw values."""
    value = _first_text(raw_data, ("alcohol_type",))
    if value and not looks_mojibake(value):
        return value
    return classify_product_alcohol_type(name, category)


def looks_mojibake(value: str) -> bool:
    """Return whether text looks like double-decoded Cyrillic."""
    return "Р" in value and any(marker in value for marker in ("Р ", "РЎ", "РІР", "СЊ"))


def _first_text(raw_data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw_data.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""
