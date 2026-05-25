"""Wine-specific product classification helpers for storefront exports."""

from __future__ import annotations

import re
from typing import Any

from models.schemas import Product

WINE_STYLE_QUIET = "РўРёС…РѕРµ"
WINE_STYLE_SPARKLING = "РРіСЂРёСЃС‚РѕРµ"
WINE_STYLE_VERMOUTH = "Р’РµСЂРјСѓС‚"
WINE_STYLE_SANGRIA = "РЎР°РЅРіСЂРёСЏ"
WINE_STYLE_CHAMPAGNE = "РЁР°РјРїР°РЅСЃРєРѕРµ"
WINE_STYLE_WINE_DRINK = "Р’РёРЅРЅС‹Р№ РЅР°РїРёС‚РѕРє"
ALCOHOL_FREE = "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ"
ALCOHOL_REGULAR = "РђР»РєРѕРіРѕР»СЊРЅРѕРµ"


def merge_wine_raw_fields(
    raw_data: dict[str, Any] | None,
    *,
    alcohol_type: str | None = None,
    intent_scope: str | None = None,
) -> dict[str, Any]:
    """Merge wine-specific metadata into a raw payload mapping."""
    merged = dict(raw_data or {})
    if alcohol_type:
        merged["alcohol_type"] = alcohol_type
    if intent_scope:
        merged["intent_scope"] = intent_scope
    return merged


def extract_brand_from_payload(payload: dict[str, Any]) -> str | None:
    """Extract brand-like fields from a payload or fall back to name parsing."""
    for key in ("brand", "trademark", "producer", "manufacturer", "vendor"):
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
        if isinstance(value, dict):
            for nested_key in ("name", "title", "value"):
                nested_value = value.get(nested_key)
                if isinstance(nested_value, str):
                    text = nested_value.strip()
                    if text:
                        return text
    name = payload.get("name")
    if isinstance(name, str):
        return extract_brand_from_name(name)
    return None


def is_wine_product(product: Product) -> bool:
    """Return whether one normalized product belongs to the wine storefront intent."""
    name_text = str(product.name or "").casefold()
    context_text = " ".join(
        [
            str(product.category or ""),
            str((product.raw_data or {}).get("categories") or ""),
        ]
    ).casefold()
    include_markers = (
        "РІРёРЅРѕ",
        "РёРіСЂРёСЃС‚",
        "С€Р°РјРїР°РЅ",
        "РІРµСЂРјСѓС‚",
        "РїСЂРѕСЃРµРєРєРѕ",
        "Р±СЂСЋС‚",
        "РєР°РІР°",
        "РІРёРЅРЅС‹Р№ РЅР°РїРёС‚",
        "СЃР°РЅРіСЂРёСЏ",
        "martini",
        "spumante",
        "sparkling",
    )
    exclude_markers = ("СЌРЅРµСЂРіРµС‚", "РїРёРІРѕ", "СЃРёРґСЂ", "РјРµРґРѕРІСѓС…")
    if any(marker in name_text for marker in exclude_markers):
        return False
    if any(marker in name_text for marker in include_markers):
        return True
    return any(marker in context_text for marker in include_markers)


def classify_wine_alcohol_type(name: str, category: str | None) -> str | None:
    """Classify whether a wine-like product is alcohol-free or regular."""
    combined = f"{name or ''} {category or ''}".casefold()
    if not any(
        marker in combined
        for marker in (
            "РІРёРЅРѕ",
            "РёРіСЂРёСЃС‚",
            "С€Р°РјРїР°РЅ",
            "РІРµСЂРјСѓС‚",
            "СЃР°РЅРіСЂРёСЏ",
            "РІРёРЅРЅС‹Р№ РЅР°РїРёС‚",
            "spumante",
            "sparkling",
        )
    ):
        return None
    if "Р±РµР·Р°Р»РєРѕРіРѕР»СЊ" in combined:
        return ALCOHOL_FREE
    return ALCOHOL_REGULAR


def classify_wine_style(name: str, category: str | None) -> str | None:
    """Classify the wine style from product name and category context."""
    combined = f"{name or ''} {category or ''}".casefold()
    if "РІРµСЂРјСѓС‚" in combined or "martini" in combined:
        return WINE_STYLE_VERMOUTH
    if "СЃР°РЅРіСЂРёСЏ" in combined or "sangria" in combined:
        return WINE_STYLE_SANGRIA
    if "С€Р°РјРїР°РЅ" in combined:
        return WINE_STYLE_CHAMPAGNE
    if any(
        marker in combined
        for marker in (
            "РёРіСЂРёСЃС‚",
            "РїСЂРѕСЃРµРєРєРѕ",
            "Р±СЂСЋС‚",
            "РєР°РІР°",
            "spumante",
            "sparkling",
            "mousseux",
        )
    ):
        return WINE_STYLE_SPARKLING
    if "РІРёРЅРЅС‹Р№ РЅР°РїРёС‚" in combined:
        return WINE_STYLE_WINE_DRINK
    if "РІРёРЅРѕ" in combined:
        return WINE_STYLE_QUIET
    return None


def extract_brand_from_name(name: str) -> str | None:
    """Extract a conservative brand candidate from a wine product title."""
    source = str(name or "").strip()
    if not source:
        return None

    normalized = re.sub(
        r"^(РІРёРЅРѕ(?:\s+РёРіСЂРёСЃС‚РѕРµ)?|РЅР°РїРёС‚РѕРє|РІРµСЂРјСѓС‚|С€Р°РјРїР°РЅСЃРєРѕРµ|РІРёРЅРЅС‹Р№ РЅР°РїРёС‚РѕРє)\s+",
        "",
        source,
        flags=re.IGNORECASE,
    )
    if normalized == source:
        return None

    stop_markers = {
        "Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ",
        "Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅС‹Р№",
        "РіР°Р·РёСЂРѕРІР°РЅРЅРѕРµ",
        "РіР°Р·РёСЂРѕРІР°РЅРЅС‹Р№",
        "Р±РµР»РѕРµ",
        "РєСЂР°СЃРЅРѕРµ",
        "СЂРѕР·РѕРІРѕРµ",
        "РїРѕР»СѓСЃР»Р°РґРєРѕРµ",
        "РїРѕР»СѓСЃСѓС…РѕРµ",
        "СЃСѓС…РѕРµ",
        "СЃР»Р°РґРєРѕРµ",
        "Р±СЂСЋС‚",
        "СЌРєСЃС‚СЂР°",
        "riesling",
        "chardonnay",
        "merlot",
        "merllot",
        "pinot",
        "noir",
        "blanc",
        "cabernet",
        "tempranillo",
        "sauvignon",
        "sparkling",
        "spumante",
        "mousseux",
        "bianco",
        "rose",
        "white",
        "red",
        "veneto",
    }

    tokens = re.split(r"\s+", normalized)
    brand_tokens: list[str] = []
    for token in tokens:
        cleaned = token.strip(".,;:()[]{}\"'")
        if not cleaned:
            continue
        if re.search(r"\d", cleaned):
            break
        if cleaned.casefold() in stop_markers:
            break
        brand_tokens.append(cleaned)
        if len(brand_tokens) == 3:
            break

    if not brand_tokens:
        return None
    return " ".join(brand_tokens)
