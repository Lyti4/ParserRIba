"""Safe API discovery helpers for catalog smoke investigations."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from utils.api_first_extractor import summarize_api_first_candidates
from utils.api_discovery_report import build_markdown_report
from utils.interception import (PRODUCT_ID_KEYS, PRODUCT_NAME_KEYS, PRODUCT_PRICE_KEYS,
                                build_product_candidate, iter_dicts, safe_json_loads,
                                summarize_interception_events)
from utils.proxy import mask_proxy_url

API_HOST_MARKERS = ("//5d.5ka.ru/", "//5ka.ru/")
API_PATH_MARKERS = ("/api/catalog", "/api/products", "/api/search", "/api/orders")


def is_interesting_api_url(url: str) -> bool:
    """Return True for catalog/product API URLs worth capturing."""
    lowered = url.lower()
    return any(host in lowered for host in API_HOST_MARKERS) and any(path in lowered for path in API_PATH_MARKERS)


def extract_product_candidates(payload: Any, limit: int = 10) -> list[dict[str, Any]]:
    """Extract likely product records from arbitrary catalog JSON."""
    candidates: list[dict[str, Any]] = []
    for item in iter_dicts(payload):
        has_name = any(key in item for key in PRODUCT_NAME_KEYS)
        has_identity = any(key in item for key in PRODUCT_ID_KEYS)
        has_price = any(key in item for key in PRODUCT_PRICE_KEYS)
        if not has_name or not (has_identity or has_price):
            continue
        candidate = build_product_candidate(item)
        candidate["slug"] = str(item.get("slug") or "")
        candidates.append(candidate)
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
    run: dict[str, Any] | None = None,
    attempt: dict[str, Any] | None = None,
    session: dict[str, Any] | None = None,
    rate_profile: dict[str, Any] | None = None,
    dom_link_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the discovery report payload."""
    status_counts = Counter(str(event.get("status")) for event in events)
    product_events = [event for event in events if event.get("candidate_product_count", 0) > 0]
    empty_events = [event for event in events if event.get("empty_products_payload")]
    interception_summary = summarize_interception_events(events)
    api_first_summary = summarize_api_first_candidates(events)
    dom_link_summary = _summarize_dom_link_evidence(dom_link_evidence, api_first_summary)
    api_first_summary = summarize_api_first_candidates(events, dom_link_summary.get("links_by_id") or {})
    dom_link_summary = _summarize_dom_link_evidence(dom_link_evidence, api_first_summary)
    result = {
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
        "interception": interception_summary,
        "api_first": api_first_summary,
        "dom_link_evidence": dom_link_summary,
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }
    if run:
        result["run"] = run
    if attempt:
        result["attempt"] = attempt
    if session:
        result["session"] = session
    if rate_profile:
        result["rate_profile"] = rate_profile
    return result

def _summarize_dom_link_evidence(dom_link_evidence: dict[str, Any] | None, api_first: dict[str, Any]) -> dict[str, Any]:
    if not dom_link_evidence:
        return {}
    links_by_id = {
        str(key): str(value)
        for key, value in (dom_link_evidence.get("links_by_id") or {}).items()
        if str(key) and str(value)
    }
    if not links_by_id:
        sample_links = dom_link_evidence.get("sample_links") or []
        product_ids = dom_link_evidence.get("product_ids") or []
        for product_id, item in zip(product_ids, sample_links):
            if not isinstance(item, dict):
                continue
            href = str(item.get("href") or "")
            if str(product_id) and href:
                links_by_id[str(product_id)] = href
    api_source_ids = sorted(
        {
            str(item.get("source_id"))
            for item in (api_first.get("samples") or [])
            if str(item.get("source_id") or "")
        }
    )
    product_ids = [str(value) for value in (dom_link_evidence.get("product_ids") or []) if str(value)]
    matched = [value for value in product_ids if value in api_source_ids]
    unmatched = [value for value in product_ids if value not in api_source_ids]
    return {
        "count": int(dom_link_evidence.get("count", 0)),
        "sample_links": dom_link_evidence.get("sample_links", [])[:10],
        "product_ids": product_ids[:20],
        "links_by_id": links_by_id,
        "api_source_ids": api_source_ids[:20],
        "matched_api_source_ids": matched[:20],
        "unmatched_dom_product_ids": unmatched[:20],
    }
