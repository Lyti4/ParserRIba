"""Product mini-catalog helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_dynamic_filter_panel import extract_found_filters, normalize_found_filter_options
from launcher.desktop_list_widget_helpers import checked_or_selected_items, make_item_checkable
from launcher.desktop_state_readers import found_filter_fields

MINI_CATALOG_FIELD = "product_type"


def build_product_mini_catalog_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the local mini-catalog for products collected from one catalog node."""
    box = qtwidgets.QGroupBox("Мини-каталог раздела")
    box.setObjectName("launcherProductMiniCatalogBox")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    label = qtwidgets.QLabel("Быстрый отбор по типам товаров внутри выбранного раздела.")
    label.setWordWrap(True)
    layout.addWidget(label)

    widget = qtwidgets.QListWidget(box)
    widget.setObjectName("launcherProductMiniCatalogList")
    widget.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    widget.setMinimumHeight(64)
    widget.setMaximumHeight(132)
    layout.addWidget(widget)

    shell.product_mini_catalog_box = box
    shell.product_mini_catalog_list = widget
    refresh_product_mini_catalog(shell)
    if hasattr(shell, "_on_filter_changed"):
        widget.itemChanged.connect(shell._on_filter_changed)
    return box


def refresh_product_mini_catalog(shell: Any) -> None:
    """Refresh mini-catalog values from collected product fields."""
    box = getattr(shell, "product_mini_catalog_box", None)
    widget = getattr(shell, "product_mini_catalog_list", None)
    if box is None or widget is None:
        return
    widget.clear()
    options = _mini_catalog_options(shell)
    box.setVisible(bool(options))
    selected = set(shell.state.filters.found_filters.get(MINI_CATALOG_FIELD) or [])
    for value, label in options:
        item = shell._qtwidgets.QListWidgetItem(str(label))
        item.setData(32, str(value))
        make_item_checkable(item, checked=str(value) in selected)
        widget.addItem(item)


def collect_product_mini_catalog_selection(shell: Any) -> list[str]:
    """Collect checked mini-catalog values."""
    widget = getattr(shell, "product_mini_catalog_list", None)
    if widget is None:
        return []
    return [
        str(item.data(32) or item.text())
        for item in checked_or_selected_items(widget)
        if str(item.data(32) or item.text()).strip()
    ]


def _mini_catalog_options(shell: Any) -> list[tuple[str, str]]:
    raw_options = extract_found_filters(found_filter_fields(shell.state)).get(MINI_CATALOG_FIELD)
    if raw_options is None:
        return []
    return [
        (str(value), f"{value} ({count})" if count is not None else str(value))
        for value, count in normalize_found_filter_options(raw_options)
    ]
