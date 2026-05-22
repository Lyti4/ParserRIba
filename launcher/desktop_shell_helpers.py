"""Small UI helpers shared by the desktop launcher shell."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from launcher.desktop_list_widget_helpers import clear_multi_select_widgets, set_all_items_selected


def load_pyside6() -> tuple[Any, Any, Any]:
    """Load PySide6 lazily so non-GUI environments can still import the shell."""
    try:
        qtwidgets = import_module("PySide6.QtWidgets")
        qtcore = import_module("PySide6.QtCore")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "PySide6 is not installed. Install desktop dependencies before running the launcher."
        ) from error
    return qtwidgets.QApplication, qtwidgets, qtcore.Qt


def build_window_icon(root_dir: Path | str) -> Any | None:
    """Build a Qt window icon from the local launcher asset when available."""
    icon_path = resolve_launcher_icon_path(root_dir)
    if not icon_path.exists():
        return None
    qtgui = import_module("PySide6.QtGui")
    return qtgui.QIcon(str(icon_path))


def resolve_launcher_icon_path(root_dir: Path | str) -> Path:
    """Resolve the local launcher icon asset path inside the project."""
    assets_dir = Path(root_dir) / "launcher" / "assets"
    ico_path = assets_dir / "parserriba_launcher.ico"
    if ico_path.exists():
        return ico_path
    return assets_dir / "parserriba_launcher.svg"


def sync_setting_widgets(shell: Any) -> None:
    """Push launcher settings state into the visible widgets."""
    for widget, value in (
        (shell.headless_checkbox, shell.state.settings.headless),
        (shell.manual_wait_checkbox, shell.state.settings.manual_wait),
        (shell.attempts_spin, shell.state.settings.attempts),
        (shell.listen_seconds_spin, shell.state.settings.listen_seconds),
    ):
        if widget is not None:
            widget.setChecked(value) if isinstance(value, bool) else widget.setValue(value)
    if getattr(shell, "research_mode_combo", None) is not None:
        index = shell.research_mode_combo.findData(shell.state.research.mode)
        if index >= 0:
            shell.research_mode_combo.setCurrentIndex(index)


def set_category_selection(shell: Any, selected: bool) -> None:
    """Select or clear every category in the category list widget."""
    if shell.category_list is None:
        return
    set_all_items_selected(shell.category_list, selected)
    shell._update_state_from_widgets()
    shell._refresh_ui()


def clear_filter_selections(shell: Any, filter_keys: tuple[str, ...]) -> None:
    """Clear all visible multi-select filters and sync launcher state."""
    clear_multi_select_widgets(shell.filter_widgets.values())
    min_price_widget = shell.filter_field_widgets.get("min_price")
    max_price_widget = shell.filter_field_widgets.get("max_price")
    in_stock_widget = shell.filter_field_widgets.get("in_stock")
    strict_missing_widget = shell.filter_field_widgets.get("strict_missing")
    if min_price_widget is not None:
        min_price_widget.setValue(0.0)
    if max_price_widget is not None:
        max_price_widget.setValue(0.0)
    if in_stock_widget is not None:
        in_stock_widget.setCurrentIndex(0)
    if strict_missing_widget is not None:
        strict_missing_widget.setChecked(False)
    cleared_filters = {filter_name: [] for filter_name in filter_keys}
    cleared_filters.update(
        {
            "min_price": None,
            "max_price": None,
            "in_stock": None,
            "strict_missing": False,
        }
    )
    shell.controller.set_filters(cleared_filters)
    shell._refresh_ui()
