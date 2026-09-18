"""Workspace journal normalization and secret-safe diagnostics."""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from utils.store_profile_payloads import utc_timestamp

SECRET_MARK = "[redacted]"
SECRET_KEY_PARTS = ("password", "token", "cookie", "secret", "authorization", "auth_header", "proxy")


def build_workspace_event(
    *,
    workspace_id: str,
    profile_id: str = "",
    version_id: str = "",
    event_type: str,
    title: str,
    message: str = "",
    status: str = "info",
    counts: dict[str, Any] | None = None,
    artifact_refs: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
    event_id: str = "",
    created_at: str = "",
) -> dict[str, Any]:
    """Build one sanitized workspace journal event."""
    return {
        "event_id": event_id or uuid4().hex,
        "workspace_id": str(workspace_id or "default"),
        "profile_id": str(profile_id or ""),
        "version_id": str(version_id or ""),
        "event_type": str(event_type),
        "title": str(title),
        "message": str(message),
        "status": str(status or "info"),
        "counts": _plain_dict(counts),
        "artifact_refs": _plain_dict(artifact_refs),
        "diagnostics": sanitize_diagnostics(_plain_dict(diagnostics)),
        "created_at": created_at or utc_timestamp(),
    }


def sanitize_diagnostics(value: Any) -> Any:
    """Return diagnostics with secret-looking keys masked."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            result[key_text] = SECRET_MARK if _is_secret_key(key_text) else sanitize_diagnostics(item)
        return result
    if isinstance(value, list):
        return [sanitize_diagnostics(item) for item in value]
    return value


def json_text(value: Any) -> str:
    """Serialize journal payload JSON."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def insert_workspace_event(connection: sqlite3.Connection, event: dict[str, Any]) -> None:
    """Insert one sanitized workspace event row."""
    connection.execute(
        """
        INSERT INTO workspace_journal_events (
            event_id, workspace_id, profile_id, version_id, event_type, title,
            message, status, counts_json, artifact_refs_json, diagnostics_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"], event["workspace_id"], event["profile_id"], event["version_id"],
            event["event_type"], event["title"], event["message"], event["status"],
            json_text(event["counts"]), json_text(event["artifact_refs"]), json_text(event["diagnostics"]),
            event["created_at"],
        ),
    )


def list_workspace_events(connection: sqlite3.Connection, workspace_id: str, *, limit: int) -> list[dict[str, Any]]:
    """Return recent workspace events newest first."""
    rows = connection.execute(
        """
        SELECT event_id, workspace_id, profile_id, version_id, event_type, title,
               message, status, counts_json, artifact_refs_json, diagnostics_json, created_at
        FROM workspace_journal_events
        WHERE workspace_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (workspace_id, limit),
    ).fetchall()
    return [_workspace_event_row(row) for row in rows]


def _plain_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEY_PARTS)


def _workspace_event_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "event_id": str(row["event_id"]),
        "workspace_id": str(row["workspace_id"]),
        "profile_id": str(row["profile_id"]),
        "version_id": str(row["version_id"]),
        "event_type": str(row["event_type"]),
        "title": str(row["title"]),
        "message": str(row["message"]),
        "status": str(row["status"]),
        "counts": json.loads(str(row["counts_json"])),
        "artifact_refs": json.loads(str(row["artifact_refs_json"])),
        "diagnostics": json.loads(str(row["diagnostics_json"])),
        "created_at": str(row["created_at"]),
    }
