"""SQLite-backed persistence for discovery profiles and their history."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from models.catalog_discovery import SiteProfileVersion


def initialize_discovery_profile_tables(connection: sqlite3.Connection) -> None:
    """Create discovery profile tables if they do not exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_profiles (
            profile_id TEXT PRIMARY KEY,
            shop_slug TEXT NOT NULL,
            site_url TEXT NOT NULL,
            latest_version_id TEXT NOT NULL,
            latest_payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_profile_versions (
            version_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            shop_slug TEXT NOT NULL,
            site_url TEXT NOT NULL,
            run_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_discovery_profile_versions_lookup
        ON discovery_profile_versions(shop_slug, site_url, created_at DESC)
        """
    )


class DiscoveryProfileRepository(Protocol):
    """Typed storage contract for discovery profiles."""

    def initialize(self) -> None:
        """Create required tables."""

    def save_profile_version(self, profile: SiteProfileVersion) -> None:
        """Persist one profile version and refresh the latest profile."""

    def get_latest_profile(self, shop_slug: str, site_url: str) -> SiteProfileVersion | None:
        """Return the latest known active profile for one store site."""

    def list_profile_versions(self, shop_slug: str, site_url: str) -> list[SiteProfileVersion]:
        """Return saved profile history for one store site."""


class SQLiteDiscoveryProfileRepository:
    """Persist discovery profile versions in one SQLite database."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        """Create discovery profile tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            initialize_discovery_profile_tables(connection)

    def save_profile_version(self, profile: SiteProfileVersion) -> None:
        """Upsert one historical version and refresh the current profile view."""
        self.initialize()
        timestamp = datetime.now(UTC).isoformat(timespec="microseconds")
        payload_json = profile.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO discovery_profile_versions (
                    version_id, profile_id, shop_slug, site_url, run_id, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(version_id) DO UPDATE SET
                    profile_id=excluded.profile_id,
                    shop_slug=excluded.shop_slug,
                    site_url=excluded.site_url,
                    run_id=excluded.run_id,
                    payload_json=excluded.payload_json,
                    created_at=excluded.created_at
                """,
                (
                    profile.version_id,
                    profile.profile_id,
                    profile.shop_slug,
                    profile.site_url,
                    profile.run_id,
                    payload_json,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO discovery_profiles (
                    profile_id, shop_slug, site_url, latest_version_id, latest_payload_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    shop_slug=excluded.shop_slug,
                    site_url=excluded.site_url,
                    latest_version_id=excluded.latest_version_id,
                    latest_payload_json=excluded.latest_payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    profile.profile_id,
                    profile.shop_slug,
                    profile.site_url,
                    profile.version_id,
                    payload_json,
                    timestamp,
                ),
            )

    def get_latest_profile(self, shop_slug: str, site_url: str) -> SiteProfileVersion | None:
        """Return the current profile snapshot for one store site."""
        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            initialize_discovery_profile_tables(connection)
            row = connection.execute(
                """
                SELECT latest_payload_json
                FROM discovery_profiles
                WHERE shop_slug = ? AND site_url = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (shop_slug, site_url),
            ).fetchone()
        if not row:
            return None
        return SiteProfileVersion.model_validate_json(str(row["latest_payload_json"]))

    def list_profile_versions(self, shop_slug: str, site_url: str) -> list[SiteProfileVersion]:
        """Return all known profile versions for one store site, newest first."""
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_discovery_profile_tables(connection)
            rows = connection.execute(
                """
                SELECT payload_json
                FROM discovery_profile_versions
                WHERE shop_slug = ? AND site_url = ?
                ORDER BY created_at DESC, version_id DESC
                """,
                (shop_slug, site_url),
            ).fetchall()
        return [SiteProfileVersion.model_validate_json(str(row["payload_json"])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
