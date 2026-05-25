"""Low-level value extraction helpers for API-first candidate building."""

from __future__ import annotations

import hashlib
import re
from typing import Any

PRODUCT_MAPPER_REQUIRED_FIELDS = ("source_id", "name", "price", "link", "image", "availability")
API_FIRST_FILTER_MODE = "products_only"
LINK_EVIDENCE_KEYS = (
    "link",
    "url",
    "href",
    "product_url",
    "productUrl",
    "webUrl",
    "deeplink",
    "deep_link",
    "info_link",
    "slug",
)
PRODUCT_ID_KEYS = ("id", "plu", "product_id", "productId", "sku", "slug")
PRODUCT_NAME_KEYS = ("name", "title")
PRODUCT_PRICE_KEYS = ("price", "current_price", "price_current", "regular_price", "prices")
PRODUCT_IMAGE_KEYS = ("image", "image_link", "image_links", "image_url", "imageUrl")
PRODUCT_LINK_KEYS = ("link", "url", "href", "product_url", "productUrl", "webUrl")
PRODUCT_AVAILABILITY_KEYS = ("availability", "available", "in_stock", "inStock", "is_available", "isAvailable", "stock")


def dedupe_key(*, source_id: str, name: str, link: str) -> str:
    """Build a stable short dedupe key for one candidate."""
    stable = source_id or link or normalize_name(name)
    if not stable:
        stable = "unknown"
    digest = hashlib.sha1(stable.encode("utf-8", errors="ignore")).hexdigest()
    return digest[:16]


def normalize_name(value: str) -> str:
    """Normalize product names for candidate deduplication."""
    return re.sub(r"\s+", " ", value.strip().lower())


def first_string(sample: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first string-like value for one of the provided keys."""
    for key in keys:
        value = sample.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, list) and value:
            nested = first_nested_url(value)
            if nested:
                return nested
        if isinstance(value, dict):
            nested = first_nested_url(value)
            if nested:
                return nested
    return ""


def first_present_key(sample: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first key that exists in the sample."""
    for key in keys:
        if key in sample:
            return key
    return ""


def first_price(sample: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    """Return the first parseable price value for one of the provided keys."""
    for key in keys:
        if key in sample:
            price = extract_price(sample[key])
            if price is not None:
                return price
    return None


def first_availability(sample: dict[str, Any], keys: tuple[str, ...]) -> bool | None:
    """Return the first parseable availability value for one of the provided keys."""
    for key in keys:
        if key in sample:
            found = extract_availability(sample[key])
            if found is not None:
                return found
    return None


def first_nested_url(value: Any) -> str:
    """Return the first nested string-like URL from dict/list payloads."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for nested in value.values():
            found = first_nested_url(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = first_nested_url(item)
            if found:
                return found
    return ""


def extract_price(value: Any) -> float | None:
    """Extract one numeric price from nested API data."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        if match:
            return float(match.group(0))
        return None
    if isinstance(value, dict):
        for key in ("current", "regular", "value", "price", "amount"):
            if key in value:
                price = extract_price(value[key])
                if price is not None:
                    return price
        for nested in value.values():
            price = extract_price(nested)
            if price is not None:
                return price
    if isinstance(value, list):
        for item in value:
            price = extract_price(item)
            if price is not None:
                return price
    return None


def extract_availability(value: Any) -> bool | None:
    """Extract one availability flag from nested API data."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "available", "in_stock", "instock", "1"}:
            return True
        if normalized in {"false", "no", "unavailable", "out_of_stock", "outofstock", "0"}:
            return False
    if isinstance(value, dict):
        for key in ("available", "in_stock", "inStock", "is_available", "isAvailable", "stock", "quantity"):
            if key in value:
                found = extract_availability(value[key])
                if found is not None:
                    return found
    return None
