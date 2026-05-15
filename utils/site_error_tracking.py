"""Normalize browser, network, proxy and API errors into report events."""

from __future__ import annotations

from collections import Counter
from typing import Any


def build_site_error_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Build a compact error summary from one parser/smoke/discovery result."""
    events: list[dict[str, Any]] = []
    _add_navigation_error(events, result)
    _add_block_reason(events, result)
    _add_proxy_errors(events, result.get("proxy_diagnostics") or {})
    _add_network_errors(events, result.get("network") or {})
    _add_product_api_errors(events, result)
    _add_discovery_errors(events, result)
    _add_browser_observation_errors(events, result.get("browser_observations") or {})

    code_counts = Counter(str(event["code"]) for event in events)
    source_counts = Counter(str(event["source"]) for event in events)
    severity_counts = Counter(str(event["severity"]) for event in events)
    return {
        "total": len(events),
        "code_counts": dict(code_counts),
        "source_counts": dict(source_counts),
        "severity_counts": dict(severity_counts),
        "events": events[:30],
    }


def attach_site_error_summary(result: dict[str, Any]) -> None:
    """Attach a site error summary when a result contains diagnostic signals."""
    summary = build_site_error_summary(result)
    if summary["total"] > 0:
        result["site_errors"] = summary


def build_browser_observations(
    *,
    console_messages: list[Any] | None = None,
    network_requests: list[Any] | None = None,
) -> dict[str, Any]:
    """Normalize Playwright/Chrome DevTools MCP observations for reports."""
    return {
        "console_messages": [_normalize_console_message(item) for item in (console_messages or [])],
        "network_requests": [_normalize_network_request(item) for item in (network_requests or [])],
    }


def _add_navigation_error(events: list[dict[str, Any]], result: dict[str, Any]) -> None:
    navigation_error = str(result.get("navigation_error") or "")
    if navigation_error:
        events.append(
            _event(
                code="navigation_error",
                source="browser",
                severity="error",
                message=navigation_error.splitlines()[0][:220],
            )
        )


def _add_block_reason(events: list[dict[str, Any]], result: dict[str, Any]) -> None:
    reason = str(result.get("block_reason") or "")
    if not reason or reason == "ok":
        return
    severity = "warning"
    if "captcha" in reason or "antibot" in reason:
        severity = "error"
    events.append(_event(code=reason, source="challenge", severity=severity, message=reason))


def _add_proxy_errors(events: list[dict[str, Any]], diagnostics: dict[str, Any]) -> None:
    preflight = diagnostics.get("preflight") or {}
    health = diagnostics.get("health") or {}
    if preflight.get("enabled") and preflight.get("ok") is False:
        events.append(
            _event(
                code="proxy_preflight_failed",
                source="proxy",
                severity="error",
                message=str(preflight.get("error") or "Proxy preflight failed.")[:220],
            )
        )
    health_status = str(health.get("status") or "")
    if health_status and health_status not in {"ok", "not_configured"}:
        events.append(
            _event(
                code=f"proxy_{health_status}",
                source="proxy",
                severity="warning" if health.get("traffic_risk") != "high" else "error",
                message="; ".join(str(note) for note in (health.get("notes") or []))[:260],
            )
        )


def _add_network_errors(events: list[dict[str, Any]], network: dict[str, Any]) -> None:
    status_counts = network.get("status_counts") or {}
    failure_counts = network.get("failure_counts") or {}
    for status, count in status_counts.items():
        status_code = int(status) if str(status).isdigit() else 0
        if status_code < 400:
            continue
        code = _status_code_to_error(status_code)
        events.append(
            _event(
                code=code,
                source="network",
                severity="error" if status_code in {403, 407} or status_code >= 500 else "warning",
                message=f"HTTP {status_code} responses observed: {count}",
                count=int(count),
            )
        )
    for failure, count in failure_counts.items():
        events.append(
            _event(
                code="network_request_failed",
                source="network",
                severity="warning",
                message=str(failure)[:220],
                count=int(count),
            )
        )


def _add_product_api_errors(events: list[dict[str, Any]], result: dict[str, Any]) -> None:
    network = result.get("network") or {}
    if network.get("empty_product_api_samples"):
        events.append(
            _event(
                code="product_api_empty_payload",
                source="product_api",
                severity="warning",
                message="Product API returned an empty product payload.",
                count=len(network.get("empty_product_api_samples") or []),
            )
        )
    page_context = (result.get("product_api_diagnostics") or {}).get("page_context") or {}
    if page_context and not page_context.get("selected_store_detected"):
        events.append(
            _event(
                code="store_not_selected",
                source="page_context",
                severity="warning",
                message="Selected store was not detected in the page context.",
            )
        )


def _add_discovery_errors(events: list[dict[str, Any]], result: dict[str, Any]) -> None:
    if "events_count" not in result:
        return
    if int(result.get("events_count") or 0) == 0:
        events.append(
            _event(
                code="api_discovery_no_events",
                source="discovery",
                severity="warning",
                message="No API events were captured during the discovery window.",
            )
        )
    if int(result.get("product_events_count") or 0) == 0:
        events.append(
            _event(
                code="api_discovery_no_product_payload",
                source="discovery",
                severity="warning",
                message="No product payload candidates were captured.",
            )
        )


def _add_browser_observation_errors(events: list[dict[str, Any]], observations: dict[str, Any]) -> None:
    for item in observations.get("console_messages") or []:
        level = str(item.get("level") or "").lower()
        if level not in {"error", "warning", "warn"}:
            continue
        events.append(
            _event(
                code=f"browser_console_{'warning' if level == 'warn' else level}",
                source="mcp_console",
                severity="error" if level == "error" else "warning",
                message=str(item.get("text") or "")[:260],
            )
        )
    for item in observations.get("network_requests") or []:
        failure = str(item.get("failure") or item.get("error") or "")
        status = item.get("status")
        if failure:
            events.append(
                _event(
                    code="mcp_network_request_failed",
                    source="mcp_network",
                    severity="warning",
                    message=failure[:220],
                )
            )
            continue
        status_code = int(status) if str(status).isdigit() else 0
        if status_code >= 400:
            events.append(
                _event(
                    code=_status_code_to_error(status_code),
                    source="mcp_network",
                    severity="error" if status_code in {403, 407} or status_code >= 500 else "warning",
                    message=f"HTTP {status_code}: {item.get('url', '')}"[:260],
                )
            )

def _status_code_to_error(status_code: int) -> str:
    if status_code == 403:
        return "http_403_forbidden_or_challenge"
    if status_code == 407:
        return "http_407_proxy_auth"
    if status_code == 429:
        return "http_429_rate_limited"
    if status_code >= 500:
        return "http_5xx_upstream_error"
    return f"http_{status_code}"


def _normalize_console_message(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        level = item.get("level") or item.get("type") or item.get("severity") or ""
        text = item.get("text") or item.get("message") or item.get("value") or ""
        location = item.get("location") or item.get("url") or ""
        return {
            "level": str(level).lower(),
            "text": str(text),
            "location": str(location),
        }
    return {
        "level": _level_from_text(str(item)),
        "text": str(item),
        "location": "",
    }


def _normalize_network_request(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "method": str(item.get("method") or ""),
            "status": item.get("status") or item.get("status_code"),
            "url": str(item.get("url") or ""),
            "failure": str(item.get("failure") or item.get("error") or ""),
        }
    text = str(item)
    return {
        "method": "",
        "status": _status_from_text(text),
        "url": text[:260],
        "failure": text if "failed" in text.lower() or "error" in text.lower() else "",
    }


def _level_from_text(text: str) -> str:
    lowered = text.lower()
    if "error" in lowered or "exception" in lowered:
        return "error"
    if "warning" in lowered or "warn" in lowered:
        return "warning"
    return "info"


def _status_from_text(text: str) -> int | None:
    for token in text.replace(":", " ").replace(",", " ").split():
        if token.isdigit() and 100 <= int(token) <= 599:
            return int(token)
    return None


def _event(
    *,
    code: str,
    source: str,
    severity: str,
    message: str,
    count: int = 1,
) -> dict[str, Any]:
    return {
        "code": code,
        "source": source,
        "severity": severity,
        "message": message,
        "count": count,
    }
