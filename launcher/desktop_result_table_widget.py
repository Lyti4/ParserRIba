"""Qt widget helpers for the desktop launcher result table."""

from __future__ import annotations

from typing import Any

PRODUCT_CHECK_HEADER = "Выбор"


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
    has_product_checks = any(str(item).strip() for item in product_ids)
    visible_headers = [str(item) for item in headers] + ([PRODUCT_CHECK_HEADER] if has_product_checks else [])
    selected_product_ids = {
        str(item).strip()
        for item in (selected_product_ids or [])
        if str(item).strip()
    }
    table.blockSignals(True)
    try:
        table.setSortingEnabled(False)
        table.clearSelection()
        table.clearContents()
        table.setRowCount(0)
        table.setColumnCount(len(visible_headers))
        table.setHorizontalHeaderLabels(visible_headers)
        table.setRowCount(len(rows))
        _configure_result_table_widget(table, qtwidgets, len(visible_headers))
        for row_index, row in enumerate(rows):
            product_id = product_ids[row_index] if row_index < len(product_ids) else ""
            for column_index, value in enumerate(row):
                item = qtwidgets.QTableWidgetItem(str(value))
                item.setData(qt.ItemDataRole.UserRole, product_id)
                table.setItem(row_index, column_index, item)
            if has_product_checks:
                checkbox_item = _build_product_checkbox_item(qtwidgets, qt, product_id, product_id in selected_product_ids)
                table.setItem(row_index, len(visible_headers) - 1, checkbox_item)
            if product_id and product_id in selected_product_ids:
                for column_index in range(len(visible_headers)):
                    selected_item = table.item(row_index, column_index)
                    if selected_item is not None:
                        selected_item.setSelected(True)
    finally:
        table.setSortingEnabled(True)
        table.blockSignals(False)


def selected_product_ids_from_table(table: Any, qt: Any) -> list[str]:
    """Read final selected product ids from visible checkbox rows."""
    if _has_product_checkbox_column(table):
        return _checked_product_ids_from_table(table, qt)
    selected_product_ids: list[str] = []
    for item in table.selectedItems():
        product_id = str(item.data(qt.ItemDataRole.UserRole) or "").strip()
        if product_id and product_id not in selected_product_ids:
            selected_product_ids.append(product_id)
    return selected_product_ids


def selected_row_product_ids_from_table(table: Any, qt: Any) -> list[str]:
    """Read product ids from currently highlighted rows for detail preview."""
    selected_product_ids: list[str] = []
    for item in table.selectedItems():
        product_id = str(item.data(qt.ItemDataRole.UserRole) or "").strip()
        if product_id and product_id not in selected_product_ids:
            selected_product_ids.append(product_id)
    return selected_product_ids


def set_all_product_checks(table: Any, qt: Any, checked: bool) -> None:
    """Set every visible product checkbox to one state."""
    checkbox_column = _product_checkbox_column(table)
    if checkbox_column is None:
        return
    table.blockSignals(True)
    try:
        state = qt.CheckState.Checked if checked else qt.CheckState.Unchecked
        for row_index in range(table.rowCount()):
            item = table.item(row_index, checkbox_column)
            if item is not None:
                item.setCheckState(state)
    finally:
        table.blockSignals(False)


def sync_product_select_all_checkbox(table: Any, checkbox: Any, qt: Any) -> None:
    """Reflect visible product row checks in the master checkbox."""
    if table is None or checkbox is None or qt is None:
        return
    states = _visible_product_check_states(table)
    checkbox.blockSignals(True)
    try:
        checkbox.setTristate(True)
        checkbox.setEnabled(bool(states))
        if states and all(state == qt.CheckState.Checked for state in states):
            checkbox.setCheckState(qt.CheckState.Checked)
        elif any(state == qt.CheckState.Checked for state in states):
            checkbox.setCheckState(qt.CheckState.PartiallyChecked)
        else:
            checkbox.setCheckState(qt.CheckState.Unchecked)
    finally:
        checkbox.blockSignals(False)


def _build_product_checkbox_item(qtwidgets: Any, qt: Any, product_id: str, checked: bool) -> Any:
    item = qtwidgets.QTableWidgetItem("")
    item.setData(qt.ItemDataRole.UserRole, product_id)
    item.setFlags(item.flags() | qt.ItemFlag.ItemIsUserCheckable)
    item.setTextAlignment(qt.AlignmentFlag.AlignCenter)
    item.setCheckState(qt.CheckState.Checked if checked else qt.CheckState.Unchecked)
    return item


def _checked_product_ids_from_table(table: Any, qt: Any) -> list[str]:
    selected_product_ids: list[str] = []
    checkbox_column = _product_checkbox_column(table)
    if checkbox_column is None:
        return selected_product_ids
    for row_index in range(table.rowCount()):
        item = table.item(row_index, checkbox_column)
        if item is None or item.checkState() != qt.CheckState.Checked:
            continue
        product_id = str(item.data(qt.ItemDataRole.UserRole) or "").strip()
        if product_id and product_id not in selected_product_ids:
            selected_product_ids.append(product_id)
    return selected_product_ids


def _visible_product_check_states(table: Any) -> list[Any]:
    checkbox_column = _product_checkbox_column(table)
    if checkbox_column is None:
        return []
    states: list[Any] = []
    for row_index in range(table.rowCount()):
        item = table.item(row_index, checkbox_column)
        if item is not None:
            states.append(item.checkState())
    return states


def _has_product_checkbox_column(table: Any) -> bool:
    return _product_checkbox_column(table) is not None


def _product_checkbox_column(table: Any) -> int | None:
    for column_index in range(table.columnCount()):
        header_item = table.horizontalHeaderItem(column_index)
        if header_item is not None and header_item.text() == PRODUCT_CHECK_HEADER:
            return column_index
    return None


def _configure_result_table_widget(table: Any, qtwidgets: Any, column_count: int) -> None:
    """Apply one stable desktop presentation profile to the result table."""
    abstract_view = qtwidgets.QAbstractItemView
    table.setEditTriggers(abstract_view.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(abstract_view.SelectionBehavior.SelectRows)
    table.setSelectionMode(abstract_view.SelectionMode.ExtendedSelection)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.verticalHeader().setDefaultSectionSize(28)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    if header is None or column_count == 0:
        return
    resize_mode = qtwidgets.QHeaderView.ResizeMode
    for index in range(column_count):
        header.setSectionResizeMode(index, resize_mode.ResizeToContents)
    if column_count > 1:
        header.setSectionResizeMode(1, resize_mode.Stretch)
    if column_count > 6:
        table.setColumnWidth(6, 180)
    header.setStretchLastSection(False)
