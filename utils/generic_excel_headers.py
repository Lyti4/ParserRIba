"""Header helpers for user-renamed Excel report columns."""

from __future__ import annotations

from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet


def display_column_titles(columns: list[str], column_titles: dict[str, str] | None) -> list[str]:
    """Return Excel-facing titles while preserving internal column keys."""
    titles = column_titles or {}
    return [str(titles.get(column) or column) for column in columns]


def has_custom_column_titles(columns: list[str], column_titles: dict[str, str] | None) -> bool:
    """Return true when at least one selected column has a custom Excel title."""
    titles = column_titles or {}
    return any(str(titles.get(column) or "").strip() and str(titles.get(column)) != column for column in columns)


def write_column_schema_sheet(sheet: Worksheet, *, columns: list[str], column_titles: dict[str, str] | None) -> None:
    """Write a compact mapping of internal and Excel-facing column names."""
    sheet.append(["Исходная колонка", "Название в Excel"])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    titles = display_column_titles(columns, column_titles)
    for original, title in zip(columns, titles, strict=False):
        sheet.append([original, title])
    sheet.column_dimensions["A"].width = 36
    sheet.column_dimensions["B"].width = 36
