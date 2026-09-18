"""Project workspace helpers for StoreProfile storage."""

from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from utils.store_profile_payloads import json_value, slug, utc_timestamp


def create_workspace_row(
    connection: sqlite3.Connection,
    name: str,
    *,
    description: str = "",
    workspace_id: str = "",
) -> dict[str, Any]:
    """Create or update one project workspace row."""
    clean_name = str(name or "").strip() or "Новое рабочее пространство"
    clean_id = str(workspace_id or "").strip() or _workspace_id_from_name(clean_name)
    now = utc_timestamp()
    connection.execute(
        """
        INSERT INTO project_workspaces (
            workspace_id, name, description, settings_json,
            is_default, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            updated_at=excluded.updated_at
        """,
        (clean_id, clean_name, str(description or ""), "{}", 0, now, now),
    )
    row = workspace_by_id(connection, clean_id)
    return workspace_row(row) if row else {}


def rename_workspace_row(
    connection: sqlite3.Connection,
    workspace_id: str,
    name: str,
    *,
    description: str | None = None,
) -> dict[str, Any]:
    """Rename one existing project workspace row."""
    clean_id = str(workspace_id or "").strip() or "default"
    current = workspace_by_id(connection, clean_id)
    if current is None:
        return {}
    next_description = str(description) if description is not None else str(current["description"])
    connection.execute(
        """
        UPDATE project_workspaces
        SET name = ?, description = ?, updated_at = ?
        WHERE workspace_id = ?
        """,
        (str(name or "").strip() or "Рабочее пространство", next_description, utc_timestamp(), clean_id),
    )
    row = workspace_by_id(connection, clean_id)
    return workspace_row(row) if row else {}


def workspace_by_id(connection: sqlite3.Connection, workspace_id: str) -> sqlite3.Row | None:
    """Return one workspace SQLite row by id."""
    return connection.execute(
        """
        SELECT workspace_id, name, description, settings_json,
               is_default, created_at, updated_at
        FROM project_workspaces
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()


def workspace_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert one workspace row to a plain dictionary."""
    return {
        "workspace_id": str(row["workspace_id"]),
        "name": str(row["name"]),
        "description": str(row["description"]),
        "settings": json_value(row, "settings_json") or {},
        "is_default": bool(row["is_default"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def profile_row(row: sqlite3.Row, *, include_workspace: bool = False) -> dict[str, str]:
    """Convert one store profile row to a plain dictionary."""
    result = {
        "profile_id": str(row["profile_id"]),
        "shop": str(row["shop"]),
        "site_url": str(row["site_url"]),
        "domain": str(row["domain"]),
        "display_name": str(row["display_name"]),
        "runtime_status": str(row["runtime_status"]),
        "latest_version_id": str(row["latest_version_id"]),
    }
    if include_workspace:
        result["workspace_id"] = str(row["workspace_id"])
    return result


def _workspace_id_from_name(name: str) -> str:
    value = slug(name).lower()
    if value == "profile":
        value = uuid4().hex[:12]
    return f"workspace:{value}"
