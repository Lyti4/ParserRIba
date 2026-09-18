"""Local settings persistence for the desktop launcher."""

from __future__ import annotations

import json
from pathlib import Path

from models.launcher_state import LauncherAppState, LauncherSettingsState
from utils.launcher_task_events import append_launcher_task_event


class LauncherSettingsStore:
    """Persist and restore local launcher settings."""

    def __init__(self, settings_path: Path | str) -> None:
        self.settings_path = Path(settings_path)

    def load(self) -> LauncherSettingsState:
        """Load settings from disk or return defaults."""
        payload = self._load_json()
        settings_payload = payload.get("settings")
        if isinstance(settings_payload, dict):
            return LauncherSettingsState(**settings_payload)
        return LauncherSettingsState()

    def save(self, settings: LauncherSettingsState) -> Path:
        """Persist settings to disk in UTF-8 JSON."""
        payload = self._load_json()
        payload["settings"] = settings.model_dump(mode="json")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.settings_path

    def load_app_state(self) -> LauncherAppState:
        """Load a fuller launcher state snapshot when available."""
        payload = self._load_json()
        if not payload:
            return LauncherAppState()
        state = LauncherAppState(**payload)
        _clear_transient_selection(state)
        return state

    def save_app_state(self, state: LauncherAppState) -> Path:
        """Persist the full launcher state snapshot."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        append_launcher_task_event(self.settings_path, state)
        return self.settings_path

    def _load_json(self) -> dict:
        if not self.settings_path.exists():
            return {}
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}


def _clear_transient_selection(state: LauncherAppState) -> None:
    """Avoid restoring stale active UI selections as fresh user choices."""
    selected_nodes = _restorable_catalog_nodes(state)
    state.selection.selected_catalog_nodes = selected_nodes
    state.selection.categories = [
        str(item.get("name") or "").strip()
        for item in selected_nodes
        if str(item.get("name") or "").strip()
    ]
    state.selection.selected_product_ids = []
    state.catalog.selected_nodes = selected_nodes
    state.catalog.selected_node_urls = [
        str(item.get("url") or "").strip()
        for item in selected_nodes
        if str(item.get("url") or "").strip()
    ]
    state.products.selected_product_ids = []
    _clear_stale_product_workspace(state)
    if state.task.status == "running":
        state.task.status = "idle"
        state.task.message = ""
        state.task.last_error = ""


def _restorable_catalog_nodes(state: LauncherAppState) -> list[dict]:
    """Return persisted catalog selections that still belong to the current tree."""
    if not state.settings.remember_last_selection:
        return []
    known_urls = _catalog_urls(state.catalog.full_tree) | {
        str(item.get("url") or "").strip()
        for item in state.catalog.full_links
        if isinstance(item, dict)
    }
    if not known_urls:
        return []
    candidates = list(state.selection.selected_catalog_nodes or state.catalog.selected_nodes)
    result: list[dict] = []
    for node in candidates:
        if not isinstance(node, dict):
            continue
        url = str(node.get("url") or "").strip()
        name = str(node.get("name") or "").strip()
        if url and url in known_urls:
            result.append({"name": name, "url": url})
    return result


def _catalog_urls(nodes: list[dict]) -> set[str]:
    """Collect catalog URLs from one saved tree."""
    urls: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        url = str(node.get("url") or "").strip()
        if url:
            urls.add(url)
        children = node.get("children")
        if isinstance(children, list):
            urls.update(_catalog_urls(children))
    return urls


def _clear_stale_product_workspace(state: LauncherAppState) -> None:
    """Drop old products when no active export owns the product workspace."""
    if not state.products.items:
        return
    if state.result.json_path or state.products.json_path or state.products.products_count:
        return
    state.products.items = []
    state.products.products_count = 0
    state.products.json_path = ""
    state.products.excel_path = ""
    state.products.source_categories = []
    state.products.discovered_fields = {}
    state.dynamic_filters.available_filters = {}
    state.dynamic_filters.applied_values = {}
    state.dynamic_filters.counts = {}
    state.dynamic_filters.ranges = {}
    state.dynamic_filters.missing_fields = []
    state.filters = state.filters.__class__()
    state.report.available_columns = []
    state.report.selected_columns = []
    state.report.column_titles = {}
    state.report.columns_touched = False
    state.result.products_count = 0
    state.result.filter_snapshot = {}
