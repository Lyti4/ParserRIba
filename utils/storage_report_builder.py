"""Build local reports from stored products without running live scraping."""

from __future__ import annotations

import json
import re
import sqlite3
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from models.report_request import ReportBuildResult, ReportFilterOptionsResult, ReportRequest, ProductFilter
from models.schemas import Product
from utils.excel_report import write_products_excel_report
from utils.report_export_summary import build_report_summary
from utils.wine_product_classification import (
    classify_wine_alcohol_type,
    classify_wine_style,
    extract_brand_from_name,
)
from utils.report_filter_facets import (
    alcohol_type as report_alcohol_type,
    build_report_filter_options_result,
    color as report_color,
    ordered_categories,
    sugar_class as report_sugar_class,
    supplier as report_supplier,
)


@dataclass(frozen=True)
class BuiltReport:
    """Concrete report result with a filesystem path for Python callers."""

    report_path: Path
    products_count: int
    categories: list[str]
    filters_applied: dict[str, object]
    report_summary: dict[str, object]

    def to_model(self) -> ReportBuildResult:
        """Return the Pydantic representation used by task manifests."""
        return ReportBuildResult(
            report_path=str(self.report_path),
            products_count=self.products_count,
            categories=self.categories,
            filters_applied=self.filters_applied,
            report_summary=self.report_summary,
        )


def build_excel_report_from_storage(
    request: ReportRequest,
    *,
    db_path: Path | str,
    output_dir: Path | str,
    exported_at: str = "",
) -> BuiltReport:
    """Build one XLSX report from current SQLite product state."""
    products = load_products_from_storage(db_path=db_path, shop=request.selection.shop)
    products = _apply_selection(products, request)
    products = filter_products(products, request.filters)
    report_path = write_products_excel_report(
        products,
        shop=_safe_output_stem(request),
        output_dir=output_dir,
        exported_at=exported_at,
    )
    report_path = _normalize_report_path(report_path, request)
    return BuiltReport(
        report_path=report_path,
        products_count=len(products),
        categories=ordered_categories(products),
        filters_applied=request.filters.model_dump(mode="json"),
        report_summary=build_report_summary(products),
    )


def build_report_filter_options(
    request: ReportRequest,
    *,
    db_path: Path | str,
) -> ReportFilterOptionsResult:
    """Build available post-capture filter values from stored products."""
    products = load_products_from_storage(db_path=db_path, shop=request.selection.shop)
    products = _apply_selection(products, request)
    return build_report_filter_options_result(request, products)


def load_products_from_storage(*, db_path: Path | str, shop: str) -> list[Product]:
    """Load current Product models from SQLite storage."""
    path = Path(db_path)
    if not path.exists():
        return []
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT product_id, name, product_link, image_url, category, subcategory,
                   in_stock, current_price, old_price, unit_price, currency, raw_data
            FROM products
            WHERE store = ?
            ORDER BY category, name
            """,
            (shop,),
        ).fetchall()
    return [_row_to_product(row) for row in rows]


def filter_products(products: list[Product], filters: ProductFilter) -> list[Product]:
    """Apply post-capture report filters to Product models."""
    return [product for product in products if _matches_product_filter(product, filters)]


def _apply_selection(products: list[Product], request: ReportRequest) -> list[Product]:
    selected_product_ids = [
        str(item).strip()
        for item in request.selection.selected_product_ids
        if str(item).strip()
    ]
    if selected_product_ids:
        allowed_ids = set(selected_product_ids)
        return [
            product
            for product in products
            if str(product.id or "").strip() in allowed_ids
        ]
    categories = request.selection.categories or request.filters.categories
    if not categories:
        return products
    allowed = {_normalize_text(item) for item in categories}
    return [
        product
        for product in products
        if _normalize_text(str(product.category or "")) in allowed
    ]


def _matches_product_filter(product: Product, filters: ProductFilter) -> bool:
    if filters.in_stock is not None and bool(product.in_stock) is not filters.in_stock:
        return False
    if filters.min_price is not None and float(product.price.current) < filters.min_price:
        return False
    if filters.max_price is not None and float(product.price.current) > filters.max_price:
        return False
    if not _matches_text_list(report_supplier(product), filters.suppliers, filters.strict_missing):
        return False
    if not _matches_text_list(str(product.brand or ""), filters.brands, filters.strict_missing):
        return False
    if not _matches_text_list(str(product.category or ""), filters.categories, filters.strict_missing):
        return False
    if not _matches_text_list(str(product.subcategory or ""), filters.wine_styles, filters.strict_missing):
        return False
    if not _matches_text_list(report_alcohol_type(product), filters.alcohol_types, filters.strict_missing):
        return False
    if not _matches_text_list(report_sugar_class(product.name), filters.sugar_classes, filters.strict_missing):
        return False
    if not _matches_text_list(report_color(product.name), filters.colors, filters.strict_missing):
        return False
    return True


def _row_to_product(row: sqlite3.Row) -> Product:
    raw_data = _json_dict(str(row["raw_data"] or "{}"))
    name = str(row["name"])
    category = str(row["category"] or "")
    brand = _first_text(
        raw_data,
        ("brand", "supplier", "producer", "manufacturer", "vendor"),
    ) or extract_brand_from_name(name)
    alcohol_type = _first_text(raw_data, ("alcohol_type",)) or classify_wine_alcohol_type(name, category)
    raw_copy = dict(raw_data)
    if alcohol_type:
        raw_copy["alcohol_type"] = alcohol_type
    return Product(
        id=str(row["product_id"]),
        name=name,
        brand=brand,
        price={
            "current": float(row["current_price"]),
            "old": row["old_price"],
            "unit": row["unit_price"],
            "currency": str(row["currency"] or "RUB"),
        },
        image_url=str(row["image_url"]) or None,
        product_link=str(row["product_link"]),
        category=category or None,
        subcategory=str(row["subcategory"] or "") or classify_wine_style(name, category),
        in_stock=bool(row["in_stock"]),
        raw_data=raw_copy,
    )


def _safe_output_stem(request: ReportRequest) -> str:
    raw_name = request.output_name or f"{request.selection.shop}_{request.selection.intent}_report"
    sanitized = re.sub(r"[:\\/?*\[\]<>|\"\r\n\t]+", "_", raw_name)
    sanitized = re.sub(r"\s+", "_", sanitized).strip(" ._")
    return sanitized or "report"


def _normalize_report_path(report_path: Path, request: ReportRequest) -> Path:
    if not request.output_name:
        return report_path
    final_path = report_path.with_name(f"{_safe_output_stem(request)}.xlsx")
    if final_path == report_path:
        return report_path
    shutil.copyfile(report_path, final_path)
    return final_path


def _matches_text_list(value: str, filters: list[str], strict_missing: bool) -> bool:
    if not filters:
        return True
    normalized_value = _normalize_text(value)
    if not normalized_value:
        return not strict_missing
    allowed = {_normalize_text(item) for item in filters}
    return normalized_value in allowed


def _first_text(raw_data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = raw_data.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""


def _json_dict(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").casefold().split())
