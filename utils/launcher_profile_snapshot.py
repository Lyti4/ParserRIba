"""JSON snapshots for Launcher V2 per-site workspace profiles."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.launcher_state import LauncherAppState


def build_launcher_profile_snapshot(
    state: LauncherAppState,
    *,
    task_name: str = "",
    snapshot_id: str = "",
) -> dict[str, Any] | None:
    """Build one non-secret per-site Launcher V2 workspace snapshot."""
    site_url = str(state.profile.site_url or "").strip()
    profile_id = str(state.profile.profile_id or "").strip()
    if not site_url and not profile_id:
        return None
    return {
        "snapshot_id": snapshot_id or _timestamp_id(),
        "task_name": str(task_name or state.task.task_name or ""),
        "profile": state.profile.model_dump(mode="json"),
        "catalog": {
            "catalog_type": state.catalog.catalog_type,
            "full_tree": list(state.catalog.full_tree),
            "full_links": list(state.catalog.full_links),
            "selected_nodes": list(state.selection.selected_catalog_nodes or state.catalog.selected_nodes),
            "selected_node_urls": _selected_node_urls(state),
        },
        "products": state.products.model_dump(mode="json"),
        "dynamic_filters": state.dynamic_filters.model_dump(mode="json"),
        "selection": state.selection.model_dump(mode="json"),
        "result": {
            "summary": dict(state.result.summary),
            "artifact_paths": dict(state.result.artifact_paths),
            "products_count": state.result.products_count,
            "source_profile_id": state.result.source_profile_id,
            "filter_snapshot": dict(state.result.filter_snapshot),
        },
    }


def write_launcher_profile_snapshot(
    state: LauncherAppState,
    *,
    base_dir: Path | str,
    task_name: str = "",
    snapshot_id: str = "",
) -> Path | None:
    """Persist one Launcher V2 workspace snapshot and refresh latest.json."""
    payload = build_launcher_profile_snapshot(state, task_name=task_name, snapshot_id=snapshot_id)
    if payload is None:
        return None
    profile = payload["profile"]
    shop = _slug(str(profile.get("shop") or state.selection.shop or "unknown"))
    profile_key = _slug(str(profile.get("profile_id") or profile.get("domain") or profile.get("site_url") or "default"))
    target_dir = Path(base_dir) / shop / profile_key
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{payload['snapshot_id']}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    (target_dir / "latest.json").write_text(text, encoding="utf-8")
    return path


def _selected_node_urls(state: LauncherAppState) -> list[str]:
    urls = list(state.catalog.selected_node_urls)
    if urls:
        return urls
    result: list[str] = []
    for item in state.selection.selected_catalog_nodes:
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            if url:
                result.append(url)
    return result


def _timestamp_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return normalized.strip("._-") or "unknown"
