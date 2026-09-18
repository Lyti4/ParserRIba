"""Always-visible value controls for the desktop product filter panel."""

from __future__ import annotations

from typing import Any

from launcher.desktop_ui_text import STOCK_OPTION_ANY, STOCK_OPTION_IN_STOCK, STOCK_OPTION_OUT_OF_STOCK


def build_filter_value_row(shell: Any, qtwidgets: Any) -> Any:
    """Build the always-visible numeric and stock controls."""
    row = qtwidgets.QGridLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setHorizontalSpacing(10)
    row.setVerticalSpacing(6)
    min_price = _build_price_input(qtwidgets, "От")
    max_price = _build_price_input(qtwidgets, "До")
    for widget in (min_price, max_price):
        shell.filter_extra_widgets.append(widget)
    in_stock = qtwidgets.QComboBox()
    in_stock.addItems([STOCK_OPTION_ANY, STOCK_OPTION_IN_STOCK, STOCK_OPTION_OUT_OF_STOCK])
    in_stock.setMinimumWidth(124)
    strict_missing = qtwidgets.QCheckBox("Только заполненные поля")
    strict_missing.setToolTip("Не показывать товары, где выбранное поле фильтра не найдено")
    if hasattr(shell, "_on_filter_changed"):
        min_price.textChanged.connect(shell._on_filter_changed)
        max_price.textChanged.connect(shell._on_filter_changed)
        in_stock.currentIndexChanged.connect(shell._on_filter_changed)
        strict_missing.stateChanged.connect(shell._on_filter_changed)
    shell.filter_extra_widgets.extend([in_stock, strict_missing])
    shell.filter_field_widgets.update(
        {"min_price": min_price, "max_price": max_price, "in_stock": in_stock, "strict_missing": strict_missing}
    )
    row.addWidget(qtwidgets.QLabel("Цена, ₽"), 0, 0)
    row.addWidget(min_price, 0, 1)
    row.addWidget(max_price, 0, 2)
    row.addWidget(qtwidgets.QLabel("Наличие"), 1, 0)
    row.addWidget(in_stock, 1, 1)
    row.addWidget(strict_missing, 1, 2, 1, 2)
    row.setColumnStretch(3, 1)
    return row


def refresh_filter_value_widgets(shell: Any, filters_state: Any) -> None:
    """Sync value filter widgets from launcher filter state."""
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    if min_price_widget is not None:
        _set_price_text(min_price_widget, filters_state.min_price)
    if max_price_widget is not None:
        _set_price_text(max_price_widget, filters_state.max_price)
    if in_stock_widget is not None:
        in_stock_widget.setCurrentIndex(_in_stock_index(filters_state.in_stock))
    if strict_missing_widget is not None:
        strict_missing_widget.setChecked(bool(filters_state.strict_missing))


def normalized_price_value(widget: Any) -> float | None:
    """Return the selected price value or None when the control is set to any."""
    if widget is None:
        return None
    text = str(widget.text() if hasattr(widget, "text") else widget.value()).strip().replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def normalized_in_stock_value(widget: Any) -> bool | None:
    """Return the selected stock filter value."""
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


def _build_price_input(qtwidgets: Any, placeholder: str) -> Any:
    widget = qtwidgets.QLineEdit()
    widget.setPlaceholderText(placeholder)
    widget.setClearButtonEnabled(True)
    widget.setMinimumWidth(92)
    widget.setMaximumWidth(110)
    return widget


def _set_price_text(widget: Any, value: float | None) -> None:
    if value is None:
        widget.setText("")
        return
    widget.setText(f"{float(value):g}")
