"""Selection and catalog panels for the desktop launcher."""

from __future__ import annotations

from typing import Any

from application.source_profile_catalog import declared_source_profiles
from launcher.desktop_catalog_tree_widget import collect_checked_catalog_nodes, populate_catalog_tree_widget
from launcher.desktop_state_readers import full_catalog_links, full_catalog_tree
from launcher.desktop_ui_text import SHOP_LABELS


def build_store_selection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the store URL selection panel for general research."""
    box = qtwidgets.QGroupBox("Выбор магазина")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    layout.addWidget(qtwidgets.QLabel("URL сайта"), 0, 0)
    shell.site_url_input = qtwidgets.QLineEdit("")
    layout.addWidget(shell.site_url_input, 0, 1, 1, 3)
    layout.addWidget(qtwidgets.QLabel("Магазин"), 1, 0)
    shell.shop_combo = qtwidgets.QComboBox()
    shell.shop_combo.addItem("Выберите источник", "")
    for value, label in SHOP_LABELS.items():
        shell.shop_combo.addItem(label, value)
    shell.shop_combo.currentTextChanged.connect(shell._on_shop_changed)
    layout.addWidget(shell.shop_combo, 1, 1)
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
    shell.catalog_tree = qtwidgets.QTreeWidget()
    shell.catalog_tree.setMinimumHeight(280)
    shell.catalog_tree.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.NoSelection)
    shell.catalog_tree.itemChanged.connect(shell._on_catalog_tree_changed)
    layout.addWidget(shell.catalog_tree, 2, 1, 1, 3)
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
    layout.addLayout(button_grid, 3, 1, 1, 3)
    return box


def build_source_adapter_collection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build blank explicit SourceProfile and CatalogNode inputs for local-only collection."""
    box = qtwidgets.QGroupBox("Сбор из явного источника")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    note = qtwidgets.QLabel(
        "Выберите источник и разделы явно. Fixture работает локально; для JSON укажите canonical file:/// URI."
    )
    note.setWordWrap(True)
    layout.addWidget(note, 0, 0, 1, 2)
    layout.addWidget(qtwidgets.QLabel("Источник"), 1, 0)
    shell.source_profile_combo = qtwidgets.QComboBox()
    shell.source_profile_combo.addItem("Выберите источник", "")
    for profile in declared_source_profiles():
        shell.source_profile_combo.addItem(profile.display_name, profile.source_profile_id)
    layout.addWidget(shell.source_profile_combo, 1, 1)
    layout.addWidget(qtwidgets.QLabel("Локальный URI"), 2, 0)
    shell.source_locator_input = qtwidgets.QLineEdit("")
    layout.addWidget(shell.source_locator_input, 2, 1)
    layout.addWidget(qtwidgets.QLabel("ID разделов через запятую"), 3, 0)
    shell.source_catalog_node_ids_input = qtwidgets.QLineEdit("")
    layout.addWidget(shell.source_catalog_node_ids_input, 3, 1)
    button = qtwidgets.QPushButton("Собрать выбранный источник")
    button.clicked.connect(shell._on_run_source_adapter_collection)
    layout.addWidget(button, 4, 0, 1, 2)
    return box


def selected_source_adapter_catalog_node_ids(shell: Any) -> list[str]:
    """Return only explicit nonempty CatalogNode IDs in entered order, without inferred selection."""
    input_widget = getattr(shell, "source_catalog_node_ids_input", None)
    value = input_widget.text() if input_widget is not None else ""
    return [node_id.strip() for node_id in str(value).replace("\n", ",").split(",") if node_id.strip()]


PYATEROCHKA_FIXTURE_NODE_OPTIONS = (
    ("pyaterochka-fish", "Рыба"),
    ("pyaterochka-wine", "Вино"),
)


def build_pyaterochka_fixture_collection_box(shell: Any, qtwidgets: Any) -> Any:
    """Build an explicit local-only fixture collection control, separate from live catalog selection."""
    box = qtwidgets.QGroupBox("Демо: Пятёрочка (fixture)")
    layout = qtwidgets.QGridLayout(box)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    note = qtwidgets.QLabel("Локальные детерминированные данные. Разделы live-каталога не используются.")
    note.setWordWrap(True)
    layout.addWidget(note, 0, 0, 1, 2)
    shell.pyaterochka_fixture_node_checkboxes = {}
    for row, (node_id, label) in enumerate(PYATEROCHKA_FIXTURE_NODE_OPTIONS, start=1):
        checkbox = qtwidgets.QCheckBox(label)
        checkbox.setChecked(False)
        shell.pyaterochka_fixture_node_checkboxes[node_id] = checkbox
        layout.addWidget(checkbox, row, 0, 1, 2)
    button = qtwidgets.QPushButton("Собрать выбранные демо-товары")
    button.clicked.connect(shell._on_run_pyaterochka_fixture)
    layout.addWidget(button, len(PYATEROCHKA_FIXTURE_NODE_OPTIONS) + 1, 0, 1, 2)
    return box


def selected_pyaterochka_fixture_catalog_node_ids(shell: Any) -> list[str]:
    """Return only user-checked explicit fixture IDs in the declared display order."""
    checkboxes = getattr(shell, "pyaterochka_fixture_node_checkboxes", {})
    return [
        node_id
        for node_id, _label in PYATEROCHKA_FIXTURE_NODE_OPTIONS
        if node_id in checkboxes and checkboxes[node_id].isChecked()
    ]


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
