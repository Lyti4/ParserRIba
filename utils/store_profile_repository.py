"""Central SQLite storage for store profiles and launcher sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from models.launcher_state import LauncherAppState
from utils.launcher_profile_snapshot import build_launcher_profile_snapshot
from utils.store_profile_payloads import json_row, profile_id_from_payload, utc_timestamp, workspace_id_from_payload
from utils.store_profile_favorites import StoreProfileFavoritesMixin
from utils.store_profile_presets import apply_latest_presets, latest_presets
from utils.store_profile_prices import compare_latest_price_sessions, list_price_observations, record_price_observation
from utils.store_profile_schema import initialize_store_profile_schema
from utils.store_profile_sessions import get_profile_version, list_profile_versions
from utils.store_profile_workspaces import create_workspace_row, profile_row, rename_workspace_row, workspace_by_id, workspace_row
from utils.store_profile_writes import save_profile_payload_rows
from utils.workspace_journal import build_workspace_event, insert_workspace_event, list_workspace_events


class StoreProfileRepository(StoreProfileFavoritesMixin):
    """Persist StoreProfile versions, workspaces, presets and price history."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create StoreProfile v1 tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            initialize_store_profile_schema(connection)

    def ensure_default_workspace(self) -> dict[str, Any]:
        """Ensure and return the default project workspace."""
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            row = connection.execute(
                """
                SELECT workspace_id, name, description, settings_json,
                       is_default, created_at, updated_at
                FROM project_workspaces
                WHERE workspace_id = ?
                """,
                ("default",),
            ).fetchone()
        return workspace_row(row) if row else {}

    def list_workspaces(self) -> list[dict[str, Any]]:
        """Return local project workspaces for launcher selectors."""
        if not self.db_path.exists():
            return [self.ensure_default_workspace()]
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            rows = connection.execute(
                """
                SELECT workspace_id, name, description, settings_json,
                       is_default, created_at, updated_at
                FROM project_workspaces
                ORDER BY is_default DESC, updated_at DESC, name
                """
            ).fetchall()
        return [workspace_row(row) for row in rows]

    def create_workspace(self, name: str, *, description: str = "", workspace_id: str = "") -> dict[str, Any]:
        """Create a named project workspace for launcher use."""
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return create_workspace_row(connection, name, description=description, workspace_id=workspace_id)

    def rename_workspace(self, workspace_id: str, name: str, *, description: str | None = None) -> dict[str, Any]:
        """Rename an existing project workspace."""
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return rename_workspace_row(connection, workspace_id, name, description=description)

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        """Return one project workspace by id."""
        clean_id = str(workspace_id or "").strip() or "default"
        if not self.db_path.exists():
            return self.ensure_default_workspace() if clean_id == "default" else None
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            row = workspace_by_id(connection, clean_id)
        return workspace_row(row) if row else None

    def save_launcher_state(
        self,
        state: LauncherAppState,
        *,
        task_name: str = "",
        snapshot_id: str = "",
    ) -> dict[str, str]:
        """Persist the current Launcher V3 state as a StoreProfile version."""
        payload = build_launcher_profile_snapshot(state, task_name=task_name, snapshot_id=snapshot_id)
        if payload is None:
            return {}
        profile = payload["profile"]
        workspace_id = workspace_id_from_payload(payload)
        profile_id = profile_id_from_payload(profile)
        version_id = str(profile.get("profile_version_id") or payload["snapshot_id"]).strip()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            save_profile_payload_rows(
                connection,
                payload,
                profile_id=profile_id,
                workspace_id=workspace_id,
                version_id=version_id,
                task_name=task_name,
                now=utc_timestamp(),
            )
        return {"profile_id": profile_id, "version_id": version_id, "workspace_id": workspace_id}

    def get_latest_profile_by_site(self, shop: str, site_url: str, *, workspace_id: str = "") -> dict[str, Any] | None:
        """Return the latest saved launcher snapshot for one shop/site."""
        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            if workspace_id:
                row = connection.execute(
                    """
                    SELECT p.profile_id, p.workspace_id, v.payload_json
                    FROM store_profiles p
                    JOIN profile_versions v ON v.version_id = p.latest_version_id
                    WHERE p.workspace_id = ? AND p.shop = ? AND p.site_url = ?
                    ORDER BY p.updated_at DESC
                    LIMIT 1
                    """,
                    (str(workspace_id), shop, site_url),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT p.profile_id, p.workspace_id, v.payload_json
                    FROM store_profiles p
                    JOIN profile_versions v ON v.version_id = p.latest_version_id
                    WHERE p.shop = ? AND p.site_url = ?
                    ORDER BY p.updated_at DESC
                    LIMIT 1
                    """,
                    (shop, site_url),
                ).fetchone()
            if not row:
                return None
            payload = json_row(row, "payload_json")
            if payload is None:
                return None
            return apply_latest_presets(
                connection,
                payload,
                profile_id=str(row["profile_id"]),
                workspace_id=str(row["workspace_id"]),
            )

    def get_latest_presets(self, profile_id: str, *, workspace_id: str = "") -> dict[str, Any]:
        """Return the latest stored filter/report presets for one profile."""
        if not self.db_path.exists():
            return {}
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return latest_presets(connection, str(profile_id), workspace_id=str(workspace_id or ""))

    def list_profiles(self, *, workspace_id: str = "") -> list[dict[str, str]]:
        """Return known store profiles for launcher selectors."""
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            if workspace_id:
                rows = connection.execute(
                    """
                    SELECT profile_id, workspace_id, shop, site_url, domain,
                           display_name, runtime_status, latest_version_id
                    FROM store_profiles
                    WHERE workspace_id = ?
                    ORDER BY updated_at DESC, display_name
                    """,
                    (str(workspace_id),),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT profile_id, workspace_id, shop, site_url, domain,
                           display_name, runtime_status, latest_version_id
                    FROM store_profiles
                    ORDER BY updated_at DESC, display_name
                    """
                ).fetchall()
        return [profile_row(row, include_workspace=bool(workspace_id)) for row in rows]

    def list_profile_versions(self, *, workspace_id: str, profile_id: str) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return list_profile_versions(
                connection,
                workspace_id=str(workspace_id or "default"),
                profile_id=str(profile_id),
            )

    def get_profile_version(
        self,
        *,
        workspace_id: str,
        profile_id: str,
        version_id: str,
    ) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return get_profile_version(
                connection,
                workspace_id=str(workspace_id or "default"),
                profile_id=str(profile_id),
                version_id=str(version_id),
            )

    def record_workspace_event(self, **kwargs: Any) -> dict[str, Any]:
        self.initialize()
        event = build_workspace_event(**kwargs)
        with self._connect() as connection:
            insert_workspace_event(connection, event)
        return event

    def list_workspace_events(self, workspace_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return list_workspace_events(connection, str(workspace_id or "default"), limit=max(1, int(limit)))

    def record_price_observation(
        self,
        *,
        workspace_id: str = "default",
        profile_id: str,
        product_id: str,
        product_url: str,
        category: str,
        price: float,
        old_price: float | None,
        in_stock: bool,
        captured_at: str = "",
        session_id: str = "",
    ) -> int:
        self.initialize()
        with self._connect() as connection:
            return record_price_observation(
                connection,
                workspace_id=workspace_id,
                profile_id=profile_id,
                product_id=product_id,
                product_url=product_url,
                category=category,
                price=price,
                old_price=old_price,
                in_stock=in_stock,
                captured_at=captured_at,
                session_id=session_id,
            )

    def list_price_observations(
        self,
        profile_id: str,
        product_id: str,
        *,
        workspace_id: str = "",
    ) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return list_price_observations(connection, profile_id, product_id, workspace_id=str(workspace_id))

    def compare_latest_price_sessions(self, profile_id: str, *, workspace_id: str = "") -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return compare_latest_price_sessions(connection, str(profile_id), workspace_id=str(workspace_id))

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection
