"""Helpers for building Pyaterochka Product exports."""

from __future__ import annotations

import re
from typing import Any

from models.schemas import Product
from scripts.discover_pyaterochka_api import DEFAULT_CATEGORY
from utils.category_intents import get_category_intent_resolver
from utils.interception import (
    PRODUCT_AVAILABILITY_KEYS,
    PRODUCT_PRICE_KEYS,
    build_product_candidate,
    iter_dicts,
)
from utils.wine_product_classification import (
    ALCOHOL_FREE,
    ALCOHOL_REGULAR,
    WINE_STYLE_CHAMPAGNE,
    WINE_STYLE_QUIET,
    WINE_STYLE_SANGRIA,
    WINE_STYLE_SPARKLING,
    WINE_STYLE_VERMOUTH,
    WINE_STYLE_WINE_DRINK,
    classify_wine_alcohol_type,
    classify_wine_style,
    extract_brand_from_payload,
    is_wine_product,
    merge_wine_raw_fields,
)


def build_products_from_discovery_result(result: dict[str, Any]) -> list[Product]:
    """Build normalized Product models from ready API-first samples."""
    products: list[Product] = []
    for sample in (result.get("api_first") or {}).get("samples") or []:
        if not isinstance(sample, dict) or sample.get("missing_fields"):
            continue
        link = str(sample.get("link") or "").strip()
        name = str(sample.get("name") or "").strip()
        price = sample.get("price")
        if not link or not name or price is None:
            continue
        category = str(result.get("category") or "").strip() or None
        alcohol_type = classify_wine_alcohol_type(name, category)
        products.append(
            Product(
                id=str(sample.get("source_id") or "").strip() or None,
                name=name,
                brand=extract_brand_from_payload(sample),
                price=float(price),
                image_url=(str(sample.get("image") or "").strip() or None),
                product_link=link,
                category=category,
                subcategory=classify_wine_style(name, category),
                in_stock=bool(sample.get("availability")),
                raw_data=merge_wine_raw_fields(
                    {
                        "source_id": str(sample.get("source_id") or "").strip(),
                        "field_sources": sample.get("field_sources") or {},
                    },
                    alcohol_type=alcohol_type,
                ),
            )
        )
    return products


def build_products_from_result(result: dict[str, Any]) -> list[Product]:
    """Build products from raw capture when available, otherwise diagnostics samples."""
    raw_items = result.get("raw_product_items") or []
    dom_links_by_id = ((result.get("dom_link_evidence") or {}).get("links_by_id")) or {}
    category = str(result.get("category") or "")
    if raw_items:
        return build_products_from_product_items(
            raw_items,
            category=category,
            dom_links_by_id=dom_links_by_id,
        )
    return build_products_from_discovery_result(result)


def resolve_export_category_names(
    category_name: str,
    available_categories: dict[str, str] | None = None,
    *,
    intent: str = "fish_catalog",
) -> list[str]:
    """Resolve target categories for one export run."""
    resolver = get_category_intent_resolver(intent)
    return resolver(category_name or DEFAULT_CATEGORY, available_categories)


def merge_products(products: list[Product]) -> list[Product]:
    """Deduplicate products by id while preserving category provenance."""
    merged_by_id: dict[str, Product] = {}
    categories_by_id: dict[str, list[str]] = {}
    for product in products:
        product_id = str(product.id or "").strip()
        if not product_id:
            continue
        category = str(product.category or "").strip()
        if product_id not in merged_by_id:
            raw_data = dict(product.raw_data or {})
            if category:
                raw_data["categories"] = [category]
                product.raw_data = raw_data
            merged_by_id[product_id] = product
            categories_by_id[product_id] = [category] if category else []
            continue

        existing = merged_by_id[product_id]
        categories = categories_by_id[product_id]
        if category and category not in categories:
            categories.append(category)
        if categories:
            raw_data = dict(existing.raw_data or {})
            raw_data["categories"] = categories
            existing.category = categories[0]
            existing.raw_data = raw_data
            existing.subcategory = existing.subcategory or classify_wine_style(
                existing.name,
                existing.category,
            )
    return list(merged_by_id.values())


def filter_products_for_intent(products: list[Product], intent: str) -> list[Product]:
    """Filter and normalize exported products for a specific catalog intent."""
    normalized = str(intent or "").strip().casefold()
    if normalized != "wine_catalog":
        return products

    filtered: list[Product] = []
    for product in products:
        if not is_wine_product(product):
            continue
        product.subcategory = classify_wine_style(product.name, product.category)
        alcohol_type = classify_wine_alcohol_type(product.name, product.category)
        product.raw_data = merge_wine_raw_fields(
            product.raw_data,
            alcohol_type=alcohol_type,
            intent_scope="wine_storefront",
        )
        filtered.append(product)
    return filtered


def extract_product_items_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Extract all product-like dicts from a raw products payload."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in iter_dicts(payload):
        if "name" not in item or "plu" not in item or "prices" not in item:
            continue
        product_id = str(item.get("plu") or "").strip()
        if not product_id or product_id in seen:
            continue
        seen.add(product_id)
        items.append(item)
    return items


def build_products_from_product_items(
    items: list[dict[str, Any]],
    *,
    category: str,
    dom_links_by_id: dict[str, str],
) -> list[Product]:
    """Build Product models from raw product API items."""
    products: list[Product] = []
    for item in items:
        source_id = str(item.get("plu") or "").strip()
        link = str(dom_links_by_id.get(source_id) or "").strip()
        if not source_id or not link:
            continue
        candidate = build_product_candidate(item)
        price = _extract_price_from_item(item)
        name = str(candidate.get("name") or "").strip()
        if not name or price is None:
            continue
        raw_sources = dict(candidate.get("field_sources") or {})
        field_sources = {
            "source_id": raw_sources.get("source_id") or raw_sources.get("id") or "",
            "name": raw_sources.get("name") or "",
            "price": raw_sources.get("price") or "",
            "image": raw_sources.get("image") or "",
            "availability": raw_sources.get("availability") or "",
            "link": "dom_product_href",
        }
        alcohol_type = classify_wine_alcohol_type(name, category)
        products.append(
            Product(
                id=source_id,
                name=name,
                brand=extract_brand_from_payload(item),
                price=price,
                image_url=(str(candidate.get("image") or "").strip() or None),
                product_link=link,
                category=category or None,
                subcategory=classify_wine_style(name, category),
                in_stock=_extract_availability_from_item(item),
                raw_data=merge_wine_raw_fields(
                    _build_raw_product_data(item, source_id=source_id, field_sources=field_sources),
                    alcohol_type=alcohol_type,
                ),
            )
        )
    return products


def _extract_price_from_item(item: dict[str, Any]) -> float | None:
    value = item.get("prices")
    if isinstance(value, dict):
        raw = value.get("regular")
        if raw is None:
            raw = value.get("current")
        if raw is None:
            raw = value.get("price")
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", "."))
            if match:
                return float(match.group(0))
    for key in PRODUCT_PRICE_KEYS:
        raw = item.get(key)
        if isinstance(raw, (int, float)):
            return float(raw)
    return None


def _extract_availability_from_item(item: dict[str, Any]) -> bool:
    for key in PRODUCT_AVAILABILITY_KEYS:
        if key not in item:
            continue
        value = item[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value > 0
    return True


def _build_raw_product_data(
    item: dict[str, Any],
    *,
    source_id: str,
    field_sources: dict[str, str],
) -> dict[str, Any]:
    """Keep useful raw product-card fields for filters and product details."""
    raw_data: dict[str, Any] = {
        "source_id": source_id,
        "field_sources": {
            key: value for key, value in field_sources.items() if value
        },
    }
    for key in (
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
    ):
        value = _raw_filter_value(item.get(key))
        if value not in ("", [], {}):
            raw_data[key] = value
    return raw_data


def _raw_filter_value(value: Any) -> Any:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        return [_raw_filter_value(item) for item in value if _raw_filter_value(item) not in ("", [], {})]
    if isinstance(value, dict):
        for key in ("name", "title", "value", "label"):
            if key in value:
                return _raw_filter_value(value[key])
    return ""
