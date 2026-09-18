"""Write helpers for StoreProfile repository payloads."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.store_profile_payloads import json_text, runtime_status_from_payload
from utils.store_profile_prices import save_price_observations_from_payload


def save_profile_payload_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    profile_id: str,
    workspace_id: str,
    version_id: str,
    task_name: str,
    now: str,
) -> None:
    """Persist all rows derived from one launcher profile payload."""
    _upsert_workspace(connection, payload, workspace_id, now)
    _upsert_profile(connection, payload, profile_id, workspace_id, version_id, now)
    _insert_version(connection, payload, profile_id, workspace_id, version_id, task_name, now)
    _insert_catalog_snapshot(connection, payload, profile_id, workspace_id, version_id, now)
    _insert_workspace_snapshot(connection, payload, profile_id, workspace_id, version_id, now)
    _upsert_presets(connection, payload, profile_id, workspace_id, now)
    save_price_observations_from_payload(
        connection,
        payload,
        workspace_id=workspace_id,
        profile_id=profile_id,
        version_id=version_id,
        captured_at=now,
    )


def _upsert_workspace(connection: sqlite3.Connection, payload: dict[str, Any], workspace_id: str, now: str) -> None:
    workspace = payload.get("project_workspace") if isinstance(payload.get("project_workspace"), dict) else {}
    name = str(workspace.get("name") or "").strip() if isinstance(workspace, dict) else ""
    description = str(workspace.get("description") or "").strip() if isinstance(workspace, dict) else ""
    settings = workspace.get("settings") if isinstance(workspace, dict) else {}
    is_default = bool(workspace.get("is_default")) if isinstance(workspace, dict) else workspace_id == "default"
    if not name:
        name = "Основное рабочее пространство" if workspace_id == "default" else workspace_id
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
            settings_json=excluded.settings_json,
            updated_at=excluded.updated_at
        """,
        (workspace_id, name, description, json_text(settings or {}), int(is_default), now, now),
    )


def _upsert_profile(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    profile_id: str,
    workspace_id: str,
    version_id: str,
    now: str,
) -> None:
    profile = payload["profile"]
    connection.execute(
        """
        INSERT INTO store_profiles (
            profile_id, workspace_id, shop, site_url, domain, display_name,
            runtime_status, latest_version_id, settings_json,
            diagnostics_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(profile_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            shop=excluded.shop,
            site_url=excluded.site_url,
            domain=excluded.domain,
            display_name=excluded.display_name,
            runtime_status=excluded.runtime_status,
            latest_version_id=excluded.latest_version_id,
            settings_json=excluded.settings_json,
            diagnostics_json=excluded.diagnostics_json,
            updated_at=excluded.updated_at
        """,
        (
            profile_id,
            workspace_id,
            str(profile.get("shop") or ""),
            str(profile.get("site_url") or ""),
            str(profile.get("domain") or ""),
            str(profile.get("display_name") or ""),
            runtime_status_from_payload(payload),
            version_id,
            json_text(profile.get("settings") or {}),
            json_text(profile.get("diagnostics") or {}),
            now,
            now,
        ),
    )


def _insert_version(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    profile_id: str,
    workspace_id: str,
    version_id: str,
    task_name: str,
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO profile_versions (
            version_id, workspace_id, profile_id, session_kind, source_task,
            payload_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(version_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            profile_id=excluded.profile_id,
            session_kind=excluded.session_kind,
            source_task=excluded.source_task,
            payload_json=excluded.payload_json,
            created_at=excluded.created_at
        """,
        (version_id, workspace_id, profile_id, "launcher_snapshot", task_name, json_text(payload), now),
    )


def _insert_catalog_snapshot(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    profile_id: str,
    workspace_id: str,
    version_id: str,
    now: str,
) -> None:
    catalog = payload["catalog"]
    connection.execute(
        """
        INSERT INTO catalog_snapshots (
            snapshot_id, workspace_id, profile_id, version_id, catalog_json,
            selected_nodes_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            catalog_json=excluded.catalog_json,
            selected_nodes_json=excluded.selected_nodes_json,
            created_at=excluded.created_at
        """,
        (
            f"{version_id}:catalog",
            workspace_id,
            profile_id,
            version_id,
            json_text(catalog),
            json_text(catalog.get("selected_nodes") or []),
            now,
        ),
    )


def _insert_workspace_snapshot(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    profile_id: str,
    workspace_id: str,
    version_id: str,
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO product_workspace_snapshots (
            snapshot_id, workspace_id, profile_id, version_id, products_json,
            dynamic_filters_json, filters_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            products_json=excluded.products_json,
            dynamic_filters_json=excluded.dynamic_filters_json,
            filters_json=excluded.filters_json,
            created_at=excluded.created_at
        """,
        (
            f"{version_id}:workspace",
            workspace_id,
            profile_id,
            version_id,
            json_text(payload["products"]),
            json_text(payload["dynamic_filters"]),
            json_text(payload["filters"]),
            now,
        ),
    )


def _upsert_presets(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    profile_id: str,
    workspace_id: str,
    now: str,
) -> None:
    presets = payload["presets"]
    filter_preset = presets.get("filter_preset") or {}
    report_preset = presets.get("report_column_preset") or {}
    connection.execute(
        """
        INSERT INTO filter_presets (
            preset_id, workspace_id, profile_id, name, filters_json,
            available_filters_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(preset_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            filters_json=excluded.filters_json,
            available_filters_json=excluded.available_filters_json,
            updated_at=excluded.updated_at
        """,
        (
            f"{profile_id}:latest-filter",
            workspace_id,
            profile_id,
            "Последние фильтры",
            json_text(filter_preset.get("filters") or {}),
            json_text(filter_preset.get("available_filters") or {}),
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO report_presets (
            preset_id, workspace_id, profile_id, name, columns_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(preset_id) DO UPDATE SET
            workspace_id=excluded.workspace_id,
            columns_json=excluded.columns_json,
            updated_at=excluded.updated_at
        """,
        (
            f"{profile_id}:latest-report",
            workspace_id,
            profile_id,
            "Последние колонки отчёта",
            json_text(report_preset.get("selected_columns") or []),
            now,
            now,
        ),
    )
