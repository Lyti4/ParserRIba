"""Facet helpers for launcher-facing report filter discovery."""

from __future__ import annotations

from typing import Iterable

from models.report_request import ReportFilterOptionsResult, ReportRequest
from models.schemas import Product
from utils.product_report_display_fields import looks_mojibake, product_supplier, readable_alcohol_type


def build_report_filter_options_result(
    request: ReportRequest,
    products: list[Product],
) -> ReportFilterOptionsResult:
    """Build available report filters from already selected products."""
    suppliers = _counted_values(_supplier(product) for product in products)
    brands = _counted_values(str(product.brand or "") for product in products)
    categories = _counted_values(str(product.category or "") for product in products)
    subcategories = _counted_values(str(product.subcategory or "") for product in products)
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
            "subcategories": list(subcategories),
            "wine_styles": list(subcategories),
            "alcohol_types": list(alcohol_types),
            "sugar_classes": list(sugar_classes),
            "colors": list(colors),
        },
        available_filter_counts={
            "suppliers": suppliers,
            "brands": brands,
            "categories": categories,
            "subcategories": subcategories,
            "wine_styles": subcategories,
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
    return product_supplier(product)


def _alcohol_type(product: Product) -> str:
    raw_data = dict(product.raw_data or {})
    value = raw_data.get("alcohol_type")
    if isinstance(value, str) and value.strip() and not looks_mojibake(value):
        return value.strip()
    return readable_alcohol_type(raw_data, str(product.name or ""), str(product.category or ""))


def _sugar_class(name: str) -> str:
    lowered = str(name or "").casefold()
    if _has_any(lowered, "\u044d\u043a\u0441\u0442\u0440\u0430 \u0431\u0440\u044e\u0442", "\u0421\u040c\u0420\u0454\u0421\u0403\u0421\u201a\u0421\u0402\u0420\xb0 \u0420\xb1\u0421\u0402\u0421\u040b\u0421\u201a"):
        return "\u042d\u043a\u0441\u0442\u0440\u0430 \u0431\u0440\u044e\u0442"
    if _has_any(lowered, "\u0431\u0440\u044e\u0442", "\u0420\xb1\u0421\u0402\u0421\u040b\u0421\u201a"):
        return "\u0411\u0440\u044e\u0442"
    if _has_any(lowered, "\u043f\u043e\u043b\u0443\u0441\u0443\u0445", "\u0420\u0457\u0420\u0455\u0420\xbb\u0421\u0453\u0421\u0403\u0421\u0453\u0421\u2026"):
        return "\u041f\u043e\u043b\u0443\u0441\u0443\u0445\u043e\u0435"
    if _has_any(lowered, "\u0441\u0443\u0445", "\u0421\u0403\u0421\u0453\u0421\u2026"):
        return "\u0421\u0443\u0445\u043e\u0435"
    if _has_any(lowered, "\u043f\u043e\u043b\u0443\u0441\u043b\u0430\u0434", "\u0420\u0457\u0420\u0455\u0420\xbb\u0421\u0453\u0421\u0403\u0420\xbb\u0420\xb0\u0420\u0491"):
        return "\u041f\u043e\u043b\u0443\u0441\u043b\u0430\u0434\u043a\u043e\u0435"
    if _has_any(lowered, "\u0441\u043b\u0430\u0434", "\u0421\u0403\u0420\xbb\u0420\xb0\u0420\u0491"):
        return "\u0421\u043b\u0430\u0434\u043a\u043e\u0435"
    return ""


def _color(name: str) -> str:
    lowered = str(name or "").casefold()
    if _has_any(lowered, "\u0431\u0435\u043b", "\u0420\xb1\u0420\xb5\u0420\xbb"):
        return "\u0411\u0435\u043b\u043e\u0435"
    if _has_any(lowered, "\u043a\u0440\u0430\u0441", "\u0420\u0454\u0421\u0402\u0420\xb0\u0421\u0403"):
        return "\u041a\u0440\u0430\u0441\u043d\u043e\u0435"
    if _has_any(lowered, "\u0440\u043e\u0437", "\u0421\u0402\u0420\u0455\u0420\xb7"):
        return "\u0420\u043e\u0437\u043e\u0432\u043e\u0435"
    return ""


def _has_any(value: str, *needles: str) -> bool:
    return any(needle.casefold() in value for needle in needles)


def _counted_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        counts[item] = counts.get(item, 0) + 1
    return {key: counts[key] for key in sorted(counts)}
