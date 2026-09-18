"""Append-only desktop launcher task event history."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.launcher_state import LauncherAppState


def append_launcher_task_event(settings_path: Path, state: LauncherAppState) -> Path:
    """Append one compact task-state event next to launcher settings."""
    event = _task_event_payload(state)
    target = settings_path.parent / "launcher_task_events.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return target


def _task_event_payload(state: LauncherAppState) -> dict[str, Any]:
    return {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "task_name": state.task.task_name,
        "status": state.task.status,
        "task_kind": state.task.task_kind,
        "phase": state.task.phase,
        "message": state.task.message,
        "last_error": state.task.last_error,
        "selected_categories": list(state.selection.categories),
        "selected_catalog_nodes": list(state.selection.selected_catalog_nodes),
        "products_count": int(state.products.products_count or len(state.products.items)),
        "source_categories": list(state.products.source_categories),
        "json_path": state.products.json_path or state.result.json_path,
    }
