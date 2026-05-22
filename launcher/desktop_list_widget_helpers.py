"""Small helpers for multi-select list widgets in the desktop launcher."""

from __future__ import annotations

from typing import Any, Iterable


def set_all_items_selected(widget: Any, selected: bool) -> None:
    """Select or clear every item in one list widget."""
    for index in range(int(widget.count())):
        item = widget.item(index)
        if item is not None:
            item.setSelected(selected)


def clear_multi_select_widgets(widgets: Iterable[Any]) -> None:
    """Clear all selected items across a group of list widgets."""
    for widget in widgets:
        set_all_items_selected(widget, False)
