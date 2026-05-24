"""PySide6 filter panel helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import build_found_filters_host, refresh_found_filters_panel
from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts
from launcher.desktop_ui_text import (
    FILTER_TITLES,
    STOCK_OPTION_ANY,
    STOCK_OPTION_IN_STOCK,
    STOCK_OPTION_OUT_OF_STOCK,
)

FILTER_WIDGET_KEYS = (
    "suppliers",
    "brands",
    "wine_styles",
    "alcohol_types",
    "sugar_classes",
    "colors",
)


def build_filter_box(shell: Any, qtwidgets: Any) -> Any:
    """Create the filter group box and register list widgets on the shell."""
    box = qtwidgets.QGroupBox("Фильтры")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    for index, filter_name in enumerate(FILTER_WIDGET_KEYS):
        layout.addWidget(qtwidgets.QLabel(FILTER_TITLES[filter_name]), index // 2 * 2, index % 2)
        widget = qtwidgets.QListWidget()
        widget.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
        widget.setMinimumHeight(56)
        widget.setMaximumHeight(72)
        shell.filter_widgets[filter_name] = widget
        layout.addWidget(widget, index // 2 * 2 + 1, index % 2)
    layout.addLayout(_build_filter_value_row(shell, qtwidgets), 6, 0, 1, 2)
    layout.addWidget(build_found_filters_host(shell, qtwidgets), 7, 0, 1, 2)
    action_row = qtwidgets.QHBoxLayout()
    action_row.addStretch(1)
    clear_button = qtwidgets.QPushButton("Сбросить фильтры")
    clear_button.clicked.connect(shell._on_clear_filters)
    shell.filter_action_buttons.append(clear_button)
    action_row.addWidget(clear_button)
    layout.addLayout(action_row, 8, 0, 1, 2)
    refresh_found_filters_panel(shell)
    return box


def refresh_filter_widgets(shell: Any) -> None:
    """Refresh filter option lists from available_filter_counts and current state."""
    launcher_view = shell.state.result.launcher_view
    filters_state = shell.state.filters
    for filter_name, widget in shell.filter_widgets.items():
        selected = {str(item) for item in getattr(filters_state, filter_name)}
        counts = extract_filter_counts(launcher_view, filter_name)
        widget.clear()
        for value, label in build_filter_option_labels(counts):
            item = shell._qtwidgets.QListWidgetItem(label)
            item.setData(32, value)
            widget.addItem(item)
            item.setSelected(value in selected)
    refresh_found_filters_panel(shell)
    _refresh_filter_value_widgets(shell, filters_state)


def collect_filter_selections(shell: Any) -> dict[str, Any]:
    """Collect current filter values from visible filter widgets."""
    selections: dict[str, Any] = {
        filter_name: [str(item.data(32) or item.text()) for item in widget.selectedItems()]
        for filter_name, widget in shell.filter_widgets.items()
    }
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    selections["min_price"] = _normalized_price_value(min_price_widget)
    selections["max_price"] = _normalized_price_value(max_price_widget)
    selections["in_stock"] = _normalized_in_stock_value(in_stock_widget)
    selections["strict_missing"] = bool(strict_missing_widget.isChecked()) if strict_missing_widget is not None else False
    return selections


def _build_filter_value_row(shell: Any, qtwidgets: Any) -> Any:
    """Build the non-facet filter controls row."""
    row = qtwidgets.QGridLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setHorizontalSpacing(8)
    row.setVerticalSpacing(6)
    min_price = qtwidgets.QDoubleSpinBox()
    max_price = qtwidgets.QDoubleSpinBox()
    for widget in (min_price, max_price):
        widget.setRange(0.0, 1_000_000.0)
        widget.setDecimals(2)
        widget.setSingleStep(50.0)
        widget.setSpecialValueText(STOCK_OPTION_ANY)
        shell.filter_extra_widgets.append(widget)
    in_stock = qtwidgets.QComboBox()
    in_stock.addItems([STOCK_OPTION_ANY, STOCK_OPTION_IN_STOCK, STOCK_OPTION_OUT_OF_STOCK])
    strict_missing = qtwidgets.QCheckBox("Строго по заполненным полям")
    shell.filter_extra_widgets.extend([in_stock, strict_missing])
    shell.filter_field_widgets.update(
        {
            "min_price": min_price,
            "max_price": max_price,
            "in_stock": in_stock,
            "strict_missing": strict_missing,
        }
    )
    row.addWidget(qtwidgets.QLabel("Цена от"), 0, 0)
    row.addWidget(min_price, 0, 1)
    row.addWidget(qtwidgets.QLabel("Цена до"), 0, 2)
    row.addWidget(max_price, 0, 3)
    row.addWidget(qtwidgets.QLabel("Наличие"), 0, 4)
    row.addWidget(in_stock, 0, 5)
    row.addWidget(strict_missing, 0, 6)
    row.setColumnStretch(7, 1)
    return row


def _refresh_filter_value_widgets(shell: Any, filters_state: Any) -> None:
    """Sync non-facet filter widgets from launcher filter state."""
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    if min_price_widget is not None:
        min_price_widget.setValue(float(filters_state.min_price or 0.0))
    if max_price_widget is not None:
        max_price_widget.setValue(float(filters_state.max_price or 0.0))
    if in_stock_widget is not None:
        in_stock_widget.setCurrentIndex(_in_stock_index(filters_state.in_stock))
    if strict_missing_widget is not None:
        strict_missing_widget.setChecked(bool(filters_state.strict_missing))


def _normalized_price_value(widget: Any) -> float | None:
    if widget is None:
        return None
    value = float(widget.value())
    return value if value > 0 else None


def _normalized_in_stock_value(widget: Any) -> bool | None:
    if widget is None:
        return None
    current_text = str(widget.currentText() or "")
    if current_text == STOCK_OPTION_IN_STOCK:
        return True
    if current_text == STOCK_OPTION_OUT_OF_STOCK:
        return False
    return None


def _in_stock_index(value: bool | None) -> int:
    if value is True:
        return 1
    if value is False:
        return 2
    return 0
