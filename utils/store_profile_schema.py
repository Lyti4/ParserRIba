"""SQLite schema for central StoreProfile storage."""

from __future__ import annotations

import sqlite3

DEFAULT_WORKSPACE_ID = "default"
DEFAULT_WORKSPACE_NAME = "Основное рабочее пространство"


def initialize_store_profile_schema(connection: sqlite3.Connection) -> None:
    """Create StoreProfile v1 tables and indexes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS project_workspaces (
            workspace_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            settings_json TEXT NOT NULL,
            is_default INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS store_profiles (
            profile_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            shop TEXT NOT NULL,
            site_url TEXT NOT NULL,
            domain TEXT NOT NULL,
            display_name TEXT NOT NULL,
            runtime_status TEXT NOT NULL,
            latest_version_id TEXT NOT NULL,
            settings_json TEXT NOT NULL,
            diagnostics_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profile_versions (
            version_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            session_kind TEXT NOT NULL,
            source_task TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS catalog_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            catalog_json TEXT NOT NULL,
            selected_nodes_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS product_workspace_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            products_json TEXT NOT NULL,
            dynamic_filters_json TEXT NOT NULL,
            filters_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS filter_presets (
            preset_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            name TEXT NOT NULL,
            filters_json TEXT NOT NULL,
            available_filters_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS report_presets (
            preset_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            name TEXT NOT NULL,
            columns_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS price_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            profile_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_url TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            old_price REAL,
            in_stock INTEGER NOT NULL,
            captured_at TEXT NOT NULL,
            session_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspace_journal_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            version_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL,
            counts_json TEXT NOT NULL,
            artifact_refs_json TEXT NOT NULL,
            diagnostics_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspace_favorites (
            favorite_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            favorite_type TEXT NOT NULL,
            display_label TEXT NOT NULL,
            store_label TEXT NOT NULL,
            stable_key TEXT NOT NULL,
            source_version_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            refresh_capability TEXT NOT NULL,
            last_refresh_status TEXT NOT NULL,
            last_refresh_message TEXT NOT NULL,
            last_refreshed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorite_refresh_runs (
            refresh_run_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            requested_scope TEXT NOT NULL,
            overall_status TEXT NOT NULL,
            requested_count INTEGER NOT NULL,
            success_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorite_refresh_results (
            result_id TEXT PRIMARY KEY,
            refresh_run_id TEXT NOT NULL,
            favorite_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            saved_version_id TEXT NOT NULL,
            artifact_refs_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    _ensure_legacy_workspace_columns(connection)
    _ensure_default_workspace(connection)
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_store_profiles_site
            ON store_profiles(shop, site_url);
        CREATE INDEX IF NOT EXISTS idx_store_profiles_workspace
            ON store_profiles(workspace_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_profile_versions_profile
            ON profile_versions(profile_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_profile_versions_workspace
            ON profile_versions(workspace_id, profile_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_price_observations_lookup
            ON price_observations(profile_id, product_id, captured_at);
        CREATE INDEX IF NOT EXISTS idx_workspace_journal_events
            ON workspace_journal_events(workspace_id, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_favorites_unique_target
            ON workspace_favorites(workspace_id, profile_id, favorite_type, stable_key);
        CREATE INDEX IF NOT EXISTS idx_workspace_favorites_workspace
            ON workspace_favorites(workspace_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_workspace_favorites_profile
            ON workspace_favorites(workspace_id, profile_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_favorite_refresh_runs_workspace
            ON favorite_refresh_runs(workspace_id, started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_favorite_refresh_results_run
            ON favorite_refresh_results(refresh_run_id, created_at);
        """
    )


def _ensure_legacy_workspace_columns(connection: sqlite3.Connection) -> None:
    for table in (
        "store_profiles",
        "profile_versions",
        "catalog_snapshots",
        "product_workspace_snapshots",
        "filter_presets",
        "report_presets",
        "price_observations",
    ):
        if not _has_column(connection, table, "workspace_id"):
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN workspace_id TEXT NOT NULL DEFAULT '{DEFAULT_WORKSPACE_ID}'"
            )


def _ensure_default_workspace(connection: sqlite3.Connection) -> None:
    now = "1970-01-01T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO project_workspaces (
            workspace_id, name, description, settings_json,
            is_default, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id) DO NOTHING
        """,
        (DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_NAME, "", "{}", 1, now, now),
    )


def _has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row[1]) == column for row in rows)
