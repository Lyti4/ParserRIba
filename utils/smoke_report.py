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
        f"- Persistent profile: {result.get('persistent_profile', False)}",
        f"- Profile dir: {result.get('profile_dir', '')}",
        f"- Manual wait: {result.get('manual_wait', False)}",
        f"- Manual cards ready: {result.get('manual_cards_ready', False)}",
    ]
    fingerprint = result.get("fingerprint") or {}
    if fingerprint:
        lines.extend(
            [
                f"- Fingerprint engine: {fingerprint.get('engine', '')}",
                f"- Fingerprint OS: {fingerprint.get('os', '')}",
                f"- Locale: {fingerprint.get('locale', '')}",
                f"- Camoufox humanize: {fingerprint.get('humanize', False)}",
                f"- Block images: {fingerprint.get('block_images', False)}",
                f"- Block WebRTC: {fingerprint.get('block_webrtc', False)}",
                f"- Block WebGL: {fingerprint.get('block_webgl', False)}",
            ]
        )
        screen = fingerprint.get("screen") or {}
        if screen:
            lines.append(
                "- Screen constraints: {min_width}-{max_width} x {min_height}-{max_height}".format(
                    min_width=screen.get("min_width", ""),
                    max_width=screen.get("max_width", ""),
                    min_height=screen.get("min_height", ""),
                    max_height=screen.get("max_height", ""),
                )
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
        if reason.startswith("network_"):
            lines.extend(
                [
                    "",
                    "## Network Action",
                    "Navigation failed before the catalog loaded. Check DNS, VPN/proxy connectivity, or set a working RU proxy in `.env`.",
                ]
            )

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
        catalog_samples = network.get("catalog_samples") or []
        if catalog_samples:
            lines.append("- Catalog/API samples:")
            for item in catalog_samples[:8]:
                lines.append(f"  - {item.get('status')}: {item.get('url', '')}")

    product_api = result.get("product_api_diagnostics") or {}
    page_context = product_api.get("page_context") or {}
    product_samples = network.get("product_api_samples") if network else []
    empty_samples = network.get("empty_product_api_samples") if network else []
    if product_api or product_samples or empty_samples:
        lines.extend(["", "## Product API Diagnostics"])
        if page_context:
            lines.extend(
                [
                    f"- Next data present: {page_context.get('next_data_present', False)}",
                    f"- Catalog store present: {page_context.get('catalog_store_present', False)}",
                    f"- Selected store detected: {page_context.get('selected_store_detected', False)}",
                    f"- Address detected: {page_context.get('address_detected', False)}",
                    f"- Region hint detected: {page_context.get('region_hint_detected', False)}",
                    f"- Products list empty: {page_context.get('products_list_empty', False)}",
                    f"- Products empty: {page_context.get('products_empty', False)}",
                    f"- Products response null: {page_context.get('products_response_null', False)}",
                ]
            )
        if product_samples:
            lines.append("- Product/API responses:")
            for item in product_samples[:8]:
                empty = item.get("empty_products_payload", "")
                lines.append(f"  - {item.get('status')}: empty={empty} {item.get('url', '')}")
        if empty_samples:
            lines.append("- Empty product payload samples:")
            for item in empty_samples[:3]:
                preview = item.get("payload_preview", "")
                lines.append(f"  - {item.get('status')}: {preview}")

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
