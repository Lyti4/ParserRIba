"""Render a compact local report from Pyaterochka products SQLite storage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.discover_pyaterochka_api import OUTPUT_DIR
from utils.product_storage import ProductStorage


def build_products_report(summary: dict[str, Any]) -> str:
    """Build a compact human-readable products report."""
    lines = [
        "# Pyaterochka Products Report",
        "",
        f"- Products stored: {summary.get('products_count', 0)}",
        f"- Latest snapshot: {summary.get('latest_snapshot_at', '')}",
        f"- Previous snapshot: {summary.get('previous_snapshot_at', '')}",
        f"- Changed prices: {len(summary.get('changed_prices') or [])}",
    ]
    for item in (summary.get("changed_prices") or [])[:10]:
        lines.append(
            "- {product_id} | {name} | {previous_price} -> {current_price}".format(
                product_id=item.get("product_id", ""),
                name=item.get("name", ""),
                previous_price=item.get("previous_price"),
                current_price=item.get("current_price"),
            )
        )
    lines.append(f"- Changed availability: {len(summary.get('changed_availability') or [])}")
    for item in (summary.get("changed_availability") or [])[:10]:
        lines.append(
            "- {product_id} | {name} | {previous_in_stock} -> {current_in_stock}".format(
                product_id=item.get("product_id", ""),
                name=item.get("name", ""),
                previous_in_stock=item.get("previous_in_stock"),
                current_in_stock=item.get("current_in_stock"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show local Pyaterochka product snapshot report")
    parser.add_argument("--db-path", default=str(OUTPUT_DIR / "products.db"))
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    storage = ProductStorage(args.db_path)
    report = build_products_report(storage.latest_snapshot_report("pyaterochka"))
    sys.stdout.write(report)
