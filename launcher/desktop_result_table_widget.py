"""Qt widget helpers for the desktop launcher result table."""

from __future__ import annotations

from typing import Any


def populate_result_table_widget(
    table: Any,
    qtwidgets: Any,
    qt: Any,
    headers: list[str],
    rows: list[list[str]],
    product_ids: list[str] | None = None,
    selected_product_ids: list[str] | None = None,
) -> None:
    """Populate and configure one desktop result table widget."""
    product_ids = list(product_ids or [])
    selected_product_ids = {
        str(item).strip()
        for item in (selected_product_ids or [])
        if str(item).strip()
    }
    table.blockSignals(True)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(item) for item in headers])
    table.setRowCount(len(rows))
    _configure_result_table_widget(table, qtwidgets, len(headers))
    table.clearSelection()
    for row_index, row in enumerate(rows):
        product_id = product_ids[row_index] if row_index < len(product_ids) else ""
        for column_index, value in enumerate(row):
            item = qtwidgets.QTableWidgetItem(str(value))
            item.setData(qt.ItemDataRole.UserRole, product_id)
            table.setItem(row_index, column_index, item)
        if product_id and product_id in selected_product_ids:
            table.selectRow(row_index)
    table.blockSignals(False)


def _configure_result_table_widget(table: Any, qtwidgets: Any, column_count: int) -> None:
    """Apply one stable desktop presentation profile to the result table."""
    abstract_view = qtwidgets.QAbstractItemView
    table.setEditTriggers(abstract_view.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(abstract_view.SelectionBehavior.SelectRows)
    table.setSelectionMode(abstract_view.SelectionMode.ExtendedSelection)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(True)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    if header is None or column_count == 0:
        return
    resize_mode = qtwidgets.QHeaderView.ResizeMode
    for index in range(column_count):
        header.setSectionResizeMode(index, resize_mode.ResizeToContents)
    if column_count > 1:
        header.setSectionResizeMode(1, resize_mode.Stretch)
    header.setStretchLastSection(column_count > 1)
