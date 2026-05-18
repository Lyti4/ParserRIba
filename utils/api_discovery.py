"""Safe API discovery helpers for catalog smoke investigations."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from utils.api_first_extractor import summarize_api_first_candidates
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
                sample_sources = _sample_sources_suffix(item)
                lines.append(
                    "  - {status}: products={count} {url}{sources}".format(
                        status=item.get("status"),
                        count=item.get("candidate_product_count", 0),
                        url=item.get("url", ""),
                        sources=sample_sources,
                    )
                )
        schema_candidates = interception.get("schema_candidates") or []
        if schema_candidates:
            lines.append("- Schema candidates:")
            for item in schema_candidates[:5]:
                hints = item.get("schema_hints") or {}
                sample_sources = _sample_sources_suffix(item)
                lines.append(
                    "  - products={count}, keys={keys}{sources}".format(
                        count=item.get("candidate_product_count", 0),
                        keys=hints.get("top_keys", [])[:8],
                        sources=sample_sources,
                    )
                )
    api_first = result.get("api_first") or {}
    if api_first:
        lines.extend(["", "## API-first Extraction"])
        lines.append(f"- Candidate products: {api_first.get('candidate_count', 0)}")
        lines.append(f"- Ready for product model: {api_first.get('ready_count', 0)}")
        lines.append(f"- Missing fields: {api_first.get('missing_field_counts', {})}")
        source_filter = api_first.get("source_filter") or {}
        if source_filter:
            lines.append(
                "- Source filter: mode={mode}, eligible={eligible}, excluded={excluded}".format(
                    mode=source_filter.get("mode", ""),
                    eligible=source_filter.get("eligible_events_count", 0),
                    excluded=source_filter.get("excluded_events_count", 0),
                )
            )
            excluded_urls = source_filter.get("excluded_urls") or []
            if excluded_urls:
                lines.append("- Excluded URLs:")
                for url in excluded_urls[:5]:
                    lines.append(f"  - {url}")
        coverage = api_first.get("field_coverage") or {}
        if coverage:
            lines.append(
                "- Field coverage: "
                + ", ".join(f"{field}={count}" for field, count in coverage.items())
            )
        mapper_readiness = api_first.get("mapper_readiness") or {}
        if mapper_readiness:
            lines.append(
                "- Mapper readiness: ready={ready}, missing={missing}".format(
                    ready=mapper_readiness.get("ready", False),
                    missing=mapper_readiness.get("missing_fields", []),
                )
            )
        link_evidence = api_first.get("link_evidence") or {}
        if link_evidence:
            lines.append(
                "- Link evidence: products_have_link_key={products_have_link_key}, eligible_with_link={eligible_with_link}, eligible_without_link={eligible_without_link}".format(
                    products_have_link_key=link_evidence.get("products_have_link_key", False),
                    eligible_with_link=link_evidence.get("eligible_product_events_with_link_key", 0),
                    eligible_without_link=link_evidence.get("eligible_product_events_without_link_key", 0),
                )
            )
            non_product_link_keys = link_evidence.get("non_product_link_keys") or []
            if non_product_link_keys:
                lines.append(f"- Non-product link keys: {non_product_link_keys}")
            non_product_link_urls = link_evidence.get("non_product_link_urls") or []
            if non_product_link_urls:
                lines.append("- Non-product link URLs:")
                for url in non_product_link_urls[:5]:
                    lines.append(f"  - {url}")
        for item in (api_first.get("samples") or [])[:5]:
            sources = item.get("field_sources")
            lines.append(
                "- {id} | {name} | price={price} | available={available} | missing={missing}{sources}".format(
                    id=item.get("source_id", ""),
                    name=item.get("name", ""),
                    price=item.get("price"),
                    available=item.get("availability"),
                    missing=item.get("missing_fields", []),
                    sources=f" | sources={sources}" if sources else "",
                )
            )
    dom_link_evidence = result.get("dom_link_evidence") or {}
    if dom_link_evidence:
        lines.extend(["", "## DOM Link Evidence"])
        lines.append(f"- DOM product links: {dom_link_evidence.get('count', 0)}")
        lines.append(f"- API source ids: {dom_link_evidence.get('api_source_ids', [])}")
        lines.append(f"- Matched API ids: {dom_link_evidence.get('matched_api_source_ids', [])}")
        lines.append(f"- Unmatched DOM ids: {dom_link_evidence.get('unmatched_dom_product_ids', [])}")
        for item in (dom_link_evidence.get("sample_links") or [])[:5]:
            lines.append(
                "- {href} | {title}".format(
                    href=item.get("href", ""),
                    title=item.get("title", ""),
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
            sources = product.get("field_sources")
            lines.append(
                "  - {id} | {name} | {price} | {link} | available={available}{sources}".format(
                    id=product.get("id", ""),
                    name=product.get("name", ""),
                    price=product.get("price", ""),
                    link=product.get("link", ""),
                    available=product.get("availability", ""),
                    sources=f" | sources={sources}" if sources else "",
                )
            )
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


def _sample_sources_suffix(item: dict[str, Any]) -> str:
    sample_products = item.get("sample_products") or []
    if not sample_products:
        return ""
    sources = sample_products[0].get("field_sources") if isinstance(sample_products[0], dict) else None
    return f" | sources={sources}" if sources else ""


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
