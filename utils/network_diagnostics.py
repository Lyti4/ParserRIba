"""Network and proxy diagnostics for parser reports."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

CATALOG_DIAGNOSTIC_MARKERS = ("api", "catalog", "product", "products", "search", "plu", "xpvnsulc")
PRODUCT_API_HOSTS = ("5ka.ru", "5d.5ka.ru")
PRODUCT_API_PATH_MARKERS = ("/api/catalog", "/api/orders", "/api/products", "/api/search")


def is_catalog_diagnostic_url(url: Any) -> bool:
    """Return True when a URL is useful for catalog/network diagnostics."""
    lowered = str(url or "").lower()
    return any(marker in lowered for marker in CATALOG_DIAGNOSTIC_MARKERS)


def is_product_api_url(url: Any) -> bool:
    """Return True when a URL looks relevant to catalog/product diagnostics."""
    try:
        parts = urlsplit(str(url or ""))
    except ValueError:
        return False
    host = parts.netloc.lower()
    path = parts.path.lower()
    return any(host.endswith(item) for item in PRODUCT_API_HOSTS) and any(
        marker in path for marker in PRODUCT_API_PATH_MARKERS
    )


def build_network_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact network summary for smoke diagnostics."""
    status_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    error_samples: list[dict[str, Any]] = []
    catalog_samples: list[dict[str, Any]] = []
    product_api_samples: list[dict[str, Any]] = []
    empty_product_api_samples: list[dict[str, Any]] = []
    estimated_body_bytes = 0
    for event in events:
        failure = event.get("failure")
        if failure:
            failure_key = str(failure)
            failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1
            if len(error_samples) < 10:
                error_samples.append(event)
            continue
        status = event.get("status")
        status_key = str(status) if status is not None else "unknown"
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        estimated_body_bytes += int(event.get("content_length") or 0)
        if isinstance(status, int) and status >= 400 and len(error_samples) < 10:
            error_samples.append(event)
        if is_catalog_diagnostic_url(event.get("url", "")):
            catalog_samples.append(event)
        if is_product_api_url(event.get("url", "")):
            if len(product_api_samples) < 12:
                product_api_samples.append(event)
            if event.get("empty_products_payload") and len(empty_product_api_samples) < 8:
                empty_product_api_samples.append(event)
    return {
        "responses": len(events),
        "status_counts": status_counts,
        "failure_counts": failure_counts,
        "estimated_body_bytes": estimated_body_bytes,
        "error_samples": error_samples,
        "catalog_samples": catalog_samples[:15],
        "product_api_samples": product_api_samples,
        "empty_product_api_samples": empty_product_api_samples,
    }


def classify_proxy_health(
    *,
    proxy_enabled: bool,
    preflight: dict[str, Any],
    network: dict[str, Any],
    browser_external_ip: str,
) -> dict[str, Any]:
    """Classify practical proxy health signals without provider API access."""
    if not proxy_enabled:
        return {
            "status": "not_configured",
            "traffic_risk": "unknown",
            "notes": ["Proxy is not configured for this attempt."],
        }

    status_counts = network.get("status_counts") or {}
    failure_counts = network.get("failure_counts") or {}
    notes: list[str] = []
    status = "ok"
    traffic_risk = "low"

    if not preflight.get("ok"):
        status = "preflight_failed"
        traffic_risk = "high"
        notes.append("Proxy preflight failed before opening Pyaterochka.")
    auth_challenges = int(status_counts.get("407", 0))
    if auth_challenges > 0 and not preflight.get("ok"):
        status = "proxy_auth_failed"
        traffic_risk = "high"
        notes.append("HTTP 407 means proxy authentication or account access failed.")
    elif auth_challenges > 0:
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("A transient HTTP 407 appeared, but proxy preflight later succeeded.")
    if int(status_counts.get("429", 0)) > 0:
        status = "rate_limited"
        traffic_risk = "medium"
        notes.append("HTTP 429 suggests rate limiting by the site or proxy route.")
    server_errors = sum(int(status_counts.get(str(code), 0)) for code in range(500, 600))
    if server_errors:
        status = "upstream_errors" if status == "ok" else status
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("5xx responses can indicate unstable proxy route or upstream blocking.")
    if failure_counts:
        status = "network_failures" if status == "ok" else status
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Browser reported failed network requests.")
    if not browser_external_ip:
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Browser external IP check did not return an IP.")
    if network.get("responses", 0) < 5:
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Very few responses were observed; proxy or page load may have stopped early.")
    if not notes:
        notes.append("No obvious proxy traffic/auth symptoms detected in this run.")

    return {
        "status": status,
        "traffic_risk": traffic_risk,
        "notes": notes,
    }
