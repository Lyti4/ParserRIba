"""Reusable Markdown sections for smoke reports."""

from __future__ import annotations

from typing import Any


def append_proxy_diagnostics(lines: list[str], proxy_diagnostics: dict[str, Any]) -> None:
    """Append proxy preflight, GeoIP and health details."""
    if not proxy_diagnostics:
        return
    preflight = proxy_diagnostics.get("preflight") or {}
    preflight_geoip = proxy_diagnostics.get("preflight_geoip") or {}
    health = proxy_diagnostics.get("health") or {}
    lines.extend(["", "## Proxy Diagnostics"])
    lines.extend(
        [
            f"- Preflight enabled: {preflight.get('enabled', False)}",
            f"- Preflight ok: {preflight.get('ok')}",
            f"- Preflight status: {preflight.get('status')}",
            f"- Preflight duration ms: {preflight.get('duration_ms', '')}",
            f"- Preflight response bytes: {preflight.get('response_bytes', '')}",
            f"- Preflight IP: {preflight.get('ip', '')}",
            f"- Proxy health: {health.get('status', '')}",
            f"- Proxy traffic risk: {health.get('traffic_risk', '')}",
        ]
    )
    if preflight.get("error"):
        lines.append(f"- Preflight error: {preflight.get('error')}")
    if preflight_geoip:
        lines.extend(
            [
                f"- Preflight GeoIP country: {preflight_geoip.get('country_iso', '')}",
                f"- Preflight GeoIP city: {preflight_geoip.get('city', '')}",
                f"- Preflight GeoIP timezone: {preflight_geoip.get('timezone', '')}",
            ]
        )
    notes = health.get("notes") or []
    if notes:
        lines.append("- Proxy notes:")
        for note in notes:
            lines.append(f"  - {note}")


def append_browser_environment(lines: list[str], browser_environment: dict[str, Any]) -> None:
    """Append report-safe browser runtime environment details."""
    if not browser_environment:
        return
    lines.extend(["", "## Browser Environment"])
    if browser_environment.get("error"):
        lines.append(f"- Error: {browser_environment.get('error')}")
    lines.extend(
        [
            f"- Timezone: {browser_environment.get('timezone', '')}",
            f"- Language: {browser_environment.get('language', '')}",
            f"- Languages: {', '.join(browser_environment.get('languages') or [])}",
            f"- Platform: {browser_environment.get('platform', '')}",
            f"- Webdriver: {browser_environment.get('webdriver')}",
            f"- Geolocation API: {browser_environment.get('geolocation_api')}",
            f"- Geolocation permission: {browser_environment.get('geolocation_permission', '')}",
            f"- WebRTC API: {browser_environment.get('webrtc_api')}",
            f"- External IP matches preflight: {browser_environment.get('external_ip_matches_preflight')}",
            f"- Timezone matches preflight GeoIP: {browser_environment.get('timezone_matches_preflight_geoip')}",
        ]
    )
    screen = browser_environment.get("screen") or {}
    viewport = browser_environment.get("viewport") or {}
    if screen:
        lines.append(f"- Screen: {screen.get('width')}x{screen.get('height')}")
    if viewport:
        lines.append(f"- Viewport: {viewport.get('width')}x{viewport.get('height')}")


def append_manual_phase_network(lines: list[str], manual_phase_network: dict[str, Any]) -> None:
    """Append network counters split around manual captcha solving."""
    if not manual_phase_network:
        return
    lines.extend(["", "## Manual Phase Network"])
    for key, title in (
        ("before_prompt", "Before manual prompt"),
        ("during_manual", "During manual solving"),
        ("post_manual_wait", "After Enter wait"),
    ):
        summary = manual_phase_network.get(key) or {}
        lines.append(
            "- {title}: responses={responses}, failures={failures}, statuses={statuses}".format(
                title=title,
                responses=summary.get("responses", 0),
                failures=summary.get("failure_counts", {}),
                statuses=summary.get("status_counts", {}),
            )
        )
