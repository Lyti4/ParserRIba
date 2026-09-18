"""SQLite row operations for workspace favorites."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.store_profile_payloads import utc_timestamp
from utils.workspace_favorites import (
    favorite_id_for,
    favorite_row,
    refresh_result_row,
    refresh_run_row,
    result_id_for,
    safe_json_text,
)


def upsert_favorite_row(
    connection: sqlite3.Connection,
    *,
    workspace_id: str = "default",
    profile_id: str = "",
    favorite_type: str,
    display_label: str,
    stable_key: str,
    store_label: str = "",
    source_version_id: str = "",
    payload: dict[str, Any] | None = None,
    refresh_capability: str = "unresolved",
    favorite_id: str = "",
) -> dict[str, Any]:
    """Create or update one workspace-scoped favorite row."""
    clean_workspace = str(workspace_id or "default")
    clean_profile = str(profile_id or "")
    clean_type = str(favorite_type or "").strip()
    clean_key = str(stable_key or "").strip()
    clean_label = str(display_label or "").strip()
    if clean_type not in {"store", "catalog_node", "product"}:
        raise ValueError("favorite_type must be store, catalog_node or product")
    if not clean_key:
        raise ValueError("stable_key is required")
    if not clean_label:
        raise ValueError("display_label is required")
    clean_id = str(favorite_id or "").strip() or favorite_id_for(
        workspace_id=clean_workspace,
        profile_id=clean_profile,
        favorite_type=clean_type,
        stable_key=clean_key,
    )
    now = utc_timestamp()
    connection.execute(
        """
        INSERT INTO workspace_favorites (
            favorite_id, workspace_id, profile_id, favorite_type,
            display_label, store_label, stable_key, source_version_id,
            payload_json, refresh_capability, last_refresh_status,
            last_refresh_message, last_refreshed_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id, profile_id, favorite_type, stable_key) DO UPDATE SET
            display_label=excluded.display_label,
            store_label=excluded.store_label,
            source_version_id=excluded.source_version_id,
            payload_json=excluded.payload_json,
            refresh_capability=excluded.refresh_capability,
            updated_at=excluded.updated_at
        """,
        (
            clean_id,
            clean_workspace,
            clean_profile,
            clean_type,
            clean_label,
            str(store_label or ""),
            clean_key,
            str(source_version_id or ""),
            safe_json_text(payload or {}, path="payload"),
            str(refresh_capability or "unresolved"),
            "never",
            "",
            "",
            now,
            now,
        ),
    )
    row = connection.execute(
        """
        SELECT *
        FROM workspace_favorites
        WHERE workspace_id = ? AND profile_id = ? AND favorite_type = ? AND stable_key = ?
        LIMIT 1
        """,
        (clean_workspace, clean_profile, clean_type, clean_key),
    ).fetchone()
    return favorite_row(row)


def list_favorite_rows(connection: sqlite3.Connection, workspace_id: str, *, profile_id: str = "") -> list[dict[str, Any]]:
    """Return favorites from one workspace, optionally scoped to one profile."""
    clean_workspace = str(workspace_id or "default")
    if profile_id:
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_favorites
            WHERE workspace_id = ? AND profile_id = ?
            ORDER BY updated_at DESC, display_label
            """,
            (clean_workspace, str(profile_id)),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_favorites
            WHERE workspace_id = ?
            ORDER BY updated_at DESC, store_label, display_label
            """,
            (clean_workspace,),
        ).fetchall()
    return [favorite_row(row) for row in rows]


def get_favorite_row(connection: sqlite3.Connection, workspace_id: str, favorite_id: str) -> dict[str, Any] | None:
    """Return one favorite by workspace and id."""
    row = connection.execute(
        """
        SELECT *
        FROM workspace_favorites
        WHERE workspace_id = ? AND favorite_id = ?
        LIMIT 1
        """,
        (str(workspace_id or "default"), str(favorite_id)),
    ).fetchone()
    return favorite_row(row) if row else None


def remove_favorite_row(connection: sqlite3.Connection, workspace_id: str, favorite_id: str) -> bool:
    """Remove one favorite row."""
    cursor = connection.execute(
        """
        DELETE FROM workspace_favorites
        WHERE workspace_id = ? AND favorite_id = ?
        """,
        (str(workspace_id or "default"), str(favorite_id)),
    )
    return cursor.rowcount > 0


def record_refresh_run_row(
    connection: sqlite3.Connection,
    *,
    workspace_id: str = "default",
    refresh_run_id: str,
    requested_scope: str,
    overall_status: str = "partial",
    requested_count: int = 0,
    success_count: int = 0,
    skipped_count: int = 0,
    failed_count: int = 0,
    started_at: str = "",
    finished_at: str = "",
) -> dict[str, Any]:
    """Persist one favorite refresh batch summary."""
    now = utc_timestamp()
    clean_started = str(started_at or now)
    clean_finished = str(finished_at or "")
    connection.execute(
        """
        INSERT INTO favorite_refresh_runs (
            refresh_run_id, workspace_id, requested_scope, overall_status,
            requested_count, success_count, skipped_count, failed_count,
            started_at, finished_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(refresh_run_id) DO UPDATE SET
            overall_status=excluded.overall_status,
            requested_count=excluded.requested_count,
            success_count=excluded.success_count,
            skipped_count=excluded.skipped_count,
            failed_count=excluded.failed_count,
            finished_at=excluded.finished_at
        """,
        (
            str(refresh_run_id),
            str(workspace_id or "default"),
            str(requested_scope or "selected"),
            str(overall_status or "partial"),
            int(requested_count),
            int(success_count),
            int(skipped_count),
            int(failed_count),
            clean_started,
            clean_finished,
        ),
    )
    row = connection.execute(
        "SELECT * FROM favorite_refresh_runs WHERE refresh_run_id = ? LIMIT 1",
        (str(refresh_run_id),),
    ).fetchone()
    return refresh_run_row(row)


def record_refresh_result_row(
    connection: sqlite3.Connection,
    *,
    workspace_id: str = "default",
    refresh_run_id: str,
    favorite_id: str,
    status: str,
    profile_id: str = "",
    reason: str = "",
    saved_version_id: str = "",
    artifact_refs: dict[str, Any] | None = None,
    created_at: str = "",
) -> dict[str, Any]:
    """Persist one per-favorite refresh result and update favorite status."""
    clean_workspace = str(workspace_id or "default")
    clean_favorite = str(favorite_id)
    clean_status = str(status or "failed")
    now = str(created_at or utc_timestamp())
    clean_result_id = result_id_for(refresh_run_id=str(refresh_run_id), favorite_id=clean_favorite)
    connection.execute(
        """
        INSERT INTO favorite_refresh_results (
            result_id, refresh_run_id, favorite_id, workspace_id, profile_id,
            status, reason, saved_version_id, artifact_refs_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(result_id) DO UPDATE SET
            status=excluded.status,
            reason=excluded.reason,
            saved_version_id=excluded.saved_version_id,
            artifact_refs_json=excluded.artifact_refs_json,
            created_at=excluded.created_at
        """,
        (
            clean_result_id,
            str(refresh_run_id),
            clean_favorite,
            clean_workspace,
            str(profile_id or ""),
            clean_status,
            str(reason or ""),
            str(saved_version_id or ""),
            safe_json_text(artifact_refs or {}, path="artifact_refs"),
            now,
        ),
    )
    connection.execute(
        """
        UPDATE workspace_favorites
        SET last_refresh_status = ?,
            last_refresh_message = ?,
            last_refreshed_at = ?,
            updated_at = ?
        WHERE workspace_id = ? AND favorite_id = ?
        """,
        (clean_status, str(reason or ""), now, now, clean_workspace, clean_favorite),
    )
    row = connection.execute(
        "SELECT * FROM favorite_refresh_results WHERE result_id = ? LIMIT 1",
        (clean_result_id,),
    ).fetchone()
    return refresh_result_row(row)
