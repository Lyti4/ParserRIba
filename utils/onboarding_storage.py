"""SQLite-backed onboarding session storage."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from models.onboarding import OnboardingResult
from utils.discovery_profile_repository import initialize_discovery_profile_tables


def initialize_onboarding_tables(connection: sqlite3.Connection) -> None:
    """Create onboarding metadata tables if they do not exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_sessions (
            session_id TEXT PRIMARY KEY,
            shop_slug TEXT NOT NULL,
            site_url TEXT NOT NULL,
            intent TEXT NOT NULL,
            status TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_selected_categories (
            session_id TEXT NOT NULL,
            category_name TEXT NOT NULL,
            PRIMARY KEY (session_id, category_name)
        )
        """
    )


class OnboardingStorage:
    """Persist versioned onboarding sessions in SQLite."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def save_onboarding_session(self, result: OnboardingResult) -> None:
        """Upsert one onboarding session and its selected categories."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            initialize_onboarding_tables(connection)
            connection.execute(
                """
                INSERT INTO onboarding_sessions (
                    session_id, shop_slug, site_url, intent, status, schema_version,
                    payload_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    shop_slug=excluded.shop_slug,
                    site_url=excluded.site_url,
                    intent=excluded.intent,
                    status=excluded.status,
                    schema_version=excluded.schema_version,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    result.session_id,
                    result.shop_slug,
                    result.site_url,
                    result.intent,
                    result.status,
                    int(result.schema_version),
                    result.model_dump_json(),
                    result.updated_at.isoformat(),
                ),
            )
            connection.execute(
                "DELETE FROM onboarding_selected_categories WHERE session_id = ?",
                (result.session_id,),
            )
            for category_name in result.selected_categories:
                connection.execute(
                    "INSERT INTO onboarding_selected_categories (session_id, category_name) VALUES (?, ?)",
                    (result.session_id, category_name),
                )

    def get_onboarding_session(self, session_id: str) -> dict:
        """Return one saved onboarding session payload."""
        if not self.db_path.exists():
            return {}
        with self._connect() as connection:
            initialize_onboarding_tables(connection)
            row = connection.execute(
                "SELECT payload_json FROM onboarding_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return {}
        return json.loads(str(row["payload_json"]))

    def get_latest_profile_metadata(self, shop_slug: str, site_url: str) -> dict:
        """Return the latest active discovery profile identifiers for one site."""
        if not self.db_path.exists():
            return {}
        with self._connect() as connection:
            initialize_discovery_profile_tables(connection)
            row = connection.execute(
                """
                SELECT profile_id, latest_version_id, updated_at
                FROM discovery_profiles
                WHERE shop_slug = ? AND site_url = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (shop_slug, site_url),
            ).fetchone()
        if not row:
            return {}
        return {
            "profile_id": str(row["profile_id"]),
            "profile_version_id": str(row["latest_version_id"]),
            "updated_at": str(row["updated_at"]),
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
