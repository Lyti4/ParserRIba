"""Compatibility aliases for launcher filter count keys."""

from __future__ import annotations

from typing import Any

RICH_FILTER_COUNT_KEYS = ("suppliers", "brands", "subcategories", "wine_styles", "alcohol_types", "sugar_classes", "colors")


def with_legacy_filter_count_aliases(counts: dict[str, Any]) -> dict[str, Any]:
    """Return counts with legacy saved filter keys mapped to neutral keys."""
    result = dict(counts)
    if "subcategories" not in result and isinstance(result.get("wine_styles"), dict):
        result["subcategories"] = result["wine_styles"]
    return result


def add_legacy_filter_count_aliases(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """Publish legacy keys expected by old launcher/report manifests."""
    result = dict(counts)
    if "wine_styles" not in result and isinstance(result.get("subcategories"), dict):
        result["wine_styles"] = result["subcategories"]
    return result
