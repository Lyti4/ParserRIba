"""Search helpers for the launcher catalog tree."""

from __future__ import annotations

from typing import Any


def apply_catalog_tree_search(tree: Any, query: str) -> None:
    """Hide catalog tree rows that do not match the current search query."""
    normalized_query = _normalize(query)
    for index in range(tree.topLevelItemCount()):
        _apply_item_search(tree.topLevelItem(index), normalized_query)


def _apply_item_search(item: Any, query: str) -> bool:
    child_matches = False
    for index in range(item.childCount()):
        child_matches = _apply_item_search(item.child(index), query) or child_matches
    own_match = not query or _matches(item.text(0), query) or _matches(item.text(1), query)
    visible = own_match or child_matches
    item.setHidden(not visible)
    if child_matches:
        item.setExpanded(True)
    return visible


def _matches(value: str, query: str) -> bool:
    normalized = _normalize(value)
    if not query:
        return True
    return normalized.startswith(query) or query in normalized or any(
        word.startswith(query) for word in normalized.split()
    )


def _normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().strip().split())
