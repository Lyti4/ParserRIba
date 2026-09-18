"""Launcher V4 top command strip."""

from __future__ import annotations

from typing import Any

from launcher.desktop_profile_session_panel import _latest_artifact_name
from launcher.desktop_state_readers import filtered_product_items
from launcher.desktop_store_identity import active_store_display_name
from launcher.desktop_theme import apply_launcher_theme
from launcher.desktop_ui_text import display_task_name
from models.launcher_state import LauncherAppState


def build_command_strip_text(state: LauncherAppState) -> str:
    """Build one compact current-workspace status line."""
    parts = [_store_summary_text(state), _status_summary_text(state)]
    progress = _progress_text(state)
    if progress:
        parts.append(progress)
    filtered_count = len(filtered_product_items(state))
    latest_artifact = _latest_artifact_name(state)
    products_count = state.products.products_count or len(state.products.items)
    selected_count = len(state.selection.selected_product_ids)
    parts.append(
        f"{_products_count_text(products_count)}, показано {filtered_count}, выбрано {selected_count}"
    )
    if latest_artifact:
        parts.append(f"Файл: {latest_artifact}")
    parts.append(f"Дальше: {_next_action_text(state)}")
    return " | ".join(parts)


def _store_summary_text(state: LauncherAppState) -> str:
    store = active_store_display_name(state) or "магазин не выбран"
    site_url = str(state.profile.site_url or "").strip()
    if site_url and site_url != store:
        return f"{store} | {site_url}"
    return store


def _status_summary_text(state: LauncherAppState) -> str:
    status = str(state.task.status or "").strip()
    if status == "running":
        task_name = str(state.task.task_name or "").strip()
        if task_name:
            label = display_task_name(task_name)
            return f"Идёт {_lower_first(label)}"
        return "Идёт работа"
    if status == "succeeded":
        return "Готово"
    if status == "failed":
        return "Нужна диагностика"
    if status == "blocked":
        return "Нужно внимание"
    return "Готов к исследованию"


def _progress_text(state: LauncherAppState) -> str:
    if not state.task.progress_total:
        return ""
    return f"{state.task.progress_current} из {state.task.progress_total}"


def _products_count_text(count: int) -> str:
    suffix = "товаров"
    if count % 10 == 1 and count % 100 != 11:
        suffix = "товар"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        suffix = "товара"
    return f"{count} {suffix}"


def _lower_first(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return "работа"
    return value[:1].lower() + value[1:]


def _next_action_text(state: LauncherAppState) -> str:
    if state.task.status == "running":
        return "\u0434\u043e\u0436\u0434\u0430\u0442\u044c\u0441\u044f \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u044f"
    if state.task.status == "failed":
        return "\u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0443"
    if filtered_product_items(state):
        return "\u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0442\u043e\u0432\u0430\u0440\u044b \u0438\u043b\u0438 \u0441\u043e\u0431\u0440\u0430\u0442\u044c Excel"
    if state.catalog.full_links or state.catalog.full_tree:
        return "\u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0440\u0430\u0437\u0434\u0435\u043b\u044b \u0438 \u0441\u043e\u0431\u0440\u0430\u0442\u044c \u0442\u043e\u0432\u0430\u0440\u044b"
    return "\u043d\u0430\u0447\u0430\u0442\u044c \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435"


def build_command_strip(shell: Any, qtwidgets: Any) -> Any:
    """Build the top V4 command strip."""
    host = qtwidgets.QFrame()
    host.setObjectName("launcherCommandStrip")
    layout = qtwidgets.QHBoxLayout(host)
    layout.setContentsMargins(10, 8, 10, 8)
    shell.command_strip_label = qtwidgets.QLabel(build_command_strip_text(shell.state))
    shell.command_strip_label.setWordWrap(True)
    layout.addWidget(shell.command_strip_label, stretch=1)
    shell.theme_combo = qtwidgets.QComboBox()
    shell.theme_combo.setObjectName("launcherThemeCombo")
    shell.theme_combo.addItem("\u0422\u0451\u043c\u043d\u0430\u044f", "dark")
    shell.theme_combo.addItem("\u0421\u0432\u0435\u0442\u043b\u0430\u044f", "light")
    shell.theme_combo.currentIndexChanged.connect(lambda _index: _apply_theme_choice(shell))
    layout.addWidget(shell.theme_combo, stretch=0)
    return host


def refresh_command_strip(shell: Any) -> None:
    """Refresh command strip from current launcher state."""
    label = getattr(shell, "command_strip_label", None)
    if label is not None:
        label.setText(build_command_strip_text(shell.state))


def _apply_theme_choice(shell: Any) -> None:
    combo = getattr(shell, "theme_combo", None)
    if combo is None:
        return
    mode = str(combo.currentData() or "dark")
    shell.state.settings.theme_mode = "light" if mode == "light" else "dark"
    apply_launcher_theme(getattr(shell, "window", None), shell.state.settings.theme_mode)
    shell.controller.save_state()
