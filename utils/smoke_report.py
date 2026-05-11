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
        f"- HTTP status: {result.get('http_status')}",
        f"- Cards found: {result.get('cards_found', 0)}",
        f"- Final URL: {result.get('final_url', '')}",
        f"- HTML size: {result.get('html_size', 0)}",
    ]

    navigation_error = result.get("navigation_error")
    if navigation_error:
        lines.append(f"- Navigation error: {str(navigation_error).splitlines()[0]}")

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
