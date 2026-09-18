"""Selected-filter summary widgets for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import field_title
from launcher.desktop_list_widget_helpers import make_item_checkable
from launcher.desktop_ui_text import FILTER_TITLES


FIXED_FILTER_LABELS = (
    ("brands", "Бренды"),
    ("categories", "Категории"),
    ("suppliers", "Поставщики"),
    ("subcategories", "Подкатегория"),
    ("alcohol_types", "Алкогольный тип"),
    ("sugar_classes", "Сахар"),
    ("colors", "Цвет"),
)


def build_selected_filter_box(shell: Any, qtwidgets: Any) -> Any:
    """Build a compact read-only list of active product filters."""
    box = qtwidgets.QGroupBox("Выбранные фильтры")
    box.setObjectName("launcherSelectedFiltersBox")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    summary_list = qtwidgets.QListWidget(box)
    summary_list.setObjectName("launcherSelectedFiltersList")
    summary_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.NoSelection)
    summary_list.setMinimumHeight(54)
    summary_list.setMaximumHeight(118)
    layout.addWidget(summary_list)

    clear_button = qtwidgets.QPushButton("Сбросить фильтры")
    clear_button.setObjectName("launcherSelectedFiltersClearButton")
    clear_button.clicked.connect(shell._on_clear_filters)
    layout.addWidget(clear_button)

    shell.selected_filters_box = box
    shell.selected_filters_list = summary_list
    shell.filter_action_buttons.append(clear_button)
    refresh_selected_filter_summary(shell)
    return box


def refresh_selected_filter_summary(shell: Any) -> None:
    """Refresh the visible active-filter summary from launcher state."""
    summary_list = getattr(shell, "selected_filters_list", None)
    qt = getattr(shell, "_qt", None)
    if summary_list is None or qt is None:
        return
    summary_list.clear()
    labels = active_filter_labels(shell.state)
    if not labels:
        item = shell._qtwidgets.QListWidgetItem("Фильтры не выбраны")
        item.setFlags(item.flags() & ~qt.ItemFlag.ItemIsEnabled)
        summary_list.addItem(item)
        return
    for label in labels:
        item = shell._qtwidgets.QListWidgetItem(label)
        make_item_checkable(item, checked=True)
        item.setFlags(item.flags() & ~qt.ItemFlag.ItemIsUserCheckable)
        summary_list.addItem(item)


def active_filter_labels(state: Any) -> list[str]:
    """Return readable labels for all currently selected product filters."""
    filters = state.filters
    labels: list[str] = []
    for field_name, title in FIXED_FILTER_LABELS:
        values = [str(item).strip() for item in getattr(filters, field_name) if str(item).strip()]
        labels.extend(_value_labels(title, values))
    labels.extend(_price_labels(filters.min_price, filters.max_price))
    if filters.in_stock is not None:
        labels.append(f"Наличие: {'в наличии' if filters.in_stock else 'нет в наличии'}")
    if filters.strict_missing:
        labels.append("Строгий режим: включён")
    for field_name, values in sorted(filters.found_filters.items(), key=lambda item: field_title(str(item[0]))):
        title = FILTER_TITLES.get(str(field_name)) or field_title(str(field_name))
        labels.extend(_value_labels(title, [str(item).strip() for item in values if str(item).strip()]))
    return labels


def _value_labels(title: str, values: list[str]) -> list[str]:
    if not values:
        return []
    if len(values) <= 3:
        return [f"{title}: {', '.join(values)}"]
    return [f"{title}: {', '.join(values[:3])} + ещё {len(values) - 3}"]


def _price_labels(min_price: float | None, max_price: float | None) -> list[str]:
    if min_price is None and max_price is None:
        return []
    if min_price is not None and max_price is not None:
        return [f"Цена: {min_price:g} - {max_price:g} ₽"]
    if min_price is not None:
        return [f"Цена: от {min_price:g} ₽"]
    return [f"Цена: до {max_price:g} ₽"]
