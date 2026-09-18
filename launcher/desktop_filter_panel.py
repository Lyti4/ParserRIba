"""PySide6 filter panel helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import (
    build_option_label,
    extract_found_filters,
    normalize_found_filter_options,
)
from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts
from launcher.desktop_filter_slots import (
    COUNT_FILTER_FIELD_MAP,
    build_dynamic_filter_entries,
    build_filter_browser,
    choose_initial_filter_field,
    collect_browser_filter_selections,
)
from launcher.desktop_filter_summary import build_selected_filter_box, refresh_selected_filter_summary
from launcher.desktop_filter_value_controls import (
    build_filter_value_row,
    normalized_in_stock_value,
    normalized_price_value,
    refresh_filter_value_widgets,
)
from launcher.desktop_list_widget_helpers import checked_or_selected_items, make_item_checkable
from launcher.desktop_empty_export_guard import clear_stale_filters_for_empty_export
from launcher.desktop_product_mini_catalog import (
    MINI_CATALOG_FIELD,
    build_product_mini_catalog_box,
    collect_product_mini_catalog_selection,
    refresh_product_mini_catalog,
)
from launcher.desktop_state_readers import available_filter_counts, found_filter_fields
from launcher.desktop_ui_text import FILTER_TITLES

FIXED_FILTER_WIDGET_KEYS = ("suppliers",)
FILTER_WIDGET_KEYS = (*FIXED_FILTER_WIDGET_KEYS, *COUNT_FILTER_FIELD_MAP.keys())
FILTERS_ONLY_CATEGORY_TEXT = "В карточках товаров пока не найдено дополнительных полей для фильтрации."
FILTERS_EMPTY_TEXT = "В собранных товарах нет дополнительных полей для фильтрации."
FILTERS_NO_PRODUCTS_TEXT = "Сначала соберите товары. Здесь появятся фильтры из найденных карточек."
FOUND_FILTERS_TITLE = "Найденные фильтры"


def build_filter_box(shell: Any, qtwidgets: Any) -> Any:
    """Create one scrollable dynamic filter workspace."""
    box = qtwidgets.QGroupBox("Отбор товаров")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    layout.addLayout(build_filter_value_row(shell, qtwidgets))
    shell.filter_context_label = qtwidgets.QLabel("")
    shell.filter_context_label.setWordWrap(True)
    layout.addWidget(shell.filter_context_label)
    layout.addWidget(build_selected_filter_box(shell, qtwidgets))
    layout.addWidget(build_product_mini_catalog_box(shell, qtwidgets))

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
    clear_stale_filters_for_empty_export(shell.state)
    shell._refreshing_filter_widgets = True
    try:
        _clear_layout(layout)
        shell.filter_widgets = {}
        shell.filter_search_widgets = {}
        shell.found_filter_widgets = {}
        shell.dynamic_filter_slots = []

        qtwidgets = shell._qtwidgets
        filter_counts = available_filter_counts(shell.state)
        filters_state = shell.state.filters
        visible_count = 0
        meaningful_count = 0

        for filter_name in FIXED_FILTER_WIDGET_KEYS:
            counts = extract_filter_counts(filter_counts, filter_name)
            options = build_filter_option_labels(counts)
            if filter_name == "brands" and not counts:
                options = _found_filter_options(found_filter_fields(shell.state), "brand")
            if not options:
                continue
            selected = {str(item) for item in getattr(filters_state, filter_name)}
            group, widget = _build_filter_group(
                shell,
                qtwidgets,
                field_name=filter_name,
                title=_fixed_filter_title(filter_name),
                options=options,
                selected=selected,
                searchable=True,
            )
            shell.filter_widgets[filter_name] = widget
            layout.addWidget(group)
            visible_count += 1
            meaningful_count += 1

        dynamic_entries = build_dynamic_filter_entries(shell)
        if dynamic_entries:
            group, browser = build_filter_browser(
                shell,
                qtwidgets,
                entries=dynamic_entries,
                current_field=choose_initial_filter_field(shell, dynamic_entries),
            )
            shell.dynamic_filter_slots.append(browser)
            layout.addWidget(group)
            visible_count += 1
            meaningful_count += 1

        if visible_count == 0:
            empty_label = qtwidgets.QLabel(FILTERS_EMPTY_TEXT if shell.state.products.items else FILTERS_NO_PRODUCTS_TEXT)
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)
        elif meaningful_count == 0 and shell.state.products.items:
            empty_label = qtwidgets.QLabel(FILTERS_ONLY_CATEGORY_TEXT)
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)
        layout.addStretch(1)
        _refresh_filter_context(shell, visible_count)
        refresh_product_mini_catalog(shell)
        refresh_selected_filter_summary(shell)
        refresh_filter_value_widgets(shell, filters_state)
    finally:
        shell._refreshing_filter_widgets = False


def collect_filter_selections(shell: Any) -> dict[str, Any]:
    """Collect current filter values from visible dynamic filter widgets."""
    selections: dict[str, Any] = {
        filter_name: [str(item.data(32) or item.text()) for item in checked_or_selected_items(widget)]
        for filter_name, widget in shell.filter_widgets.items()
    }
    for filter_name in FIXED_FILTER_WIDGET_KEYS:
        selections.setdefault(filter_name, [])
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    selections["min_price"] = normalized_price_value(min_price_widget)
    selections["max_price"] = normalized_price_value(max_price_widget)
    selections["in_stock"] = normalized_in_stock_value(in_stock_widget)
    found_filters = collect_browser_filter_selections(shell)
    mini_catalog_values = collect_product_mini_catalog_selection(shell)
    if mini_catalog_values:
        found_filters[MINI_CATALOG_FIELD] = list(dict.fromkeys(mini_catalog_values))
    else:
        found_filters.pop(MINI_CATALOG_FIELD, None)
    selections["found_filters"] = found_filters
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
    searchable: bool = False,
) -> tuple[Any, Any]:
    box = qtwidgets.QGroupBox(title)
    box.setObjectName(f"launcherFilterGroup_{field_name}")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    search_widget = None
    if searchable:
        search_widget = qtwidgets.QLineEdit(box)
        search_widget.setObjectName(f"launcherFilterSearch_{field_name}")
        search_widget.setPlaceholderText("Поиск по первым буквам")
        layout.addWidget(search_widget)
    widget = qtwidgets.QListWidget(box)
    widget.setObjectName(f"launcherFilterList_{field_name}")
    widget.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    widget.setMinimumHeight(64)
    widget.setMaximumHeight(_list_height(len(options)))
    for value, label in options:
        item = qtwidgets.QListWidgetItem(label)
        item.setData(32, value)
        make_item_checkable(item, checked=value in selected)
        widget.addItem(item)
    if hasattr(shell, "_on_filter_changed"):
        widget.itemChanged.connect(shell._on_filter_changed)
    if search_widget is not None:
        search_widget.textChanged.connect(lambda text: _apply_filter_search(widget, str(text or "")))
        shell.filter_search_widgets[field_name] = search_widget
    layout.addWidget(widget)
    return box, widget


def _fixed_filter_title(filter_name: str) -> str:
    if filter_name == "brands":
        return "Бренды"
    if filter_name == "suppliers":
        return "Поставщики / производители"
    return FILTER_TITLES[filter_name]


def _apply_filter_search(widget: Any, query: str) -> None:
    normalized_query = _normalize_search_text(query)
    for index in range(widget.count()):
        item = widget.item(index)
        label = str(item.text() or "")
        value = str(item.data(32) or "")
        item.setHidden(bool(normalized_query) and not _matches_filter_search(label, value, normalized_query))


def _matches_filter_search(label: str, value: str, query: str) -> bool:
    for candidate in (label, value):
        normalized = _normalize_search_text(candidate)
        if normalized.startswith(query):
            return True
        if any(part.startswith(query) for part in normalized.replace("/", " ").replace("-", " ").split()):
            return True
    return False


def _normalize_search_text(value: str) -> str:
    return " ".join(str(value or "").casefold().replace("ё", "е").split())


def _found_filter_options(found_filters: Any, field_name: str) -> list[tuple[str, str]]:
    raw_options = extract_found_filters(found_filters).get(field_name)
    if raw_options is None:
        return []
    return [(value, build_option_label(value, count)) for value, count in normalize_found_filter_options(raw_options)]


def _refresh_filter_context(shell: Any, visible_count: int) -> None:
    label = getattr(shell, "filter_context_label", None)
    if label is None:
        return
    product_count = len(shell.state.products.items)
    categories = [str(item).strip() for item in shell.state.products.source_categories if str(item).strip()]
    section = ", ".join(categories[:3]) if categories else "текущая рабочая область"
    label.setText(f"Фильтры построены по разделу: {section}; товаров: {product_count}; найдено фильтров: {visible_count}")


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
