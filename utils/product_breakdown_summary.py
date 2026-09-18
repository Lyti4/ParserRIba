"""Compatibility helpers for neutral product breakdown summaries."""

from __future__ import annotations

from typing import Any


def with_product_breakdown_alias(summary: dict[str, Any] | None) -> dict[str, Any]:
    """Return a summary with neutral product_breakdown populated from legacy data."""
    result = dict(summary or {})
    if "product_breakdown" not in result and isinstance(result.get("wine_breakdown"), dict):
        result["product_breakdown"] = result["wine_breakdown"]
    return result
