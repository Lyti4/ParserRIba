"""Wine-specific product classification helpers for storefront exports."""

from __future__ import annotations

import re
from typing import Any

from models.schemas import Product
from utils.product_name_branding import derive_supplier_from_product_name

WINE_STYLE_QUIET = "Тихое"
WINE_STYLE_SPARKLING = "Игристое"
WINE_STYLE_VERMOUTH = "Вермут"
WINE_STYLE_SANGRIA = "Сангрия"
WINE_STYLE_CHAMPAGNE = "Шампанское"
WINE_STYLE_WINE_DRINK = "Винный напиток"
ALCOHOL_FREE = "Безалкогольное"
ALCOHOL_REGULAR = "Алкогольное"

WINE_MARKERS = (
    "вино",
    "винный напиток",
    "игрист",
    "шампан",
    "вермут",
    "сангр",
    "просекко",
    "брют",
    "кава",
    "spumante",
    "sparkling",
    "mousseux",
    "martini",
    "vino",
    "vina",
)
NON_WINE_MARKERS = ("энергет", "пиво", "сидр", "медовух", "beer", "energy")


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
    for key in ("brand", "brand_name", "brandName", "trademark", "producer", "manufacturer", "vendor"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for nested_key in ("name", "title", "value"):
                nested_value = value.get(nested_key)
                if isinstance(nested_value, str) and nested_value.strip():
                    return nested_value.strip()
    return extract_brand_from_name(str(payload.get("name") or ""))


def is_wine_product(product: Product) -> bool:
    """Return whether one normalized product belongs to the wine storefront intent."""
    return _is_wine_product_text(
        str(product.name or ""),
        " ".join([str(product.category or ""), str((product.raw_data or {}).get("categories") or "")]),
    )


def classify_wine_alcohol_type(name: str, category: str | None) -> str | None:
    """Classify whether a wine-like product is alcohol-free or regular."""
    if not _is_wine_product_text(name, category or ""):
        return None
    combined = f"{name or ''} {category or ''}".casefold()
    if "безалкогол" in combined or "alcohol-free" in combined or "non alcoholic" in combined:
        return ALCOHOL_FREE
    return ALCOHOL_REGULAR


def classify_wine_style(name: str, category: str | None) -> str | None:
    """Classify the wine style from product name and category context."""
    if not _is_wine_product_text(name, category or ""):
        return None
    combined = f"{name or ''} {category or ''}".casefold()
    if "вермут" in combined or "martini" in combined:
        return WINE_STYLE_VERMOUTH
    if "сангр" in combined or "sangria" in combined:
        return WINE_STYLE_SANGRIA
    if "шампан" in combined:
        return WINE_STYLE_CHAMPAGNE
    if any(marker in combined for marker in ("игрист", "просекко", "брют", "кава", "spumante", "sparkling", "mousseux")):
        return WINE_STYLE_SPARKLING
    if "винный напиток" in combined:
        return WINE_STYLE_WINE_DRINK
    return WINE_STYLE_QUIET


def extract_brand_from_name(name: str) -> str | None:
    """Extract a conservative brand candidate from a wine product title."""
    source = str(name or "").strip()
    if not source:
        return None
    normalized = re.sub(
        r"^(вино(?:\s+игристое)?|напиток|вермут|шампанское|винный напиток|sparkling)\s+",
        "",
        source,
        flags=re.IGNORECASE,
    )
    return derive_supplier_from_product_name(normalized) or None


def _is_wine_product_text(name: str, context: str) -> bool:
    name_text = str(name or "").casefold()
    if any(marker in name_text for marker in NON_WINE_MARKERS):
        return False
    if any(marker in name_text for marker in WINE_MARKERS):
        return True
    context_text = str(context or "").casefold()
    if any(marker in context_text for marker in NON_WINE_MARKERS):
        return False
    return any(marker in context_text for marker in WINE_MARKERS)
