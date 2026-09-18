"""Helpers for selecting report columns from the product workspace."""

from __future__ import annotations

from typing import Any

from utils.generic_excel_report import BASE_COLUMNS, CORE_RAW_FIELDS, RAW_FIELD_TITLES, TECHNICAL_RAW_FIELDS
from utils.product_display_fields import product_alcohol_type_name, product_supplier_name, product_type_name

ALWAYS_REPORT_COLUMN_INDEXES = (0, 1, 3, 6, 9, 24, 26, 27)
NORMALIZED_REPORT_COLUMN_INDEXES = {
    "product_type": 2,
    "brand": 4,
    "supplier": 5,
    "producer": 5,
    "manufacturer": 5,
    "vendor": 5,
    "old_price": 7,
    "regular_price": 7,
    "previous_price": 7,
    "unit_price": 8,
    "price_per_unit": 8,
    "weight": 10,
    "volume": 11,
    "fat_percent": 12,
    "fat": 18,
    "product_state": 13,
    "product_form": 14,
    "packaging": 15,
    "country": 16,
    "country_of_origin": 16,
    "origin_country": 16,
    "protein": 17,
    "carbohydrate": 19,
    "calories": 20,
    "composition": 21,
    "storage_conditions": 22,
    "shelf_life": 23,
    "image": 25,
}


def build_report_column_options(products: list[dict[str, Any]]) -> list[str]:
    """Return report columns available for the current report product scope."""
    if not products:
        return []
    columns = [BASE_COLUMNS[index] for index in ALWAYS_REPORT_COLUMN_INDEXES]
    for product in products:
        _add_normalized_product_columns(columns, product)
        raw_data = product.get("raw_data")
        raw = raw_data if isinstance(raw_data, dict) else {}
        for key in sorted(raw):
            if key in TECHNICAL_RAW_FIELDS or raw.get(key) in ("", [], {}, None):
                continue
            if key in CORE_RAW_FIELDS or key in NORMALIZED_REPORT_COLUMN_INDEXES:
                _add_column(columns, _column_for_raw_key(key))
                continue
            _add_column(columns, RAW_FIELD_TITLES.get(str(key), "Поле: " + str(key).replace("_", " ")))
    return columns


def normalize_selected_report_columns(available: list[str], selected: list[str]) -> list[str]:
    """Keep selected columns valid for the available column list."""
    allowed = [str(item) for item in available if str(item).strip()]
    return [str(item) for item in selected if str(item) in allowed]


def build_report_preview_rows(
    products: list[dict[str, Any]],
    columns: list[str],
    column_titles: dict[str, str] | None = None,
    *,
    limit: int = 20,
) -> dict[str, list[list[str]] | list[str]]:
    """Build a small user-facing report preview table."""
    headers = [str((column_titles or {}).get(column) or column) for column in columns]
    rows = [[_preview_value(product, column) for column in columns] for product in products[:limit]]
    return {"headers": headers, "rows": rows}


def _add_normalized_product_columns(columns: list[str], product: dict[str, Any]) -> None:
    raw_data = product.get("raw_data")
    raw = raw_data if isinstance(raw_data, dict) else {}
    if product_type_name(product):
        _add_column(columns, BASE_COLUMNS[2])
    if _has_distinct_brand(product):
        _add_column(columns, BASE_COLUMNS[4])
    if product_supplier_name(product):
        _add_column(columns, BASE_COLUMNS[5])
    price = product.get("price")
    price_dict = price if isinstance(price, dict) else {}
    if any(price_dict.get(key) not in (None, "", [], {}) for key in ("old", "regular", "previous")):
        _add_column(columns, BASE_COLUMNS[7])
    for key, column_index in NORMALIZED_REPORT_COLUMN_INDEXES.items():
        if _has_raw_value(raw, key):
            _add_column(columns, BASE_COLUMNS[column_index])
    if product.get("image") or product.get("image_url") or _has_raw_value(raw, "image"):
        _add_column(columns, BASE_COLUMNS[25])


def _column_for_raw_key(key: str) -> str:
    index = NORMALIZED_REPORT_COLUMN_INDEXES.get(str(key))
    if index is not None:
        return BASE_COLUMNS[index]
    return RAW_FIELD_TITLES.get(str(key), "Поле: " + str(key).replace("_", " "))


def _has_raw_value(raw: dict[str, Any], key: str) -> bool:
    return raw.get(key) not in (None, "", [], {})


def _add_column(columns: list[str], title: str) -> None:
    if title and title not in columns:
        columns.append(title)


def _preview_value(product: dict[str, Any], column: str) -> str:
    raw_data = product.get("raw_data")
    raw = raw_data if isinstance(raw_data, dict) else {}
    price = product.get("price")
    price_dict = price if isinstance(price, dict) else {}
    base_values = {
        BASE_COLUMNS[0]: "",
        BASE_COLUMNS[1]: product.get("category"),
        BASE_COLUMNS[2]: product_type_name(product),
        BASE_COLUMNS[3]: product.get("name"),
        BASE_COLUMNS[4]: product.get("brand") or raw.get("brand"),
        BASE_COLUMNS[5]: product_supplier_name(product),
        BASE_COLUMNS[6]: price_dict.get("current") if price_dict else product.get("price"),
        BASE_COLUMNS[7]: price_dict.get("old") or price_dict.get("regular") or price_dict.get("previous"),
        BASE_COLUMNS[8]: price_dict.get("unit"),
        BASE_COLUMNS[9]: "Да" if product.get("in_stock") else "Нет",
        BASE_COLUMNS[24]: product.get("product_link"),
        BASE_COLUMNS[25]: product.get("image") or product.get("image_url") or raw.get("image"),
        BASE_COLUMNS[26]: product.get("id") or product.get("product_id"),
        BASE_COLUMNS[27]: product.get("exported_at") or raw.get("exported_at"),
    }
    if column == RAW_FIELD_TITLES.get("alcohol_type"):
        return product_alcohol_type_name(product)
    for key, index in NORMALIZED_REPORT_COLUMN_INDEXES.items():
        if raw.get(key) not in (None, "", [], {}) and BASE_COLUMNS[index] == column:
            return _stringify_preview(raw.get(key))
    value = base_values.get(column)
    if value in (None, "", [], {}):
        value = _raw_value_by_title(raw, column)
    return _stringify_preview(value)


def _has_distinct_brand(product: dict[str, Any]) -> bool:
    raw_data = product.get("raw_data")
    raw = raw_data if isinstance(raw_data, dict) else {}
    brand = str(product.get("brand") or raw.get("brand") or "").strip()
    supplier = product_supplier_name(product)
    return bool(brand and brand.casefold() != supplier.casefold())


def _raw_value_by_title(raw: dict[str, Any], column: str) -> Any:
    for key, title in RAW_FIELD_TITLES.items():
        if title == column and raw.get(key) not in (None, "", [], {}):
            return raw.get(key)
    prefix = "Поле: "
    if column.startswith(prefix):
        return raw.get(column[len(prefix):].replace(" ", "_"))
    return ""


def _stringify_preview(value: Any) -> str:
    if value in (None, [], {}):
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
