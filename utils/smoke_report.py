"""Human-readable smoke test reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_pyaterochka_smoke_report(result: dict[str, Any]) -> str:
    """Build a compact Markdown report for a Pyaterochka smoke result."""
    status = "blocked" if result.get("blocked") else "ok"
    lines = [
        "# Pyaterochka Camoufox Smoke Report",
        "",
        f"- Status: {status}",
        f"- Block reason: {result.get('block_reason', 'unknown')}",
        f"- Attempt: {result.get('attempt', '')} / {result.get('max_attempts', '')}",
        f"- HTTP status: {result.get('http_status')}",
        f"- Cards found: {result.get('cards_found', 0)}",
        f"- Final URL: {result.get('final_url', '')}",
        f"- HTML size: {result.get('html_size', 0)}",
        f"- Proxy enabled: {result.get('proxy_enabled', False)}",
        f"- Proxy: {result.get('proxy', '')}",
        f"- Browser external IP: {result.get('browser_external_ip', '')}",
        f"- GeoIP enabled: {result.get('geoip_enabled', False)}",
    ]
    fingerprint = result.get("fingerprint") or {}
    if fingerprint:
        lines.extend(
            [
                f"- Fingerprint engine: {fingerprint.get('engine', '')}",
                f"- Fingerprint OS: {fingerprint.get('os', '')}",
                f"- Locale: {fingerprint.get('locale', '')}",
                f"- Camoufox humanize: {fingerprint.get('humanize', False)}",
            ]
        )
    behavior_profile = result.get("behavior_profile") or {}
    if behavior_profile:
        lines.extend(
            [
                f"- Behavior profile: {behavior_profile.get('name', '')}",
                "- Behavior scroll: {min_steps}-{max_steps} steps, {min_delta}-{max_delta}px".format(
                    min_steps=behavior_profile.get("scroll_steps_min", ""),
                    max_steps=behavior_profile.get("scroll_steps_max", ""),
                    min_delta=behavior_profile.get("scroll_delta_min", ""),
                    max_delta=behavior_profile.get("scroll_delta_max", ""),
                ),
                f"- Behavior hover cards: {behavior_profile.get('hover_cards', '')}",
            ]
        )

    navigation_error = result.get("navigation_error")
    if navigation_error:
        lines.append(f"- Navigation error: {str(navigation_error).splitlines()[0]}")

    reason = str(result.get("block_reason", ""))
    if "captcha" in reason:
        lines.extend(
            [
                "",
                "## Manual Action",
                "Captcha detected. Run visual mode with images enabled and solve it in Camoufox:",
                "",
                "```powershell",
                "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\run_pyaterochka_visual.ps1",
                "```",
            ]
        )

    attempts = result.get("attempts") or []
    if attempts:
        lines.extend(["", "## Attempts"])
        for attempt in attempts:
            lines.append(
                "- #{attempt}: blocked={blocked}, reason={reason}, cards={cards}, proxy={proxy}".format(
                    attempt=attempt.get("attempt", ""),
                    blocked=attempt.get("blocked", ""),
                    reason=attempt.get("block_reason", ""),
                    cards=attempt.get("cards_found", 0),
                    proxy=attempt.get("proxy", ""),
                )
            )

    network = result.get("network") or {}
    if network:
        lines.extend(
            [
                "",
                "## Network",
                f"- Responses: {network.get('responses', 0)}",
                f"- Status counts: {network.get('status_counts', {})}",
            ]
        )
        error_samples = network.get("error_samples") or []
        if error_samples:
            lines.append("- Error samples:")
            for item in error_samples[:5]:
                lines.append(f"  - {item.get('status')}: {item.get('url', '')}")

    lines.extend(
        [
            f"- HTML path: {result.get('html_path', '')}",
            f"- Screenshot path: {result.get('screenshot_path', '')}",
            "",
            "## Sample Products",
        ]
    )

    products = result.get("products_sample") or []
    if not products:
        lines.append("")
        lines.append("No sample products were extracted.")
    else:
        for product in products:
            lines.append(
                "- {name} | {price} | {link}".format(
                    name=product.get("name", ""),
                    price=product.get("price", ""),
                    link=product.get("link", ""),
                )
            )
    lines.append("")
    return "\n".join(lines)


def write_smoke_report(result: dict[str, Any], output_path: str | Path) -> Path:
    """Write a Markdown smoke report and return its path."""
    path = Path(output_path)
    path.write_text(build_pyaterochka_smoke_report(result), encoding="utf-8")
    return path
