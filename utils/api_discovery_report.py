"""Markdown report rendering helpers for API discovery output."""

from __future__ import annotations

from typing import Any


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
    _append_run_context(lines, result)
    _append_proxy_history(lines, result)
    _append_site_errors(lines, result)
    _append_interception(lines, result)
    _append_api_first(lines, result)
    _append_dom_link_evidence(lines, result)
    _append_product_payload_candidates(lines, result)
    _append_empty_payloads(lines, result)
    lines.append("")
    return "\n".join(lines)


def _append_run_context(lines: list[str], result: dict[str, Any]) -> None:
    run = result.get("run") or {}
    attempt = result.get("attempt") or {}
    session = result.get("session") or {}
    rate_profile = result.get("rate_profile") or {}
    if not (run or attempt or session or rate_profile):
        return
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


def _append_proxy_history(lines: list[str], result: dict[str, Any]) -> None:
    proxy_history = result.get("proxy_history") or {}
    if not proxy_history:
        return
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


def _append_site_errors(lines: list[str], result: dict[str, Any]) -> None:
    site_errors = result.get("site_errors") or {}
    if not site_errors:
        return
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


def _append_interception(lines: list[str], result: dict[str, Any]) -> None:
    interception = result.get("interception") or {}
    if not interception:
        return
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


def _append_api_first(lines: list[str], result: dict[str, Any]) -> None:
    api_first = result.get("api_first") or {}
    if not api_first:
        return
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
        lines.append("- Field coverage: " + ", ".join(f"{field}={count}" for field, count in coverage.items()))
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


def _append_dom_link_evidence(lines: list[str], result: dict[str, Any]) -> None:
    dom_link_evidence = result.get("dom_link_evidence") or {}
    if not dom_link_evidence:
        return
    lines.extend(["", "## DOM Link Evidence"])
    lines.append(f"- DOM product links: {dom_link_evidence.get('count', 0)}")
    lines.append(f"- API source ids: {dom_link_evidence.get('api_source_ids', [])}")
    lines.append(f"- Matched API ids: {dom_link_evidence.get('matched_api_source_ids', [])}")
    lines.append(f"- Unmatched DOM ids: {dom_link_evidence.get('unmatched_dom_product_ids', [])}")
    for item in (dom_link_evidence.get("sample_links") or [])[:5]:
        lines.append("- {href} | {title}".format(href=item.get("href", ""), title=item.get("title", "")))


def _append_product_payload_candidates(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Product Payload Candidates"])
    product_events = result.get("product_events") or []
    if not product_events:
        lines.extend(["", "No product payload candidates were captured."])
        return
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


def _append_empty_payloads(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Empty Payloads"])
    empty_events = result.get("empty_events") or []
    if not empty_events:
        lines.extend(["", "No empty product payloads were captured."])
        return
    for event in empty_events[:8]:
        lines.append(f"- {event.get('status')}: {event.get('url')}")
        preview = event.get("payload_preview", "")
        if preview:
            lines.append(f"  - {preview}")


def _sample_sources_suffix(item: dict[str, Any]) -> str:
    sample_products = item.get("sample_products") or []
    if not sample_products:
        return ""
    first = sample_products[0]
    sources = first.get("field_sources") if isinstance(first, dict) else None
    return f" | sources={sources}" if sources else ""
