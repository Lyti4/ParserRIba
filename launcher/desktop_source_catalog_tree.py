"""Source-neutral CatalogNode tree rendering for explicit desktop collection."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def populate_source_catalog_tree_widget(
    tree: Any,
    qtwidgets: Any,
    qt: Any,
    nodes: Sequence[Mapping[str, Any]],
    selected_node_ids: Sequence[str],
) -> None:
    """Render validated parent-linked CatalogNodes while keeping IDs in item data only."""
    selected = set(selected_node_ids)
    role = _user_role(qt)
    checkable = qt.ItemFlag.ItemIsUserCheckable
    checked = qt.CheckState.Checked
    unchecked = qt.CheckState.Unchecked
    by_id: dict[str, Mapping[str, Any]] = {}
    children_by_parent: dict[str | None, list[str]] = {}
    for node in nodes:
        node_id = _required_mapping_text(node, "catalog_node_id")
        _required_mapping_text(node, "display_name")
        if node_id in by_id:
            raise ValueError("SOURCE_CATALOG_TREE_INVALID: CatalogNode IDs must be unique.")
        parent_raw = node.get("parent_catalog_node_id")
        parent_id = None if parent_raw is None else str(parent_raw).strip()
        if parent_raw is not None and not parent_id:
            raise ValueError("SOURCE_CATALOG_TREE_INVALID: Parent IDs must be non-empty.")
        by_id[node_id] = node
        children_by_parent.setdefault(parent_id, []).append(node_id)
    for parent_id in children_by_parent:
        if parent_id is not None and parent_id not in by_id:
            raise ValueError("SOURCE_CATALOG_TREE_INVALID: Parent CatalogNode is unavailable.")

    tree.blockSignals(True)
    try:
        tree.clear()
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Раздел каталога", "Вложенность"])
        rendered: set[str] = set()

        def build_item(node_id: str, depth: int) -> Any:
            if node_id in rendered:
                raise ValueError("SOURCE_CATALOG_TREE_INVALID: Parent links must be acyclic.")
            rendered.add(node_id)
            node = by_id[node_id]
            item = qtwidgets.QTreeWidgetItem(
                [_required_mapping_text(node, "display_name"), "Корень" if depth == 0 else f"Уровень {depth}"]
            )
            item.setFlags(item.flags() | checkable)
            item.setCheckState(0, checked if node_id in selected else unchecked)
            item.setData(0, role, node_id)
            for child_id in children_by_parent.get(node_id, []):
                item.addChild(build_item(child_id, depth + 1))
            return item

        for root_id in children_by_parent.get(None, []):
            tree.addTopLevelItem(build_item(root_id, 0))
        if len(rendered) != len(by_id):
            raise ValueError("SOURCE_CATALOG_TREE_INVALID: Every CatalogNode must reach a root.")
        tree.expandToDepth(1)
        header = tree.header()
        header.setSectionResizeMode(0, qtwidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, qtwidgets.QHeaderView.ResizeMode.ResizeToContents)
    finally:
        tree.blockSignals(False)


def collect_checked_source_catalog_node_ids(tree: Any, qt: Any) -> list[str]:
    """Return checked CatalogNode IDs in visible tree order."""
    role = _user_role(qt)
    checked = qt.CheckState.Checked
    selected: list[str] = []

    def visit(item: Any) -> None:
        if item.checkState(0) == checked:
            node_id = str(item.data(0, role) or "").strip()
            if node_id and node_id not in selected:
                selected.append(node_id)
        for index in range(item.childCount()):
            visit(item.child(index))

    for index in range(tree.topLevelItemCount()):
        visit(tree.topLevelItem(index))
    return selected


def set_source_catalog_tree_checked(tree: Any, qt: Any, checked_value: bool) -> None:
    """Set all visible source CatalogNodes checked or unchecked."""
    state = qt.CheckState.Checked if checked_value else qt.CheckState.Unchecked

    def visit(item: Any) -> None:
        item.setCheckState(0, state)
        for index in range(item.childCount()):
            visit(item.child(index))

    tree.blockSignals(True)
    try:
        for index in range(tree.topLevelItemCount()):
            visit(tree.topLevelItem(index))
    finally:
        tree.blockSignals(False)


def _required_mapping_text(node: Mapping[str, Any], key: str) -> str:
    value = node.get(key)
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise ValueError(f"SOURCE_CATALOG_TREE_INVALID: {key} must be non-empty text.")
    return text


def _user_role(qt: Any) -> Any:
    item_data_role = getattr(qt, "ItemDataRole", None)
    if item_data_role is not None:
        return item_data_role.UserRole
    return 32
