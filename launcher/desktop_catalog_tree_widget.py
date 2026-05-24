"""Catalog tree widget helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any


CATALOG_NODE_ROLE = 32


def populate_catalog_tree_widget(
    tree: Any,
    qtwidgets: Any,
    qt: Any,
    nodes: list[Any],
    selected_names: list[str],
) -> None:
    """Populate the catalog tree with checkable discovered catalog nodes."""
    selected = {str(item).strip() for item in selected_names if str(item).strip()}
    tree.blockSignals(True)
    try:
        tree.clear()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Раздел каталога", "URL", "Дочерних"])
        for node in nodes:
            item = _build_tree_item(qtwidgets, qt, node, selected)
            if item is not None:
                tree.addTopLevelItem(item)
        tree.expandToDepth(1)
        header = tree.header()
        resize_mode = qtwidgets.QHeaderView.ResizeMode
        header.setSectionResizeMode(0, resize_mode.Stretch)
        header.setSectionResizeMode(1, resize_mode.ResizeToContents)
        header.setSectionResizeMode(2, resize_mode.ResizeToContents)
    finally:
        tree.blockSignals(False)


def collect_checked_catalog_nodes(tree: Any, qt: Any) -> list[dict[str, str]]:
    """Return checked catalog node records from the visible tree widget."""
    selected: list[dict[str, str]] = []
    for index in range(tree.topLevelItemCount()):
        _collect_checked_tree_item(tree.topLevelItem(index), qt, selected)
    return selected


def set_all_catalog_tree_items_checked(tree: Any, qt: Any, checked: bool) -> None:
    """Check or uncheck every selectable catalog tree item."""
    state = qt.CheckState.Checked if checked else qt.CheckState.Unchecked
    tree.blockSignals(True)
    try:
        for index in range(tree.topLevelItemCount()):
            _set_item_checked(tree.topLevelItem(index), state)
    finally:
        tree.blockSignals(False)


def _build_tree_item(qtwidgets: Any, qt: Any, node: Any, selected: set[str]) -> Any | None:
    if not isinstance(node, dict):
        return None
    name = str(node.get("name") or "").strip()
    url = str(node.get("url") or "").strip()
    children = node.get("children")
    child_nodes = children if isinstance(children, list) else []
    if not name and not url and not child_nodes:
        return None
    item = qtwidgets.QTreeWidgetItem([name, url, str(len(child_nodes))])
    item.setFlags(item.flags() | qt.ItemFlag.ItemIsUserCheckable)
    item.setCheckState(0, qt.CheckState.Checked if name in selected else qt.CheckState.Unchecked)
    item.setData(0, CATALOG_NODE_ROLE, {"name": name, "url": url})
    for child in child_nodes:
        child_item = _build_tree_item(qtwidgets, qt, child, selected)
        if child_item is not None:
            item.addChild(child_item)
    return item


def _collect_checked_tree_item(item: Any, qt: Any, selected: list[dict[str, str]]) -> None:
    if item.checkState(0) == qt.CheckState.Checked:
        node = item.data(0, CATALOG_NODE_ROLE)
        if isinstance(node, dict):
            name = str(node.get("name") or "").strip()
            url = str(node.get("url") or "").strip()
            if (name or url) and not _is_synthetic_catalog_root(name, url, item.childCount()):
                selected.append({"name": name, "url": url})
    for index in range(item.childCount()):
        _collect_checked_tree_item(item.child(index), qt, selected)


def _set_item_checked(item: Any, state: Any) -> None:
    item.setCheckState(0, state)
    for index in range(item.childCount()):
        _set_item_checked(item.child(index), state)


def _is_synthetic_catalog_root(name: str, url: str, child_count: int) -> bool:
    normalized_name = name.casefold()
    normalized_url = url.rstrip("/").casefold()
    return child_count > 0 and normalized_name == "каталог" and normalized_url.endswith("/catalog")
