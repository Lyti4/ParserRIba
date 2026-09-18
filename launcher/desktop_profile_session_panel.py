"""Profile/session summary panel for the product workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from launcher.desktop_profile_session_actions import (
    open_latest_profile_session,
    save_profile_session,
    select_workspace_profile,
)
from launcher.desktop_state_readers import filtered_product_items, full_catalog_links, product_items
from launcher.desktop_store_identity import active_store_display_name
from models.launcher_state import LauncherAppState


def build_profile_session_box(shell: Any, qtwidgets: Any) -> Any:
    """Build a compact live summary of the active store profile/session."""
    box = qtwidgets.QGroupBox("Магазин и сохранения")
    box.setObjectName("launcherProfileSessionBox")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(6, 6, 6, 6)
    shell.profile_session_label = qtwidgets.QLabel("")
    shell.profile_session_label.setObjectName("launcherProfileSessionLabel")
    shell.profile_session_label.setWordWrap(True)
    layout.addWidget(shell.profile_session_label)
    shell.profile_selector_combo = qtwidgets.QComboBox()
    shell.profile_selector_combo.setObjectName("launcherWorkspaceProfileCombo")
    shell.profile_selector_combo.currentIndexChanged.connect(lambda _index: select_workspace_profile(shell))
    layout.addWidget(shell.profile_selector_combo)
    shell.profile_session_combo = qtwidgets.QComboBox()
    shell.profile_session_combo.setObjectName("launcherProfileSessionCombo")
    layout.addWidget(shell.profile_session_combo)
    shell.profile_session_versions_label = qtwidgets.QLabel("")
    shell.profile_session_versions_label.setObjectName("launcherProfileSessionVersionsLabel")
    shell.profile_session_versions_label.setWordWrap(True)
    layout.addWidget(shell.profile_session_versions_label)
    open_button = qtwidgets.QPushButton("Открыть сохранение")
    open_button.setObjectName("launcherLoadProfileSessionButton")
    open_button.clicked.connect(lambda: open_latest_profile_session(shell))
    shell.action_buttons["load_profile_session"] = open_button
    layout.addWidget(open_button)
    save_button = qtwidgets.QPushButton("Сохранить текущее состояние")
    save_button.setObjectName("launcherSaveProfileSessionButton")
    save_button.clicked.connect(lambda: save_profile_session(shell))
    shell.action_buttons["save_profile_session"] = save_button
    layout.addWidget(save_button)
    return box


def refresh_profile_session_box(shell: Any) -> None:
    """Refresh the visible profile/session summary from launcher state."""
    label = getattr(shell, "profile_session_label", None)
    text = build_profile_session_text(shell.state)
    if label is not None:
        label.setText(text)
    _refresh_profile_selector(shell)
    _refresh_session_versions(shell)
    inspector_task_label = getattr(shell, "inspector_task_label", None)
    if inspector_task_label is not None:
        from launcher.desktop_inspector_panel import build_task_summary_text

        inspector_task_label.setText(build_task_summary_text(shell.state))
    inspector_task_group = getattr(shell, "inspector_task_group", None)
    if inspector_task_group is not None:
        inspector_task_group.setVisible(shell.state.task.status == "failed")


def build_profile_session_text(state: LauncherAppState) -> str:
    """Return concise Russian text for the active profile/session panel."""
    profile_name = active_store_display_name(state) or "магазин не выбран"
    catalog_count = len(full_catalog_links(state))
    products_count = len(product_items(state))
    filtered_count = len(filtered_product_items(state))
    selected_count = len(state.selection.selected_product_ids)
    filters_count = _active_filter_count(state)
    artifact = _latest_artifact_name(state)
    report_scope = (
        f"выбранные товары: {selected_count}"
        if selected_count
        else f"текущая таблица: {filtered_count}"
    )
    filters_text = str(filters_count) if filters_count else "нет"
    lines = [
        f"Магазин: {profile_name}",
        f"Каталог: {catalog_count} разделов",
        f"Товары: {products_count}; показано: {filtered_count}",
        f"Фильтры: {filters_text}",
        f"Отчёт: {report_scope}",
    ]
    if artifact:
        lines.append(f"Последний файл: {artifact}")
    return "\n".join(lines)


def _refresh_session_versions(shell: Any) -> None:
    combo = getattr(shell, "profile_session_combo", None)
    label = getattr(shell, "profile_session_versions_label", None)
    sessions = _profile_sessions(shell)
    if combo is not None:
        combo.blockSignals(True)
        current = str(combo.currentData() or "")
        combo.clear()
        for session in sessions:
            combo.addItem(_session_combo_label(session), session.get("version_id", ""))
        if current:
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)
    if label is not None:
        label.setText(_session_list_text(sessions))


def _refresh_profile_selector(shell: Any) -> None:
    combo = getattr(shell, "profile_selector_combo", None)
    controller = getattr(shell, "controller", None)
    if combo is None or controller is None:
        return
    profiles = controller.list_workspace_profiles()
    selected_profile_id = _selected_profile_id(shell)
    combo.blockSignals(True)
    combo.clear()
    if not profiles:
        combo.addItem("\u041f\u0440\u043e\u0444\u0438\u043b\u0435\u0439 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442", "")
    for profile in profiles:
        combo.addItem(_profile_combo_label(profile), str(profile.get("profile_id") or ""))
    if selected_profile_id:
        index = combo.findData(selected_profile_id)
        if index >= 0:
            combo.setCurrentIndex(index)
    combo.blockSignals(False)


def _profile_sessions(shell: Any) -> list[dict[str, Any]]:
    controller = getattr(shell, "controller", None)
    profile_id = _selected_profile_id(shell)
    if controller is None or not profile_id:
        return []
    sessions = controller.list_profile_sessions(profile_id=profile_id)
    return sessions[:5]


def _selected_profile_id(shell: Any) -> str:
    return (
        str(shell.state.workspace_selection.selected_profile_id or "").strip()
        or str(shell.state.profile.profile_id or "").strip()
    )


def _profile_combo_label(profile: dict[str, Any]) -> str:
    display_name = str(profile.get("display_name") or profile.get("shop") or "").strip()
    domain = str(profile.get("domain") or profile.get("site_url") or "").strip()
    profile_id = str(profile.get("profile_id") or "").strip()
    label = display_name or domain or profile_id
    if domain and domain != label:
        return f"{label} | {domain}"
    return label


def _session_combo_label(session: dict[str, Any]) -> str:
    created_at = str(session.get("created_at") or "")
    products_count = int(session.get("products_count") or 0)
    return f"{_display_datetime(created_at)} | {_product_count_text(products_count)}"


def _session_list_text(sessions: list[dict[str, Any]]) -> str:
    if not sessions:
        return "Сохранений для этого магазина пока нет."
    latest = sessions[0]
    products_count = int(latest.get("products_count") or 0)
    return f"Последнее сохранение: {_display_datetime(str(latest.get('created_at') or ''))}, {_product_count_text(products_count)}."


def _display_datetime(value: str) -> str:
    compact = value[:16].replace("T", " ").strip()
    if len(compact) >= 16 and compact[4] == "-" and compact[7] == "-":
        return f"{compact[8:10]}.{compact[5:7]}.{compact[:4]} {compact[11:16]}"
    return compact or "без даты"


def _product_count_text(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        word = "товар"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "товара"
    else:
        word = "товаров"
    return f"{count} {word}"


def _active_filter_count(state: LauncherAppState) -> int:
    filters = state.filters
    count = 0
    for field_name in (
        "suppliers",
        "brands",
        "categories",
        "subcategories",
        "alcohol_types",
        "sugar_classes",
        "colors",
    ):
        count += len(getattr(filters, field_name, []) or [])
    count += sum(len(values) for values in filters.found_filters.values())
    if filters.min_price is not None:
        count += 1
    if filters.max_price is not None:
        count += 1
    if filters.in_stock is not None:
        count += 1
    if filters.strict_missing:
        count += 1
    return count


def _latest_artifact_name(state: LauncherAppState) -> str:
    path_text = (
        state.result.excel_path
        or state.products.excel_path
        or state.result.json_path
        or state.products.json_path
    )
    if not path_text:
        return ""
    return Path(path_text).name
