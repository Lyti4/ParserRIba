"""Dynamic found-filters panel helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_state_readers import found_filter_fields
from launcher.desktop_ui_text import FILTER_TITLES

FOUND_FILTERS_TITLE = "Найденные фильтры"


def build_found_filters_host(shell: Any, qtwidgets: Any) -> Any:
    """Create the placeholder widget that hosts the dynamic found-filters group."""
    host = qtwidgets.QWidget()
    host.setObjectName("launcherFoundFiltersHost")
    layout = qtwidgets.QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    shell.found_filters_host = host
    shell.found_filters_layout = layout
    shell.found_filters_group = None
    shell.found_filter_widgets = {}
    return host


def refresh_found_filters_panel(shell: Any) -> None:
    """Rebuild the dynamic found-filters panel from structured product fields."""
    layout = getattr(shell, "found_filters_layout", None)
    if layout is None:
        return
    _clear_layout(layout)
    shell.found_filters_group = None
    shell.found_filter_widgets = {}

    found_filters = _extract_found_filters(found_filter_fields(shell.state))
    if not found_filters:
        return

    qtwidgets = getattr(shell, "_qtwidgets", None)
    if qtwidgets is None:
        return

    group = qtwidgets.QGroupBox(FOUND_FILTERS_TITLE)
    group_layout = qtwidgets.QVBoxLayout(group)
    group_layout.setContentsMargins(8, 8, 8, 8)
    group_layout.setSpacing(8)

    scroll_area = qtwidgets.QScrollArea()
    scroll_area.setObjectName("launcherFoundFiltersScrollArea")
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(qtwidgets.QFrame.Shape.NoFrame)

    content = qtwidgets.QWidget()
    content_layout = qtwidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(8)

    for field_name, raw_options in found_filters.items():
        content_layout.addWidget(_build_found_filter_field_box(shell, qtwidgets, field_name, raw_options))

    content_layout.addStretch(1)
    scroll_area.setWidget(content)
    group_layout.addWidget(scroll_area)
    layout.addWidget(group)
    shell.found_filters_group = group


def _build_found_filter_field_box(shell: Any, qtwidgets: Any, field_name: str, raw_options: Any) -> Any:
    """Build one found-filters field group."""
    box = qtwidgets.QGroupBox(_field_title(field_name))
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(4)

    widget = qtwidgets.QListWidget()
    widget.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    widget.setMinimumHeight(56)

    for value, count in _normalize_found_filter_options(raw_options):
        item = qtwidgets.QListWidgetItem(_build_option_label(value, count))
        item.setData(32, value)
        widget.addItem(item)

    shell.found_filter_widgets[field_name] = widget
    layout.addWidget(widget)
    return box


def _extract_found_filters(found_filters: Any) -> dict[str, Any]:
    if not isinstance(found_filters, dict):
        return {}
    result: dict[str, Any] = {}
    for field_name, raw_options in found_filters.items():
        key = str(field_name or "").strip()
        if key:
            result[key] = raw_options
    return result


def _normalize_found_filter_options(raw_options: Any) -> list[tuple[str, int | None]]:
    if isinstance(raw_options, dict):
        result: list[tuple[str, int | None]] = []
        for raw_label, raw_value in raw_options.items():
            label, count = _coerce_option_pair(raw_label, raw_value)
            if label:
                result.append((label, count))
        return sorted(result, key=lambda item: item[0].casefold())
    if isinstance(raw_options, list):
        result = []
        for item in raw_options:
            label, count = _coerce_option_from_item(item)
            if label:
                result.append((label, count))
        return result
    label = str(raw_options or "").strip()
    return [(label, None)] if label else []


def _coerce_option_pair(raw_label: Any, raw_value: Any) -> tuple[str, int | None]:
    if isinstance(raw_value, dict):
        label = str(raw_value.get("value") or raw_value.get("label") or raw_value.get("name") or raw_label or "").strip()
        count = _coerce_count(raw_value.get("count"))
        return label, count
    label = str(raw_label or "").strip()
    return label, _coerce_count(raw_value)


def _coerce_option_from_item(item: Any) -> tuple[str, int | None]:
    if isinstance(item, dict):
        label = str(item.get("value") or item.get("label") or item.get("name") or "").strip()
        count = _coerce_count(item.get("count"))
        if not label and item:
            label = str(next(iter(item.values()))).strip()
        return label, count
    label = str(item or "").strip()
    return label, None


def _coerce_count(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_option_label(label: str, count: int | None) -> str:
    return f"{label} ({count})" if count is not None else label


def _field_title(field_name: str) -> str:
    return FILTER_TITLES.get(field_name) or field_name.replace("_", " ").strip().title() or field_name


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
