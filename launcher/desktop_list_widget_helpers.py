"""Small helpers for multi-select list widgets in the desktop launcher."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Iterable


def make_item_checkable(item: Any, checked: bool = False) -> None:
    """Make one list item show a checkbox and set its checked state."""
    qt = _qt()
    item.setFlags(item.flags() | qt.ItemFlag.ItemIsUserCheckable)
    item.setCheckState(qt.CheckState.Checked if checked else qt.CheckState.Unchecked)


def checked_or_selected_items(widget: Any) -> list[Any]:
    """Return checked items, falling back to selected items for compatibility."""
    qt = _qt()
    checked: list[Any] = []
    has_checkable_items = False
    for index in range(int(widget.count())):
        item = widget.item(index)
        if item is None:
            continue
        if item.flags() & qt.ItemFlag.ItemIsUserCheckable:
            has_checkable_items = True
        if item.checkState() == qt.CheckState.Checked:
            checked.append(item)
    if has_checkable_items:
        return checked
    return checked or list(widget.selectedItems())


def set_all_items_selected(widget: Any, selected: bool) -> None:
    """Select or clear every item in one list widget."""
    for index in range(int(widget.count())):
        item = widget.item(index)
        if item is not None:
            item.setSelected(selected)


def clear_multi_select_widgets(widgets: Iterable[Any]) -> None:
    """Clear all selected items across a group of list widgets."""
    qt = _qt()
    for widget in widgets:
        set_all_items_selected(widget, False)
        for index in range(int(widget.count())):
            item = widget.item(index)
            if (
                item is not None
                and hasattr(item, "flags")
                and item.flags() & qt.ItemFlag.ItemIsUserCheckable
            ):
                item.setCheckState(qt.CheckState.Unchecked)


def _qt() -> Any:
    """Load QtCore lazily for list item flags."""
    return import_module("PySide6.QtCore").Qt
