"""Launcher-facing summaries for already-built storage reports."""

from __future__ import annotations

from collections.abc import Iterable

from models.schemas import Product
from utils.report_filter_facets import alcohol_type, color, ordered_categories, sugar_class, supplier


def build_report_summary(products: list[Product]) -> dict[str, object]:
    """Build one structured summary for filtered report products."""
    brand_counts = _counted_values(str(product.brand or "") for product in products)
    category_counts = _counted_values(str(product.category or "") for product in products)
    supplier_counts = _counted_values(supplier(product) for product in products)
    style_counts = _counted_values(str(product.subcategory or "") for product in products)
    alcohol_type_counts = _counted_values(alcohol_type(product) for product in products)
    sugar_class_counts = _counted_values(sugar_class(product.name) for product in products)
    color_counts = _counted_values(color(product.name) for product in products)
    return {
        "products_count": len(products),
        "categories": ordered_categories(products),
        "category_counts": category_counts,
        "supplier_counts": supplier_counts,
        "brand_counts": brand_counts,
        "wine_breakdown": {
            "style_counts": style_counts,
            "alcohol_type_counts": alcohol_type_counts,
            "sugar_class_counts": sugar_class_counts,
            "color_counts": color_counts,
        },
    }


def _counted_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        counts[item] = counts.get(item, 0) + 1
    return {key: counts[key] for key in sorted(counts)}
