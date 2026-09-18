"""Session/version helpers for StoreProfile repository."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from utils.store_profile_payloads import json_row
from utils.store_profile_presets import apply_latest_presets


def list_profile_versions(
    connection: sqlite3.Connection,
    *,
    workspace_id: str,
    profile_id: str,
) -> list[dict[str, Any]]:
    """Return saved sessions for one workspace-scoped StoreProfile."""
    rows = connection.execute(
        """
        SELECT version_id, workspace_id, profile_id, session_kind, source_task,
               payload_json, created_at
        FROM profile_versions
        WHERE workspace_id = ? AND profile_id = ?
        ORDER BY created_at DESC, version_id DESC
        """,
        (workspace_id, profile_id),
    ).fetchall()
    return [_version_row(row) for row in rows]


def get_profile_version(
    connection: sqlite3.Connection,
    *,
    workspace_id: str,
    profile_id: str,
    version_id: str,
) -> dict[str, Any] | None:
    """Return one saved session payload, scoped by workspace and profile."""
    row = connection.execute(
        """
        SELECT payload_json
        FROM profile_versions
        WHERE workspace_id = ? AND profile_id = ? AND version_id = ?
        LIMIT 1
        """,
        (workspace_id, profile_id, version_id),
    ).fetchone()
    payload = json_row(row, "payload_json")
    if payload is None:
        return None
    return apply_latest_presets(connection, payload, profile_id=profile_id, workspace_id=workspace_id)


def _version_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = json_row(row, "payload_json") or {}
    catalog = payload.get("catalog") if isinstance(payload.get("catalog"), dict) else {}
    products = payload.get("products") if isinstance(payload.get("products"), dict) else {}
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    artifacts = result.get("artifact_paths") if isinstance(result.get("artifact_paths"), dict) else {}
    artifact_path = _primary_artifact_path(artifacts if isinstance(artifacts, dict) else {}, products)
    return {
        "version_id": str(row["version_id"]),
        "workspace_id": str(row["workspace_id"]),
        "profile_id": str(row["profile_id"]),
        "session_kind": str(row["session_kind"]),
        "source_task": str(row["source_task"]),
        "created_at": str(row["created_at"]),
        "catalog_count": len(catalog.get("full_links") or []),
        "products_count": _products_count(products),
        "artifact_name": Path(artifact_path).name if artifact_path else "",
        "artifact_available": bool(artifact_path and Path(artifact_path).exists()),
    }


def _products_count(products: dict[str, Any]) -> int:
    explicit = products.get("products_count")
    if explicit:
        return int(explicit)
    items = products.get("items")
    return len(items) if isinstance(items, list) else 0


def _primary_artifact_path(artifacts: dict[str, Any], products: dict[str, Any]) -> str:
    return str(
        artifacts.get("excel_path")
        or products.get("excel_path")
        or artifacts.get("json_path")
        or products.get("json_path")
        or ""
    )
