"""Safe API discovery helpers for catalog smoke investigations."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

from utils.proxy import mask_proxy_url

API_HOST_MARKERS = ("//5d.5ka.ru/", "//5ka.ru/")
API_PATH_MARKERS = ("/api/catalog", "/api/products", "/api/search", "/api/orders")
PRODUCT_NAME_KEYS = {"name", "title"}
PRODUCT_ID_KEYS = {"id", "plu", "product_id", "productId", "slug"}
PRODUCT_PRICE_KEYS = {"price", "regular_price", "current_price", "price_current", "prices"}


def is_interesting_api_url(url: str) -> bool:
    """Return True for catalog/product API URLs worth capturing."""
    lowered = url.lower()
    return any(host in lowered for host in API_HOST_MARKERS) and any(
        path in lowered for path in API_PATH_MARKERS
    )


def safe_json_loads(payload: str) -> Any:
    """Parse JSON payloads and return None on malformed content."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


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
        has_name = bool(keys & PRODUCT_NAME_KEYS)
        has_identity = bool(keys & PRODUCT_ID_KEYS)
        has_price = bool(keys & PRODUCT_PRICE_KEYS)
        if not has_name or not (has_identity or has_price):
            continue
        candidates.append(
            {
                "id": item.get("id") or item.get("plu") or item.get("product_id") or item.get("productId") or "",
                "name": item.get("name") or item.get("title") or "",
                "price": item.get("price") or item.get("regular_price") or item.get("current_price") or "",
                "slug": item.get("slug") or "",
                "keys": sorted(str(key) for key in keys)[:25],
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def summarize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return the compact JSON-safe event shape used in reports."""
    return {
        "method": event.get("method", ""),
        "status": event.get("status"),
        "url": event.get("url", ""),
        "content_type": event.get("content_type", ""),
        "empty_products_payload": event.get("empty_products_payload"),
        "candidate_product_count": event.get("candidate_product_count", 0),
        "sample_products": event.get("sample_products", []),
        "payload_preview": event.get("payload_preview", ""),
        "error": event.get("error", ""),
    }


def build_discovery_result(
    *,
    category_name: str,
    category_url: str,
    proxy_url: str,
    geoip_enabled: bool,
    listen_seconds: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the discovery report payload."""
    status_counts = Counter(str(event.get("status")) for event in events)
    product_events = [event for event in events if event.get("candidate_product_count", 0) > 0]
    empty_events = [event for event in events if event.get("empty_products_payload")]
    return {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "listen_seconds": listen_seconds,
        "proxy_enabled": bool(proxy_url),
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "events_count": len(events),
        "status_counts": dict(status_counts),
        "product_events_count": len(product_events),
        "empty_events_count": len(empty_events),
        "events": events,
        "product_events": product_events[:10],
        "empty_events": empty_events[:10],
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_markdown_report(result: dict[str, Any]) -> str:
    """Build a compact human-readable discovery report."""
    lines = [
        "# Pyaterochka API Discovery Report",
        "",
        f"- Category: {result.get('category', '')}",
        f"- Category URL: {result.get('category_url', '')}",
        f"- Listen seconds: {result.get('listen_seconds', '')}",
        f"- Proxy enabled: {result.get('proxy_enabled', False)}",
        f"- Proxy: {result.get('proxy', '')}",
        f"- GeoIP enabled: {result.get('geoip_enabled', False)}",
        f"- Events captured: {result.get('events_count', 0)}",
        f"- Status counts: {result.get('status_counts', {})}",
        f"- Product events: {result.get('product_events_count', 0)}",
        f"- Empty events: {result.get('empty_events_count', 0)}",
        "",
        "## Product Payload Candidates",
    ]
    product_events = result.get("product_events") or []
    if not product_events:
        lines.append("")
        lines.append("No product payload candidates were captured.")
    for event in product_events:
        lines.append(f"- {event.get('status')}: {event.get('url')}")
        for product in event.get("sample_products", [])[:5]:
            lines.append(f"  - {product.get('id', '')} | {product.get('name', '')} | {product.get('price', '')}")
    lines.extend(["", "## Empty Payloads"])
    empty_events = result.get("empty_events") or []
    if not empty_events:
        lines.append("")
        lines.append("No empty product payloads were captured.")
    for event in empty_events[:8]:
        lines.append(f"- {event.get('status')}: {event.get('url')}")
        preview = event.get("payload_preview", "")
        if preview:
            lines.append(f"  - {preview}")
    lines.append("")
    return "\n".join(lines)
