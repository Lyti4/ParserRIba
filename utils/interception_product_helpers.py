"""Product-candidate extraction helpers for interception diagnostics."""

from __future__ import annotations

from typing import Any

PRODUCT_NAME_KEYS = ("name", "title")
PRODUCT_ID_KEYS = ("id", "plu", "product_id", "productId", "sku", "slug")
PRODUCT_PRICE_KEYS = ("price", "current_price", "price_current", "regular_price", "prices")
PRODUCT_IMAGE_KEYS = ("image", "image_link", "image_links", "image_url", "imageUrl", "images", "picture", "pictures")
PRODUCT_LINK_KEYS = ("link", "url", "href", "product_url", "productUrl", "webUrl")
PRODUCT_AVAILABILITY_KEYS = ("availability", "available", "in_stock", "inStock", "is_available", "isAvailable", "stock")


def iter_dicts(value: Any) -> list[dict[str, Any]]:
    """Collect nested dictionaries from a JSON-like payload."""
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for item in value.values():
            found.extend(iter_dicts(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(iter_dicts(item))
    return found


def extract_product_candidates(payload: Any, limit: int = 10) -> list[dict[str, Any]]:
    """Extract likely product records from arbitrary catalog JSON."""
    candidates: list[dict[str, Any]] = []
    for item in iter_dicts(payload):
        keys = set(item)
        has_name = has_any(item, PRODUCT_NAME_KEYS)
        has_identity = has_any(item, PRODUCT_ID_KEYS)
        has_price = has_any(item, PRODUCT_PRICE_KEYS)
        if not has_name or not (has_identity or has_price):
            continue
        candidates.append(build_product_candidate(item, keys=keys))
        if len(candidates) >= limit:
            break
    return candidates


def infer_schema_hints(payload: Any, limit: int = 20) -> dict[str, Any]:
    """Infer product-related keys found in a JSON payload."""
    key_counts: dict[str, int] = {}
    product_like = 0
    for item in iter_dicts(payload):
        keys = set(str(key) for key in item)
        for key in keys:
            key_counts[key] = key_counts.get(key, 0) + 1
        if has_any(item, PRODUCT_NAME_KEYS) and (has_any(item, PRODUCT_ID_KEYS) or has_any(item, PRODUCT_PRICE_KEYS)):
            product_like += 1
    return {
        "product_like_objects": product_like,
        "top_keys": sorted(key_counts, key=key_counts.get, reverse=True)[:limit],
        "has_name_key": any(key in key_counts for key in PRODUCT_NAME_KEYS),
        "has_price_key": any(key in key_counts for key in PRODUCT_PRICE_KEYS),
        "has_image_key": any(key in key_counts for key in PRODUCT_IMAGE_KEYS),
        "has_link_key": any(key in key_counts for key in PRODUCT_LINK_KEYS),
        "has_availability_key": any(key in key_counts for key in PRODUCT_AVAILABILITY_KEYS),
    }


def has_any(item: dict[str, Any], keys: tuple[str, ...]) -> bool:
    """Return whether any of the provided keys is present in the item."""
    return any(key in item for key in keys)


def first_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first present raw value for one of the provided keys."""
    for key in keys:
        if key in item:
            return item[key]
    return ""


def field_sources(item: dict[str, Any]) -> dict[str, str]:
    """Return observed source keys for normalized product fields."""
    return {
        name: key
        for name, key in {
            "id": first_present_key(item, PRODUCT_ID_KEYS),
            "name": first_present_key(item, PRODUCT_NAME_KEYS),
            "price": first_present_key(item, PRODUCT_PRICE_KEYS),
            "image": first_present_key(item, PRODUCT_IMAGE_KEYS),
            "link": first_present_key(item, PRODUCT_LINK_KEYS),
            "availability": first_present_key(item, PRODUCT_AVAILABILITY_KEYS),
        }.items()
        if key
    }


def first_present_key(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first key that exists in the item."""
    for key in keys:
        if key in item:
            return key
    return ""


def build_product_candidate(item: dict[str, Any], *, keys: set[Any] | None = None) -> dict[str, Any]:
    """Build one normalized product candidate from a raw payload object."""
    candidate_keys = keys or set(item)
    return {
        "id": first_value(item, PRODUCT_ID_KEYS),
        "name": first_value(item, PRODUCT_NAME_KEYS),
        "price": first_value(item, PRODUCT_PRICE_KEYS),
        "image": first_nested_value(item, PRODUCT_IMAGE_KEYS),
        "link": first_nested_value(item, PRODUCT_LINK_KEYS),
        "availability": first_value(item, PRODUCT_AVAILABILITY_KEYS),
        "field_sources": field_sources(item),
        "keys": sorted(str(key) for key in candidate_keys)[:25],
    }


def first_nested_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first present nested value for one of the provided keys."""
    for key in keys:
        if key not in item:
            continue
        value = item[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        nested = first_nested_text(value)
        if nested:
            return nested
        return value
    return ""


def first_nested_text(value: Any) -> str:
    """Return the first nested text value from dict/list payloads."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for nested in value.values():
            found = first_nested_text(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = first_nested_text(item)
            if found:
                return found
    return ""
