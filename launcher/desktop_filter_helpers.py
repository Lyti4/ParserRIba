"""Helpers for launcher filter widgets backed by available_filter_counts."""

from __future__ import annotations

from typing import Any


FILTER_COUNT_KEYS = {
    "suppliers": "suppliers",
    "brands": "brands",
    "wine_styles": "wine_styles",
    "alcohol_types": "alcohol_types",
    "sugar_classes": "sugar_classes",
    "colors": "colors",
}


def extract_filter_counts(launcher_view: dict[str, Any], filter_name: str) -> dict[str, int]:
    """Extract one filter facet count mapping from launcher_view."""
    available_filter_counts = launcher_view.get("available_filter_counts")
    if not isinstance(available_filter_counts, dict):
        return {}
    facet = available_filter_counts.get(FILTER_COUNT_KEYS[filter_name])
    if not isinstance(facet, dict):
        return {}
    result: dict[str, int] = {}
    for raw_key, raw_value in facet.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        try:
            count = int(raw_value)
        except (TypeError, ValueError):
            continue
        result[key] = count
    return result


def build_filter_option_labels(counts: dict[str, int]) -> list[tuple[str, str]]:
    """Build stable widget labels from one count mapping."""
    return [(value, f"{value} ({count})") for value, count in sorted(counts.items())]
