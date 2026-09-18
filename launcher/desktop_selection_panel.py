"""Selection and catalog panels for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_catalog_search import apply_catalog_tree_search
from launcher.desktop_catalog_tree_widget import collect_checked_catalog_nodes, populate_catalog_tree_widget
from launcher.desktop_state_readers import full_catalog_links, full_catalog_tree
from launcher.desktop_ui_text import SHOP_LABELS, STORE_URL_PLACEHOLDER


def build_store_selection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the store URL selection panel for general research."""
    box = qtwidgets.QGroupBox("Выбор магазина")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(qtwidgets.QLabel("URL сайта"), 0, 0)
    shell.site_url_input = qtwidgets.QLineEdit("")
    shell.site_url_input.setPlaceholderText(STORE_URL_PLACEHOLDER)
    shell.site_url_input.setMinimumWidth(0)
    shell.site_url_input.setSizePolicy(
        qtwidgets.QSizePolicy.Policy.Ignored,
        qtwidgets.QSizePolicy.Policy.Fixed,
    )
    layout.addWidget(shell.site_url_input, 0, 1, 1, 3)
    shell.profile_hint_label = qtwidgets.QLabel("Магазин определится после исследования сайта и сохранения профиля.")
    shell.profile_hint_label.setWordWrap(True)
    layout.addWidget(shell.profile_hint_label, 1, 1, 1, 3)
    shell.shop_combo = qtwidgets.QComboBox()
    shell.shop_combo.addItem("Профиль ещё не выбран", "")
    for value, label in SHOP_LABELS.items():
        shell.shop_combo.addItem(label, value)
    shell.shop_combo.currentTextChanged.connect(shell._on_shop_changed)
    shell.shop_combo.hide()
    return box


def build_catalog_selection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the discovered category list and full catalog tree panel."""
    box = qtwidgets.QGroupBox("Каталог")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    shell.catalog_context_label = qtwidgets.QLabel("")
    shell.catalog_context_label.setWordWrap(True)
    layout.addWidget(shell.catalog_context_label, 0, 0, 1, 4)
    layout.addWidget(qtwidgets.QLabel("Выбрано для сбора"), 1, 0)
    shell.category_list = qtwidgets.QListWidget()
    shell.category_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    shell.category_list.setMinimumHeight(48)
    shell.category_list.setMaximumHeight(70)
    layout.addWidget(shell.category_list, 1, 1, 1, 3)
    layout.addWidget(qtwidgets.QLabel("Разделы каталога"), 2, 0)
    shell.catalog_search_input = qtwidgets.QLineEdit()
    shell.catalog_search_input.setObjectName("launcherCatalogSearchInput")
    shell.catalog_search_input.setPlaceholderText("Поиск по первым буквам")
    shell.catalog_search_input.textChanged.connect(lambda text: _apply_catalog_search(shell, text))
    layout.addWidget(shell.catalog_search_input, 2, 1, 1, 3)
    shell.catalog_tree = qtwidgets.QTreeWidget()
    shell.catalog_tree.setMinimumHeight(280)
    shell.catalog_tree.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.NoSelection)
    shell.catalog_tree.itemChanged.connect(shell._on_catalog_tree_changed)
    layout.addWidget(shell.catalog_tree, 3, 1, 1, 3)
    button_grid = qtwidgets.QGridLayout()
    button_grid.setContentsMargins(0, 0, 0, 0)
    button_grid.setHorizontalSpacing(8)
    for index, (label, handler) in enumerate(
        (
            ("Выбрать все разделы для сбора", shell._on_select_all_categories),
            ("Снять выбор разделов", shell._on_clear_categories),
        )
    ):
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.category_action_buttons.append(button)
        button_grid.addWidget(button, 0, index)
    layout.addLayout(button_grid, 4, 1, 1, 3)
    return box


def refresh_category_list(shell: Any) -> None:
    """Refresh the compatibility category list from the current research result."""
    assert shell.category_list is not None
    shell.category_list.clear()
    for category_name in shell.state.selection.categories:
        item = shell._qtwidgets.QListWidgetItem(category_name)
        shell.category_list.addItem(item)
        item.setSelected(True)
    _refresh_catalog_context(shell)


def refresh_catalog_tree(shell: Any) -> None:
    """Refresh the full discovered catalog tree widget."""
    if shell.catalog_tree is None or shell._qtwidgets is None or shell._qt is None:
        return
    nodes = full_catalog_tree(shell.state)
    populate_catalog_tree_widget(shell.catalog_tree, shell._qtwidgets, shell._qt, nodes, shell.state.selection.categories)
    apply_catalog_tree_search(shell.catalog_tree, _catalog_search_text(shell))
    _refresh_catalog_context(shell)


def sync_catalog_selection_from_widgets(shell: Any) -> None:
    """Push selected catalog widgets into launcher state."""
    assert shell.category_list is not None
    if shell.catalog_tree is not None and shell.catalog_tree.topLevelItemCount() > 0:
        nodes = collect_checked_catalog_nodes(shell.catalog_tree, shell._qt)
        shell.controller.set_selection(
            categories=[str(item.get("name") or "") for item in nodes if str(item.get("name") or "").strip()],
            selected_catalog_nodes=nodes,
        )
        refresh_category_list(shell)
        _refresh_catalog_context(shell)
        return
    shell.controller.set_selection(categories=[item.text() for item in shell.category_list.selectedItems()])
    _refresh_catalog_context(shell)


def _refresh_catalog_context(shell: Any) -> None:
    label = getattr(shell, "catalog_context_label", None)
    if label is None:
        return
    tree = full_catalog_tree(shell.state)
    links = full_catalog_links(shell.state)
    total = len(links) if links else _catalog_tree_count(tree)
    selected = shell.state.selection.categories
    mode = "плоский пул разделов" if _is_flat_catalog(tree) else "дерево разделов"
    preview = ", ".join(selected[:3])
    label.setText(f"Каталог: найдено {total} | выбрано {len(selected)}{(': ' + preview) if preview else ''} | структура: {mode}")


def _catalog_search_text(shell: Any) -> str:
    search_input = getattr(shell, "catalog_search_input", None)
    return search_input.text() if search_input is not None else ""


def _apply_catalog_search(shell: Any, text: str) -> None:
    if shell.catalog_tree is not None:
        apply_catalog_tree_search(shell.catalog_tree, text)


def _catalog_tree_count(tree: Any) -> int:
    if not isinstance(tree, list):
        return 0
    total = 0
    for node in tree:
        if isinstance(node, dict):
            total += 1 + _catalog_tree_count(node.get("children"))
    return total


def _is_flat_catalog(tree: Any) -> bool:
    if not isinstance(tree, list) or not tree:
        return True
    roots = [node for node in tree if isinstance(node, dict)]
    if len(roots) != 1:
        return all(not node.get("children") for node in roots)
    children = roots[0].get("children")
    child_nodes = children if isinstance(children, list) else []
    return bool(child_nodes) and all(
        not isinstance(child.get("children"), list) or not child.get("children")
        for child in child_nodes
        if isinstance(child, dict)
    )
