"""Shared launcher-facing export summary helpers."""

from __future__ import annotations

import re
from typing import Any


def build_export_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Build one structured export summary for JSON payloads and manifests."""
    return {
        "products_count": int(payload.get("products_count") or 0),
        "categories": list(payload.get("categories") or []),
        "attempt": payload.get("attempt") or {},
        "wine_breakdown": _build_wine_breakdown(payload),
    }


def _build_wine_breakdown(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    if str(payload.get("intent") or "").strip() != "wine_catalog":
        return {
            "style_counts": {},
            "alcohol_type_counts": {},
            "sugar_class_counts": {},
            "color_counts": {},
        }

    style_counts: dict[str, int] = {}
    alcohol_type_counts: dict[str, int] = {}
    sugar_class_counts: dict[str, int] = {}
    color_counts: dict[str, int] = {}

    for item in payload.get("products") or []:
        if not isinstance(item, dict):
            continue
        style = str(item.get("subcategory") or "").strip()
        if style:
            style_counts[style] = style_counts.get(style, 0) + 1

        raw_data = item.get("raw_data")
        if isinstance(raw_data, dict):
            alcohol_type = str(raw_data.get("alcohol_type") or "").strip()
            if alcohol_type:
                alcohol_type_counts[alcohol_type] = alcohol_type_counts.get(alcohol_type, 0) + 1

        name = str(item.get("name") or "")
        sugar_class = _extract_sugar_class(name)
        if sugar_class:
            sugar_class_counts[sugar_class] = sugar_class_counts.get(sugar_class, 0) + 1

        color = _extract_color_class(name)
        if color:
            color_counts[color] = color_counts.get(color, 0) + 1

    return {
        "style_counts": style_counts,
        "alcohol_type_counts": alcohol_type_counts,
        "sugar_class_counts": sugar_class_counts,
        "color_counts": color_counts,
    }


def _extract_sugar_class(name: str) -> str:
    lowered = str(name or "").casefold()
    if "экстра брют" in lowered:
        return "Экстра брют"
    if "брют" in lowered:
        return "Брют"
    if "полусух" in lowered:
        return "Полусухое"
    if re.search(r"\bсух", lowered):
        return "Сухое"
    if "полуслад" in lowered:
        return "Полусладкое"
    if "слад" in lowered:
        return "Сладкое"
    return ""


def _extract_color_class(name: str) -> str:
    lowered = str(name or "").casefold()
    if "бел" in lowered:
        return "Белое"
    if "крас" in lowered:
        return "Красное"
    if "роз" in lowered:
        return "Розовое"
    return ""
