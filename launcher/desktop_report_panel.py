"""Report tab widgets and column-selection synchronization."""

from __future__ import annotations

from typing import Any

from launcher.desktop_report_columns import build_report_column_options, build_report_preview_rows, normalize_selected_report_columns
from launcher.desktop_state_readers import report_product_items


def build_report_box(shell: Any, qtwidgets: Any) -> Any:
    """Build report-stage controls with selectable Excel columns."""
    box = qtwidgets.QGroupBox("Отчёт")
    layout = qtwidgets.QVBoxLayout(box)
    shell.report_columns_label = qtwidgets.QLabel("")
    shell.report_columns_label.setWordWrap(True)
    shell.report_column_list = qtwidgets.QListWidget()
    shell.report_column_list.setObjectName("launcherReportColumnList")
    shell.report_column_list.setMinimumHeight(180)
    shell.report_column_list.itemChanged.connect(shell._on_report_columns_changed)
    shell.report_preview_table = qtwidgets.QTableWidget(0, 0)
    shell.report_preview_table.setObjectName("launcherReportPreviewTable")
    shell.report_preview_table.setEditTriggers(qtwidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    shell.report_preview_table.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.NoSelection)
    shell.report_preview_table.setAlternatingRowColors(True)
    layout.addWidget(shell.report_columns_label)
    layout.addWidget(shell.report_column_list, stretch=1)
    layout.addWidget(shell.report_preview_table, stretch=2)
    layout.addWidget(
        _button_row(
            shell,
            qtwidgets,
            (
                ("select_report_columns", "Выбрать все столбцы", shell._on_select_all_report_columns),
                ("clear_report_columns", "Снять выбор столбцов", shell._on_clear_report_columns),
                ("build_report", "Собрать Excel", shell._on_build_report),
                ("open_excel", "Открыть Excel", shell._on_open_excel),
                ("open_folder", "Открыть папку", shell._on_open_report_dir),
            ),
        )
    )
    refresh_report_preview(shell)
    return box


def refresh_report_columns(shell: Any) -> None:
    """Refresh report-column checkboxes from current products and state."""
    widget = getattr(shell, "report_column_list", None)
    if widget is None or shell._qt is None:
        return
    available = build_report_column_options(report_product_items(shell.state))
    selected = (
        normalize_selected_report_columns(available, shell.state.report.selected_columns)
        if shell.state.report.columns_touched
        else list(available)
    )
    shell.state.report.available_columns = available
    shell.state.report.selected_columns = selected
    widget.blockSignals(True)
    widget.clear()
    for column in available:
        item = shell._qtwidgets.QListWidgetItem(column)
        item.setData(shell._qt.ItemDataRole.UserRole, column)
        item.setFlags(item.flags() | shell._qt.ItemFlag.ItemIsUserCheckable | shell._qt.ItemFlag.ItemIsEditable)
        item.setText(str(shell.state.report.column_titles.get(column) or column))
        item.setCheckState(
            shell._qt.CheckState.Checked
            if column in selected
            else shell._qt.CheckState.Unchecked
        )
        widget.addItem(item)
    widget.blockSignals(False)
    if shell.report_columns_label is not None:
        shell.report_columns_label.setText(_caption(available, selected))
    refresh_report_preview(shell)


def collect_report_columns(shell: Any) -> list[str]:
    """Collect checked report columns from the report tab."""
    widget = getattr(shell, "report_column_list", None)
    if widget is None or shell._qt is None:
        return list(shell.state.report.selected_columns)
    columns: list[str] = []
    for index in range(widget.count()):
        item = widget.item(index)
        if item.checkState() == shell._qt.CheckState.Checked:
            columns.append(str(item.data(shell._qt.ItemDataRole.UserRole) or item.text()))
    return normalize_selected_report_columns(shell.state.report.available_columns, columns)


def collect_report_column_titles(shell: Any) -> dict[str, str]:
    """Collect user-facing Excel titles without changing internal column keys."""
    widget = getattr(shell, "report_column_list", None)
    if widget is None or shell._qt is None:
        return dict(shell.state.report.column_titles)
    titles: dict[str, str] = {}
    for index in range(widget.count()):
        item = widget.item(index)
        column = str(item.data(shell._qt.ItemDataRole.UserRole) or "").strip()
        title = str(item.text() or "").strip()
        if column and title and title != column:
            titles[column] = title
    return titles


def handle_report_columns_changed(shell: Any) -> None:
    """Persist report-column checks and refresh the caption."""
    shell.state.report.columns_touched = True
    shell.state.report.selected_columns = collect_report_columns(shell)
    shell.state.report.column_titles = collect_report_column_titles(shell)
    if shell.report_columns_label is not None:
        selected = len(shell.state.report.selected_columns)
        available = len(shell.state.report.available_columns)
        shell.report_columns_label.setText(
            f"Доступно столбцов: {available} | выбрано для отчёта: {selected}"
        )


    refresh_report_preview(shell)


def set_report_column_selection(shell: Any, checked: bool) -> None:
    """Check or uncheck every report column."""
    widget = getattr(shell, "report_column_list", None)
    if widget is None or shell._qt is None:
        return
    for index in range(widget.count()):
        widget.item(index).setCheckState(
            shell._qt.CheckState.Checked if checked else shell._qt.CheckState.Unchecked
        )
    shell.state.report.selected_columns = collect_report_columns(shell)
    shell.state.report.columns_touched = True
    refresh_report_preview(shell)


def refresh_report_preview(shell: Any) -> None:
    """Refresh the report tab preview from selected columns and current products."""
    table = getattr(shell, "report_preview_table", None)
    if table is None or shell._qtwidgets is None:
        return
    preview = build_report_preview_rows(
        report_product_items(shell.state),
        shell.state.report.selected_columns,
        shell.state.report.column_titles,
        limit=20,
    )
    headers = preview["headers"]
    rows = preview["rows"]
    table.blockSignals(True)
    try:
        table.clear()
        table.setColumnCount(len(headers))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, shell._qtwidgets.QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
    finally:
        table.blockSignals(False)


def _button_row(shell: Any, qtwidgets: Any, actions: tuple[tuple[str, str, Any], ...]) -> Any:
    row = qtwidgets.QWidget()
    layout = qtwidgets.QGridLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    for index, (key, label, handler) in enumerate(actions):
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.action_buttons[key] = button
        layout.addWidget(button, 0, index)
        layout.setColumnStretch(index, 1)
    return row


def _caption(available: list[str], selected: list[str]) -> str:
    if not available:
        return "Сначала соберите товары, после этого здесь появятся столбцы отчёта."
    return f"Доступно столбцов: {len(available)} | выбрано для отчёта: {len(selected)}"
