"""Favorites tab for the desktop launcher."""

from __future__ import annotations

from typing import Any


def build_favorites_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the workspace favorites tab."""
    box = qtwidgets.QGroupBox("\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435")
    box.setObjectName("launcherFavoritesBox")
    layout = qtwidgets.QVBoxLayout(box)
    shell.favorites_summary_label = qtwidgets.QLabel("")
    shell.favorites_summary_label.setObjectName("launcherFavoritesSummaryLabel")
    shell.favorites_summary_label.setWordWrap(True)
    layout.addWidget(shell.favorites_summary_label)
    shell.favorites_list = qtwidgets.QListWidget()
    shell.favorites_list.setObjectName("launcherFavoritesList")
    shell.favorites_list.itemSelectionChanged.connect(lambda: _sync_selected_favorites(shell))
    layout.addWidget(shell.favorites_list, stretch=1)
    layout.addWidget(_build_favorites_actions(shell, qtwidgets))
    return box


def refresh_favorites_box(shell: Any) -> None:
    """Refresh favorites tab widgets from launcher state."""
    label = getattr(shell, "favorites_summary_label", None)
    items = _ordered_favorites(
        list(shell.state.favorites.items),
        str(shell.state.workspace_selection.selected_profile_id or shell.state.profile.profile_id or ""),
    )
    if label is not None:
        label.setText(_summary_text(items))
    list_widget = getattr(shell, "favorites_list", None)
    if list_widget is None:
        return
    current = set(shell.state.favorites.selected_favorite_ids)
    list_widget.blockSignals(True)
    list_widget.clear()
    for favorite in items:
        item = shell._qtwidgets.QListWidgetItem(_favorite_label(favorite))
        item.setData(shell._qt.ItemDataRole.UserRole, favorite.favorite_id)
        item.setSelected(favorite.favorite_id in current)
        list_widget.addItem(item)
    list_widget.blockSignals(False)


def _build_favorites_actions(shell: Any, qtwidgets: Any) -> Any:
    row = qtwidgets.QWidget()
    layout = qtwidgets.QGridLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    actions = (
        ("add_favorite_profile", "\u041c\u0430\u0433\u0430\u0437\u0438\u043d", lambda: _add_profile_favorite(shell)),
        ("add_favorite_catalog", "\u0420\u0430\u0437\u0434\u0435\u043b\u044b", lambda: _add_catalog_favorites(shell)),
        ("add_favorite_products", "\u0422\u043e\u0432\u0430\u0440\u044b", lambda: _add_product_favorites(shell)),
        ("refresh_selected_favorites", "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c", lambda: _refresh_selected_favorites(shell)),
        ("refresh_all_favorites", "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u0441\u0435", lambda: _refresh_all_favorites(shell)),
        ("remove_favorites", "\u0423\u0434\u0430\u043b\u0438\u0442\u044c", lambda: _remove_selected_favorites(shell)),
    )
    for index, (key, label, handler) in enumerate(actions):
        button = qtwidgets.QPushButton(label)
        button.setObjectName(f"launcherFavorites_{key}")
        button.clicked.connect(handler)
        shell.action_buttons[key] = button
        layout.addWidget(button, 0, index)
        layout.setColumnStretch(index, 1)
    return row


def _sync_selected_favorites(shell: Any) -> None:
    list_widget = getattr(shell, "favorites_list", None)
    if list_widget is None:
        return
    shell.state.favorites.selected_favorite_ids = [
        str(item.data(shell._qt.ItemDataRole.UserRole) or "") for item in list_widget.selectedItems()
    ]
    shell._refresh_action_buttons()


def _add_profile_favorite(shell: Any) -> None:
    shell.controller.add_current_profile_favorite()
    shell._refresh_ui()


def _add_catalog_favorites(shell: Any) -> None:
    if getattr(shell, "catalog_tree", None) is not None:
        from launcher.desktop_selection_panel import sync_catalog_selection_from_widgets

        sync_catalog_selection_from_widgets(shell)
    shell.controller.add_selected_catalog_favorites()
    shell._refresh_ui()


def _add_product_favorites(shell: Any) -> None:
    shell._sync_selected_products_from_table()
    shell.controller.add_selected_product_favorites()
    shell._refresh_ui()


def _remove_selected_favorites(shell: Any) -> None:
    shell.controller.remove_workspace_favorites(shell.state.favorites.selected_favorite_ids)
    shell._refresh_ui()


def _refresh_selected_favorites(shell: Any) -> None:
    shell.controller.refresh_selected_workspace_favorites()
    shell._refresh_ui()


def _refresh_all_favorites(shell: Any) -> None:
    shell.controller.refresh_all_workspace_favorites()
    shell._refresh_ui()


def _summary_text(items: list[Any]) -> str:
    if not items:
        return "\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u044b\u0445 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442."
    return f"\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435: {len(items)}."


def _ordered_favorites(items: list[Any], selected_profile_id: str) -> list[Any]:
    active_profile_id = str(selected_profile_id or "").strip()
    return sorted(
        items,
        key=lambda favorite: (
            0 if active_profile_id and favorite.profile_id == active_profile_id else 1,
            str(favorite.store_label or ""),
            str(favorite.favorite_type or ""),
            str(favorite.display_label or ""),
        ),
    )


def _favorite_label(favorite: Any) -> str:
    type_label = {
        "store": "\u041c\u0430\u0433\u0430\u0437\u0438\u043d",
        "catalog_node": "\u0420\u0430\u0437\u0434\u0435\u043b",
        "product": "\u0422\u043e\u0432\u0430\u0440",
    }.get(favorite.favorite_type, favorite.favorite_type)
    status = {
        "never": "\u0435\u0449\u0451 \u043d\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u044f\u043b\u043e\u0441\u044c",
        "success": "\u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u043e",
        "skipped": "\u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043e",
        "failed": "\u043e\u0448\u0438\u0431\u043a\u0430",
        "partial": "\u0447\u0430\u0441\u0442\u0438\u0447\u043d\u043e",
    }.get(favorite.last_refresh_status, favorite.last_refresh_status)
    store = f" | {favorite.store_label}" if favorite.store_label else ""
    return f"{type_label}: {favorite.display_label}{store} | {status}"
