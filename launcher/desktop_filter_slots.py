"""Found-filter browser for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import (
    build_option_label,
    extract_found_filters,
    field_title,
    normalize_found_filter_options,
)
from launcher.desktop_filter_helpers import build_filter_option_labels, extract_filter_counts
from launcher.desktop_list_widget_helpers import checked_or_selected_items, make_item_checkable
from launcher.desktop_product_mini_catalog import MINI_CATALOG_FIELD
from launcher.desktop_state_readers import available_filter_counts, found_filter_fields
from launcher.desktop_ui_text import FILTER_TITLES

COUNT_FILTER_FIELD_MAP = {
    "categories": "category",
    "subcategories": "subcategory",
    "sugar_classes": "sugar_class",
    "colors": "color",
}
LOW_PRIORITY_FIELDS = {"special_offers"}
FIELD_PRIORITY = {
    "category": 10,
    "supplier": 20,
    "producer": 25,
    "manufacturer": 25,
    "country": 30,
    "country_of_origin": 30,
    "origin_country": 30,
    "fat": 35,
    "product_state": 36,
    "product_form": 37,
    "weight": 40,
    "volume": 40,
    "packaging": 45,
    "subcategory": 50,
    "alcohol_type": 55,
    "sugar_class": 60,
    "color": 65,
    "special_offers": 900,
}


def build_dynamic_filter_entries(shell: Any) -> list[dict[str, Any]]:
    """Build non-brand filter entries from current launcher state."""
    entries: dict[str, dict[str, Any]] = {}
    filter_counts = available_filter_counts(shell.state)
    for source_name, field_name in COUNT_FILTER_FIELD_MAP.items():
        counts = extract_filter_counts(filter_counts, source_name)
        if not counts:
            continue
        _merge_entry(
            entries,
            field_name=field_name,
            title=FILTER_TITLES.get(source_name) or field_title(field_name),
            options=build_filter_option_labels(counts),
        )
    for field_name, raw_options in extract_found_filters(found_filter_fields(shell.state)).items():
        if field_name in {"brand", MINI_CATALOG_FIELD}:
            continue
        options = normalize_found_filter_options(raw_options)
        if not options:
            continue
        _merge_entry(
            entries,
            field_name=field_name,
            title=field_title(field_name),
            options=[(value, build_option_label(value, count)) for value, count in options],
        )
    return sorted(entries.values(), key=lambda item: (_field_priority(item["field_name"]), item["title"]))


def choose_initial_filter_field(shell: Any, entries: list[dict[str, Any]]) -> str:
    """Choose the initial field without making discount the default."""
    available = [str(entry["field_name"]) for entry in entries]
    for field_name in _active_dynamic_fields(shell):
        if field_name in available:
            return field_name
    for field_name in available:
        if field_name not in LOW_PRIORITY_FIELDS:
            return field_name
    return available[0] if available else ""


def build_filter_browser(
    shell: Any,
    qtwidgets: Any,
    *,
    entries: list[dict[str, Any]],
    current_field: str,
) -> tuple[Any, dict[str, Any]]:
    """Create one browser with found filters on the left and values on the right."""
    group = qtwidgets.QGroupBox("Найденные фильтры")
    group.setObjectName("launcherFoundFilterBrowser")
    layout = qtwidgets.QHBoxLayout(group)
    layout.setContentsMargins(6, 6, 6, 6)
    field_list = qtwidgets.QListWidget(group)
    field_list.setObjectName("launcherFoundFilterFieldList")
    field_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.SingleSelection)
    for entry in entries:
        item = qtwidgets.QListWidgetItem(str(entry["title"]))
        item.setData(32, str(entry["field_name"]))
        field_list.addItem(item)
    field_list.setMinimumWidth(132)
    field_list.setMaximumWidth(170)
    field_list.setCurrentRow(_field_row(field_list, current_field))

    value_list = qtwidgets.QListWidget(group)
    value_list.setObjectName("launcherFoundFilterValueList")
    value_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    value_list.setMinimumHeight(112)
    layout.addWidget(field_list, stretch=0)
    layout.addWidget(value_list, stretch=1)
    browser = {
        "field_list": field_list,
        "widget": value_list,
        "entries": entries,
        "entries_by_field": {str(entry["field_name"]): entry for entry in entries},
    }
    refresh_filter_browser_values(shell, browser)
    field_list.currentRowChanged.connect(lambda *_: _on_browser_field_changed(shell, browser))
    if hasattr(shell, "_on_filter_changed"):
        value_list.itemChanged.connect(shell._on_filter_changed)
    return group, browser


def refresh_filter_browser_values(shell: Any, browser: dict[str, Any]) -> None:
    """Refresh values for the currently selected found filter."""
    widget = browser["widget"]
    field_name = current_browser_field(browser)
    entry = browser["entries_by_field"].get(field_name)
    widget.clear()
    if entry is None:
        return
    selected = _selected_dynamic_values(shell.state.filters, field_name)
    for value, label in entry["options"]:
        item = shell._qtwidgets.QListWidgetItem(str(label))
        item.setData(32, str(value))
        make_item_checkable(item, checked=str(value) in selected)
        widget.addItem(item)
    widget.setMaximumHeight(_list_height(widget.count()))
    shell.found_filter_widgets[field_name] = widget


def collect_browser_filter_selections(shell: Any) -> dict[str, list[str]]:
    """Collect selected values from the found-filter browser."""
    found_filters: dict[str, list[str]] = {
        str(field): [str(item) for item in values if str(item).strip()]
        for field, values in shell.state.filters.found_filters.items()
        if values
    }
    for browser in getattr(shell, "dynamic_filter_slots", []):
        field_name = current_browser_field(browser)
        if not field_name:
            continue
        values = [str(item.data(32) or item.text()) for item in checked_or_selected_items(browser["widget"])]
        if values:
            found_filters[field_name] = list(dict.fromkeys(values))
        else:
            found_filters.pop(field_name, None)
    return found_filters


def current_browser_field(browser: dict[str, Any]) -> str:
    """Return the selected filter field."""
    item = browser["field_list"].currentItem()
    return str(item.data(32) or "") if item is not None else ""


def _merge_entry(
    entries: dict[str, dict[str, Any]],
    *,
    field_name: str,
    title: str,
    options: list[tuple[str, str]],
) -> None:
    target = entries.setdefault(field_name, {"field_name": field_name, "title": title, "options": []})
    seen = {str(value) for value, _ in target["options"]}
    for value, label in options:
        if str(value) in seen:
            continue
        target["options"].append((str(value), str(label)))
        seen.add(str(value))


def _active_dynamic_fields(shell: Any) -> list[str]:
    filters_state = shell.state.filters
    fields = [str(field) for field, values in filters_state.found_filters.items() if values]
    for source_name, field_name in COUNT_FILTER_FIELD_MAP.items():
        if getattr(filters_state, source_name):
            fields.append(field_name)
    return fields


def _selected_dynamic_values(filters_state: Any, field_name: str) -> set[str]:
    selected = filters_state.found_filters.get(field_name)
    if selected:
        return {str(item) for item in selected}
    for source_name, mapped_field in COUNT_FILTER_FIELD_MAP.items():
        if mapped_field == field_name:
            return {str(item) for item in getattr(filters_state, source_name, [])}
    return set()


def _on_browser_field_changed(shell: Any, browser: dict[str, Any]) -> None:
    previous_widgets = getattr(shell, "found_filter_widgets", {})
    for field_name, widget in list(previous_widgets.items()):
        if widget is browser["widget"]:
            previous_widgets.pop(field_name, None)
    refresh_filter_browser_values(shell, browser)
    if hasattr(shell, "_on_filter_changed") and not getattr(shell, "_refreshing_filter_widgets", False):
        shell._on_filter_changed()


def _field_priority(field_name: str) -> int:
    return FIELD_PRIORITY.get(field_name, 500)


def _list_height(option_count: int) -> int:
    return max(112, min(170, 36 + option_count * 24))


def _field_row(field_list: Any, field_name: str) -> int:
    for index in range(field_list.count()):
        if str(field_list.item(index).data(32) or "") == field_name:
            return index
    return 0
