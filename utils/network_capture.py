"""Safe network capture helpers for parser diagnostics."""

from __future__ import annotations

import re
from time import perf_counter
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from utils.api_discovery import (
    extract_product_candidates,
    is_interesting_api_url,
    safe_json_loads,
    summarize_event,
)
from utils.proxy import mask_proxy_url

DEFAULT_PROXY_PREFLIGHT_URL = "https://api.ipify.org?format=json"
SENSITIVE_QUERY_KEYS = (
    "access",
    "auth",
    "authorization",
    "cookie",
    "email",
    "key",
    "password",
    "phone",
    "refresh",
    "secret",
    "session",
    "sid",
    "token",
)


def sanitize_diagnostic_url(url: str, max_length: int = 260) -> str:
    """Mask sensitive query values before writing diagnostic URLs."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url[:max_length]
    safe_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_QUERY_KEYS):
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, value))
    sanitized = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))
    return sanitized[:max_length]


def payload_has_empty_products(payload: str) -> bool:
    """Detect product API payloads that explicitly contain empty product lists."""
    compact = re.sub(r"\s+", "", payload)
    empty_markers = (
        '"products":[]',
        '"productsList":[]',
        '"items":[]',
        '"results":[]',
        '"data":[]',
        '"productsResponse":null',
    )
    return compact == "[]" or any(marker in compact for marker in empty_markers)


def payload_preview(payload: str, max_length: int = 500) -> str:
    """Return a compact response preview for diagnostics."""
    compact = re.sub(r"\s+", " ", payload).strip()
    return compact[:max_length]


async def record_network_response(
    response: Any,
    network_events: list[dict[str, Any]],
    *,
    product_api_checker: Any,
) -> None:
    """Record a response and a small product API payload diagnostic when safe."""
    url = sanitize_diagnostic_url(str(response.url))
    event: dict[str, Any] = {
        "status": response.status,
        "url": url,
    }
    try:
        headers = await response.all_headers()
    except Exception:
        headers = {}
    content_type = str(headers.get("content-type", ""))
    if content_type:
        event["content_type"] = content_type.split(";")[0]
    content_length = str(headers.get("content-length", ""))
    if content_length.isdigit():
        event["content_length"] = int(content_length)
    if product_api_checker(url) and "json" in content_type.lower():
        try:
            payload = await response.text()
        except Exception as exc:
            event["payload_error"] = str(exc).splitlines()[0][:180]
        else:
            event["empty_products_payload"] = payload_has_empty_products(payload)
            event["payload_preview"] = payload_preview(payload)
    network_events.append(event)


async def record_network_failure(request: Any, network_events: list[dict[str, Any]]) -> None:
    """Record failed requests without leaking query secrets."""
    try:
        failure = request.failure or ""
    except Exception:
        failure = ""
    network_events.append(
        {
            "failure": str(failure or "unknown")[:180],
            "url": sanitize_diagnostic_url(str(request.url)),
        }
    )


async def record_api_discovery_response(response: Any, events: list[dict[str, Any]]) -> bool:
    """Capture safe response diagnostics for interesting catalog API calls."""
    url = sanitize_diagnostic_url(str(response.url), max_length=420)
    if not is_interesting_api_url(url):
        return False
    event: dict[str, Any] = {
        "method": response.request.method,
        "status": response.status,
        "url": url,
    }
    try:
        headers = await response.all_headers()
    except Exception:
        headers = {}
    content_type = str(headers.get("content-type", ""))
    event["content_type"] = content_type.split(";")[0] if content_type else ""
    if "json" in content_type.lower():
        try:
            payload_text = await response.text()
        except Exception as exc:
            event["error"] = str(exc).splitlines()[0][:200]
        else:
            payload = safe_json_loads(payload_text)
            event["empty_products_payload"] = payload_has_empty_products(payload_text)
            event["payload_preview"] = payload_preview(payload_text, max_length=700)
            if payload is not None:
                products = extract_product_candidates(payload)
                event["candidate_product_count"] = len(products)
                event["sample_products"] = products
    events.append(summarize_event(event))
    return True


async def run_proxy_preflight(
    page: Any,
    proxy_url: str,
    *,
    preflight_url: str = DEFAULT_PROXY_PREFLIGHT_URL,
) -> dict[str, Any]:
    """Check that the browser can pass a small request through the proxy."""
    if not proxy_url:
        return {"enabled": False, "ok": None, "url": preflight_url}
    started = perf_counter()
    result: dict[str, Any] = {
        "enabled": True,
        "ok": False,
        "url": preflight_url,
        "proxy": mask_proxy_url(proxy_url),
    }
    try:
        response = await page.goto(preflight_url, wait_until="domcontentloaded", timeout=30_000)
        body = await page.inner_text("body")
    except Exception as exc:
        result["error"] = str(exc).splitlines()[0][:240]
    else:
        result["status"] = response.status if response else None
        result["response_bytes"] = len(body.encode("utf-8", errors="ignore"))
        result["ok"] = bool(response and response.ok and '"ip"' in body)
        match = re.search(r'"ip"\s*:\s*"([^"]+)"', body)
        if match:
            result["ip"] = match.group(1)
    result["duration_ms"] = int((perf_counter() - started) * 1000)
    return result
