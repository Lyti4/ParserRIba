"""Store-neutral product classification facade for generic UI and reports."""

from __future__ import annotations

from utils.wine_product_classification import (
    classify_wine_alcohol_type,
    classify_wine_style,
    extract_brand_from_name,
)


def classify_product_alcohol_type(name: str, category: str | None = None) -> str:
    """Return a readable alcohol type when current known heuristics can infer one."""
    return classify_wine_alcohol_type(name, category) or ""


def classify_product_subcategory(name: str, category: str | None = None) -> str:
    """Return a readable product subcategory when current known heuristics can infer one."""
    return classify_wine_style(name, category) or ""


def extract_product_brand_from_name(name: str) -> str:
    """Return a conservative brand candidate derived from a product name."""
    return extract_brand_from_name(name) or ""
