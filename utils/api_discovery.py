"""Safe API discovery helpers for catalog smoke investigations."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

from utils.api_first_extractor import summarize_api_first_candidates
from utils.interception import summarize_interception_events
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
    run: dict[str, Any] | None = None,
    attempt: dict[str, Any] | None = None,
    session: dict[str, Any] | None = None,
    rate_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the discovery report payload."""
    status_counts = Counter(str(event.get("status")) for event in events)
    product_events = [event for event in events if event.get("candidate_product_count", 0) > 0]
    empty_events = [event for event in events if event.get("empty_products_payload")]
    interception_summary = summarize_interception_events(events)
    api_first_summary = summarize_api_first_candidates(events)
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
    ]
    run = result.get("run") or {}
    attempt = result.get("attempt") or {}
    session = result.get("session") or {}
    rate_profile = result.get("rate_profile") or {}
    if run or attempt or session or rate_profile:
        lines.extend(["", "## Run Context"])
        if run:
            lines.append(f"- Run ID: {run.get('run_id', '')}")
            lines.append(f"- Mode: {run.get('mode', '')}")
        if attempt:
            lines.append(f"- Attempt status: {attempt.get('status', '')}")
            lines.append(f"- Attempt reason: {attempt.get('reason', '')}")
        if session:
            lines.append(f"- Session ID: {session.get('session_id', '')}")
            lines.append(f"- Session proxy: {session.get('proxy_url', '')}")
            lines.append(f"- Session success rate: {session.get('success_rate', '')}")
        if rate_profile:
            lines.append(f"- Rate profile: {rate_profile.get('name', '')}")
            lines.append(f"- Max concurrency: {rate_profile.get('max_concurrency', '')}")
    proxy_history = result.get("proxy_history") or {}
    if proxy_history:
        lines.extend(["", "## Proxy History"])
        lines.append(f"- Known proxies: {proxy_history.get('known_proxies', 0)}")
        lines.append(f"- Ranked proxies: {proxy_history.get('ranked_proxies', [])}")
        for item in (proxy_history.get("stats") or [])[:5]:
            lines.append(
                "- {proxy}: attempts={attempts}, success_rate={rate}, avg_responses={responses}, high_risk={risk}".format(
                    proxy=item.get("proxy", ""),
                    attempts=item.get("attempts", 0),
                    rate=item.get("success_rate", 0),
                    responses=item.get("avg_responses", 0),
                    risk=item.get("high_risk_attempts", 0),
                )
            )
    site_errors = result.get("site_errors") or {}
    if site_errors:
        lines.extend(["", "## Site Error Tracking"])
        lines.append(f"- Total tracked errors: {site_errors.get('total', 0)}")
        lines.append(f"- Severity counts: {site_errors.get('severity_counts', {})}")
        lines.append(f"- Source counts: {site_errors.get('source_counts', {})}")
        for event in (site_errors.get("events") or [])[:10]:
            lines.append(
                "- {severity} {source}/{code}: {message} (x{count})".format(
                    severity=event.get("severity", ""),
                    source=event.get("source", ""),
                    code=event.get("code", ""),
                    message=event.get("message", ""),
                    count=event.get("count", 1),
                )
            )
    interception = result.get("interception") or {}
    if interception:
        lines.extend(["", "## Interception"])
        lines.append(f"- Route counts: {interception.get('route_counts', {})}")
        replay_candidates = interception.get("replay_candidates") or []
        if replay_candidates:
            lines.append("- Replay candidates:")
            for item in replay_candidates[:5]:
                lines.append(
                    "  - {status}: products={count} {url}".format(
                        status=item.get("status"),
                        count=item.get("candidate_product_count", 0),
                        url=item.get("url", ""),
                    )
                )
        schema_candidates = interception.get("schema_candidates") or []
        if schema_candidates:
            lines.append("- Schema candidates:")
            for item in schema_candidates[:5]:
                hints = item.get("schema_hints") or {}
                lines.append(
                    "  - products={count}, keys={keys}".format(
                        count=item.get("candidate_product_count", 0),
                        keys=hints.get("top_keys", [])[:8],
                    )
                )
    api_first = result.get("api_first") or {}
    if api_first:
        lines.extend(["", "## API-first Extraction"])
        lines.append(f"- Candidate products: {api_first.get('candidate_count', 0)}")
        lines.append(f"- Ready for product model: {api_first.get('ready_count', 0)}")
        lines.append(f"- Missing fields: {api_first.get('missing_field_counts', {})}")
        coverage = api_first.get("field_coverage") or {}
        if coverage:
            lines.append(
                "- Field coverage: "
                + ", ".join(f"{field}={count}" for field, count in coverage.items())
            )
        for item in (api_first.get("samples") or [])[:5]:
            lines.append(
                "- {id} | {name} | price={price} | available={available} | missing={missing}".format(
                    id=item.get("source_id", ""),
                    name=item.get("name", ""),
                    price=item.get("price"),
                    available=item.get("availability"),
                    missing=item.get("missing_fields", []),
                )
            )
    lines.extend(["", "## Product Payload Candidates"])
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
