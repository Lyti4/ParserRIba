"""Selection and catalog panels for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_catalog_tree_widget import collect_checked_catalog_nodes, populate_catalog_tree_widget
from launcher.desktop_ui_text import INTENT_LABELS, SHOP_LABELS


def build_store_selection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the store URL and intent selection panel."""
    box = qtwidgets.QGroupBox("Выбор магазина")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(qtwidgets.QLabel("URL сайта"), 0, 0)
    shell.site_url_input = qtwidgets.QLineEdit("https://5ka.ru")
    layout.addWidget(shell.site_url_input, 0, 1, 1, 3)
    layout.addWidget(qtwidgets.QLabel("Магазин"), 1, 0)
    shell.shop_combo = qtwidgets.QComboBox()
    for value, label in SHOP_LABELS.items():
        shell.shop_combo.addItem(label, value)
    shell.shop_combo.currentTextChanged.connect(shell._on_shop_changed)
    layout.addWidget(shell.shop_combo, 1, 1)
    layout.addWidget(qtwidgets.QLabel("Раздел"), 1, 2)
    shell.intent_combo = qtwidgets.QComboBox()
    for value, label in INTENT_LABELS.items():
        shell.intent_combo.addItem(label, value)
    shell.intent_combo.currentTextChanged.connect(shell._on_intent_changed)
    layout.addWidget(shell.intent_combo, 1, 3)
    return box


def build_catalog_selection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the discovered category list and full catalog tree panel."""
    box = qtwidgets.QGroupBox("Каталог")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(qtwidgets.QLabel("Категории"), 0, 0)
    shell.category_list = qtwidgets.QListWidget()
    shell.category_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
    shell.category_list.setMinimumHeight(70)
    shell.category_list.setMaximumHeight(90)
    layout.addWidget(shell.category_list, 0, 1, 1, 3)
    layout.addWidget(qtwidgets.QLabel("Дерево каталога"), 1, 0)
    shell.catalog_tree = qtwidgets.QTreeWidget()
    shell.catalog_tree.setMinimumHeight(220)
    shell.catalog_tree.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.NoSelection)
    shell.catalog_tree.itemChanged.connect(shell._on_catalog_tree_changed)
    layout.addWidget(shell.catalog_tree, 1, 1, 1, 3)
    button_grid = qtwidgets.QGridLayout()
    button_grid.setContentsMargins(0, 0, 0, 0)
    button_grid.setHorizontalSpacing(8)
    for index, (label, handler) in enumerate(
        (
            ("Выбрать всё", shell._on_select_all_categories),
            ("Снять выбор", shell._on_clear_categories),
        )
    ):
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.category_action_buttons.append(button)
        button_grid.addWidget(button, 0, index)
    layout.addLayout(button_grid, 2, 1, 1, 3)
    return box


def refresh_category_list(shell: Any) -> None:
    """Refresh the compatibility category list from the current research result."""
    assert shell.category_list is not None
    shell.category_list.clear()
    selected = set(shell.state.selection.categories)
    for category_name in shell.controller.list_available_categories():
        item = shell._qtwidgets.QListWidgetItem(category_name)
        shell.category_list.addItem(item)
        item.setSelected(category_name in selected)


def refresh_catalog_tree(shell: Any) -> None:
    """Refresh the full discovered catalog tree widget."""
    if shell.catalog_tree is None or shell._qtwidgets is None or shell._qt is None:
        return
    tree = shell.state.result.launcher_view.get("full_catalog_tree")
    nodes = tree if isinstance(tree, list) else []
    populate_catalog_tree_widget(shell.catalog_tree, shell._qtwidgets, shell._qt, nodes, shell.state.selection.categories)


def sync_catalog_selection_from_widgets(shell: Any) -> None:
    """Push selected catalog widgets into launcher state."""
    assert shell.category_list is not None
    if shell.catalog_tree is not None and shell.catalog_tree.topLevelItemCount() > 0:
        nodes = collect_checked_catalog_nodes(shell.catalog_tree, shell._qt)
        shell.controller.set_selection(
            categories=[str(item.get("name") or "") for item in nodes if str(item.get("name") or "").strip()],
            selected_catalog_nodes=nodes,
        )
        return
    shell.controller.set_selection(categories=[item.text() for item in shell.category_list.selectedItems()])
