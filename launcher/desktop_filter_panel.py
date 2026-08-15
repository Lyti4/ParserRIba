"""PySide6 filter panel helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import (
    build_option_label,
    extract_found_filters,
    field_title,
    normalize_found_filter_options,
)
from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts
from launcher.desktop_state_readers import available_filter_counts, found_filter_fields
from launcher.desktop_ui_text import (
    FILTER_TITLES,
    STOCK_OPTION_ANY,
    STOCK_OPTION_IN_STOCK,
    STOCK_OPTION_OUT_OF_STOCK,
)

FILTER_WIDGET_KEYS = (
    "categories",
    "suppliers",
    "brands",
    "wine_styles",
    "alcohol_types",
    "sugar_classes",
    "colors",
)
FILTERS_EMPTY_TEXT = "В собранных товарах нет дополнительных полей для фильтрации."
FILTERS_NO_PRODUCTS_TEXT = "Сначала соберите товары. Здесь появятся фильтры из найденных карточек."
FOUND_FILTERS_TITLE = "Найденные фильтры"


def build_filter_box(shell: Any, qtwidgets: Any) -> Any:
    """Create one scrollable dynamic filter workspace."""
    box = qtwidgets.QGroupBox("Фильтры")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    layout.addLayout(_build_filter_value_row(shell, qtwidgets))
    shell.filter_context_label = qtwidgets.QLabel("")
    shell.filter_context_label.setWordWrap(True)
    layout.addWidget(shell.filter_context_label)

    scroll_area = qtwidgets.QScrollArea()
    scroll_area.setObjectName("launcherDynamicFiltersScrollArea")
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(qtwidgets.QFrame.Shape.NoFrame)

    content = qtwidgets.QWidget()
    content_layout = qtwidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(8)
    shell.dynamic_filter_content = content
    shell.dynamic_filter_layout = content_layout
    scroll_area.setWidget(content)
    layout.addWidget(scroll_area, stretch=1)

    action_row = qtwidgets.QHBoxLayout()
    action_row.addStretch(1)
    apply_button = qtwidgets.QPushButton("Применить фильтры к товарам")
    apply_button.clicked.connect(shell._on_apply_filters)
    shell.filter_action_buttons.append(apply_button)
    action_row.addWidget(apply_button)
    show_all_button = qtwidgets.QPushButton("Показать все товары")
    show_all_button.clicked.connect(shell._on_show_all_products)
    shell.filter_action_buttons.append(show_all_button)
    action_row.addWidget(show_all_button)
    clear_button = qtwidgets.QPushButton("Сбросить фильтры")
    clear_button.clicked.connect(shell._on_clear_filters)
    shell.filter_action_buttons.append(clear_button)
    action_row.addWidget(clear_button)
    layout.addLayout(action_row)
    refresh_filter_widgets(shell)
    return box


def refresh_filter_widgets(shell: Any) -> None:
    """Refresh visible dynamic filters from collected product fields."""
    layout = getattr(shell, "dynamic_filter_layout", None)
    if layout is None:
        return
    _clear_layout(layout)
    shell.filter_widgets = {}
    shell.found_filter_widgets = {}

    qtwidgets = shell._qtwidgets
    filter_counts = available_filter_counts(shell.state)
    filters_state = shell.state.filters
    visible_count = 0

    for filter_name in FILTER_WIDGET_KEYS:
        counts = extract_filter_counts(filter_counts, filter_name)
        if not counts:
            continue
        selected = {str(item) for item in getattr(filters_state, filter_name)}
        group, widget = _build_filter_group(
            shell,
            qtwidgets,
            field_name=filter_name,
            title=FILTER_TITLES[filter_name],
            options=build_filter_option_labels(counts),
            selected=selected,
        )
        shell.filter_widgets[filter_name] = widget
        layout.addWidget(group)
        visible_count += 1

    for field_name, raw_options in extract_found_filters(found_filter_fields(shell.state)).items():
        options = normalize_found_filter_options(raw_options)
        if not options:
            continue
        selected = set(filters_state.found_filters.get(field_name, []))
        group, widget = _build_filter_group(
            shell,
            qtwidgets,
            field_name=field_name,
            title=f"{FOUND_FILTERS_TITLE}: {field_title(field_name)}",
            options=[(value, build_option_label(value, count)) for value, count in options],
            selected=selected,
        )
        shell.found_filter_widgets[field_name] = widget
        layout.addWidget(group)
        visible_count += 1

    if visible_count == 0:
        empty_label = qtwidgets.QLabel(FILTERS_EMPTY_TEXT if shell.state.products.items else FILTERS_NO_PRODUCTS_TEXT)
        empty_label.setWordWrap(True)
        layout.addWidget(empty_label)
    layout.addStretch(1)
    _refresh_filter_context(shell, visible_count)
    _refresh_filter_value_widgets(shell, filters_state)


def collect_filter_selections(shell: Any) -> dict[str, Any]:
    """Collect current filter values from visible dynamic filter widgets."""
    selections: dict[str, Any] = {
        filter_name: [str(item.data(32) or item.text()) for item in widget.selectedItems()]
        for filter_name, widget in shell.filter_widgets.items()
    }
    for filter_name in FILTER_WIDGET_KEYS:
        selections.setdefault(filter_name, [])
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    selections["min_price"] = _normalized_price_value(min_price_widget)
    selections["max_price"] = _normalized_price_value(max_price_widget)
    selections["in_stock"] = _normalized_in_stock_value(in_stock_widget)
    selections["found_filters"] = {
        str(field_name): [str(item.data(32) or item.text()) for item in widget.selectedItems()]
        for field_name, widget in getattr(shell, "found_filter_widgets", {}).items()
        if widget.selectedItems()
    }
    selections["strict_missing"] = bool(strict_missing_widget.isChecked()) if strict_missing_widget is not None else False
    return selections


def _build_filter_group(
    shell: Any,
    qtwidgets: Any,
    *,
    field_name: str,
    title: str,
    options: list[tuple[str, str]],
    selected: set[str],
) -> tuple[Any, Any]:
    box = qtwidgets.QGroupBox(title)
    box.setObjectName(f"launcherFilterGroup_{field_name}")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    widget = qtwidgets.QListWidget(box)
    widget.setObjectName(f"launcherFilterList_{field_name}")
    widget.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    widget.setMinimumHeight(64)
    widget.setMaximumHeight(_list_height(len(options)))
    for value, label in options:
        item = qtwidgets.QListWidgetItem(label)
        item.setData(32, value)
        widget.addItem(item)
        item.setSelected(value in selected)
    layout.addWidget(widget)
    return box, widget


def _build_filter_value_row(shell: Any, qtwidgets: Any) -> Any:
    """Build the always-visible numeric and stock controls."""
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


def _refresh_filter_context(shell: Any, visible_count: int) -> None:
    label = getattr(shell, "filter_context_label", None)
    if label is None:
        return
    product_count = len(shell.state.products.items)
    categories = [str(item).strip() for item in shell.state.products.source_categories if str(item).strip()]
    section = ", ".join(categories[:3]) if categories else "текущая рабочая область"
    label.setText(f"Фильтры построены по разделу: {section}; товаров: {product_count}; найдено фильтров: {visible_count}")


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


def _list_height(option_count: int) -> int:
    return max(84, min(150, 30 + option_count * 24))


def _clear_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif child_layout is not None:
            _clear_layout(child_layout)
            child_layout.deleteLater()
