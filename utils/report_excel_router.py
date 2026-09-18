"""Route report Excel generation to the intent-specific workbook template."""

from __future__ import annotations

from pathlib import Path

from models.schemas import Product
from utils.excel_report import write_products_excel_report
from utils.generic_excel_report import write_generic_products_excel_report


def write_products_excel_report_for_intent(
    products: list[Product],
    *,
    shop: str,
    output_dir: Path | str,
    exported_at: str = "",
    intent: str = "",
    selected_columns: list[str] | None = None,
    column_titles: dict[str, str] | None = None,
    products_sheet_title: str = "",
) -> Path:
    """Write user-selected columns first, otherwise use the intent default."""
    if str(intent or "").casefold() == "wine_catalog" and selected_columns is None:
        return write_products_excel_report(
            products,
            shop=shop,
            output_dir=output_dir,
            exported_at=exported_at,
        )
    return write_generic_products_excel_report(
        products,
        shop=shop,
        output_dir=output_dir,
        exported_at=exported_at,
        selected_columns=selected_columns,
        column_titles=column_titles,
        products_sheet_title=products_sheet_title or _selected_columns_sheet_title(products, intent),
    )


def _selected_columns_sheet_title(products: list[Product], intent: str) -> str:
    if str(intent or "").casefold() != "wine_catalog":
        return ""
    return str(products[0].category or "Wine") if products else "Wine"
