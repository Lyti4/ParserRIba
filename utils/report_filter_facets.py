"""Facet helpers for launcher-facing report filter discovery."""

from __future__ import annotations

from typing import Iterable

from models.report_request import ReportFilterOptionsResult, ReportRequest
from models.schemas import Product


def build_report_filter_options_result(
    request: ReportRequest,
    products: list[Product],
) -> ReportFilterOptionsResult:
    """Build available report filters from already selected products."""
    suppliers = _counted_values(_supplier(product) for product in products)
    brands = _counted_values(str(product.brand or "") for product in products)
    categories = _counted_values(str(product.category or "") for product in products)
    wine_styles = _counted_values(str(product.subcategory or "") for product in products)
    alcohol_types = _counted_values(_alcohol_type(product) for product in products)
    sugar_classes = _counted_values(_sugar_class(product.name) for product in products)
    colors = _counted_values(_color(product.name) for product in products)
    return ReportFilterOptionsResult(
        shop=request.selection.shop,
        intent=request.selection.intent,
        products_count=len(products),
        categories=_ordered_categories(products),
        available_filters={
            "suppliers": list(suppliers),
            "brands": list(brands),
            "categories": list(categories),
            "wine_styles": list(wine_styles),
            "alcohol_types": list(alcohol_types),
            "sugar_classes": list(sugar_classes),
            "colors": list(colors),
        },
        available_filter_counts={
            "suppliers": suppliers,
            "brands": brands,
            "categories": categories,
            "wine_styles": wine_styles,
            "alcohol_types": alcohol_types,
            "sugar_classes": sugar_classes,
            "colors": colors,
        },
    )


def ordered_categories(products: list[Product]) -> list[str]:
    """Return stable category order from the current product list."""
    return _ordered_categories(products)


def supplier(product: Product) -> str:
    """Return normalized supplier-like text for one product."""
    return _supplier(product)


def alcohol_type(product: Product) -> str:
    """Return normalized alcohol type for one product."""
    return _alcohol_type(product)


def sugar_class(name: str) -> str:
    """Return normalized sugar classification from product name."""
    return _sugar_class(name)


def color(name: str) -> str:
    """Return normalized wine color from product name."""
    return _color(name)


def _ordered_categories(products: list[Product]) -> list[str]:
    categories: list[str] = []
    for product in products:
        category_name = str(product.category or "")
        if category_name and category_name not in categories:
            categories.append(category_name)
    return categories


def _supplier(product: Product) -> str:
    raw_data = dict(product.raw_data or {})
    for key in ("supplier", "producer", "manufacturer", "vendor", "brand"):
        value = raw_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(product.brand or "")


def _alcohol_type(product: Product) -> str:
    raw_data = dict(product.raw_data or {})
    value = raw_data.get("alcohol_type")
    if isinstance(value, str):
        return value.strip()
    return ""


def _sugar_class(name: str) -> str:
    lowered = str(name or "").casefold()
    if "СЌРєСЃС‚СЂР° Р±СЂСЋС‚" in lowered:
        return "Р­РєСЃС‚СЂР° Р±СЂСЋС‚"
    if "Р±СЂСЋС‚" in lowered:
        return "Р‘СЂСЋС‚"
    if "РїРѕР»СѓСЃСѓС…" in lowered:
        return "РџРѕР»СѓСЃСѓС…РѕРµ"
    if "СЃСѓС…" in lowered:
        return "РЎСѓС…РѕРµ"
    if "РїРѕР»СѓСЃР»Р°Рґ" in lowered:
        return "РџРѕР»СѓСЃР»Р°РґРєРѕРµ"
    if "СЃР»Р°Рґ" in lowered:
        return "РЎР»Р°РґРєРѕРµ"
    return ""


def _color(name: str) -> str:
    lowered = str(name or "").casefold()
    if "Р±РµР»" in lowered:
        return "Р‘РµР»РѕРµ"
    if "РєСЂР°СЃ" in lowered:
        return "РљСЂР°СЃРЅРѕРµ"
    if "СЂРѕР·" in lowered:
        return "Р РѕР·РѕРІРѕРµ"
    return ""
def _counted_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        counts[item] = counts.get(item, 0) + 1
    return {key: counts[key] for key in sorted(counts)}
