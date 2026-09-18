"""Preset loading helpers for StoreProfile repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.store_profile_payloads import json_value


def apply_latest_presets(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    profile_id: str,
    workspace_id: str = "",
) -> dict[str, Any]:
    """Overlay latest explicit presets onto one saved launcher payload."""
    presets = latest_presets(connection, profile_id, workspace_id=workspace_id)
    if not presets:
        return payload
    merged = dict(payload)
    merged["presets"] = presets
    filter_preset = presets.get("filter_preset") or {}
    report_preset = presets.get("report_column_preset") or {}
    if isinstance(filter_preset.get("filters"), dict):
        merged["filters"] = filter_preset["filters"]
    if isinstance(merged.get("report"), dict) and isinstance(report_preset.get("selected_columns"), list):
        report = dict(merged["report"])
        report["selected_columns"] = report_preset["selected_columns"]
        report["columns_touched"] = True
        merged["report"] = report
    return merged


def latest_presets(connection: sqlite3.Connection, profile_id: str, *, workspace_id: str = "") -> dict[str, Any]:
    """Return latest filter/report presets for one profile."""
    if workspace_id:
        filter_row = connection.execute(
            """
            SELECT filters_json, available_filters_json
            FROM filter_presets
            WHERE preset_id = ? AND workspace_id = ?
            """,
            (f"{profile_id}:latest-filter", workspace_id),
        ).fetchone()
        report_row = connection.execute(
            """
            SELECT columns_json
            FROM report_presets
            WHERE preset_id = ? AND workspace_id = ?
            """,
            (f"{profile_id}:latest-report", workspace_id),
        ).fetchone()
    else:
        filter_row = connection.execute(
            """
            SELECT filters_json, available_filters_json
            FROM filter_presets
            WHERE preset_id = ?
            """,
            (f"{profile_id}:latest-filter",),
        ).fetchone()
        report_row = connection.execute(
            """
            SELECT columns_json
            FROM report_presets
            WHERE preset_id = ?
            """,
            (f"{profile_id}:latest-report",),
        ).fetchone()
    if not filter_row and not report_row:
        return {}
    return {
        "filter_preset": {
            "filters": json_value(filter_row, "filters_json") if filter_row else {},
            "available_filters": json_value(filter_row, "available_filters_json") if filter_row else {},
        },
        "report_column_preset": {
            "selected_columns": json_value(report_row, "columns_json") if report_row else [],
        },
    }
