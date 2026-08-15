"""Guarded, repeatable P0 SQLite migration for fixture/verified copies only."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import BinaryIO, Iterator

from application.contracts import ApplicationContractError

P0_TABLES = frozenset(
    {
        "schema_migrations",
        "app_meta",
        "workflow_runs",
        "workflow_run_events",
        "run_control_requests",
    }
)

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, "
    "applied_at TEXT NOT NULL, app_version TEXT NOT NULL, UNIQUE(checksum));",
    "CREATE TABLE IF NOT EXISTS app_meta ("
    "key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);",
    "CREATE TABLE IF NOT EXISTS workflow_runs ("
    "run_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, profile_id TEXT NOT NULL, "
    "kind TEXT NOT NULL, run_state TEXT NOT NULL, terminal_outcome TEXT, reason_code TEXT, "
    "started_at TEXT NOT NULL, finished_at TEXT, manifest_json TEXT NOT NULL DEFAULT '{}');",
    "CREATE TABLE IF NOT EXISTS workflow_run_events ("
    "event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES workflow_runs(run_id) ON DELETE CASCADE, "
    "sequence_no INTEGER NOT NULL, event_type TEXT NOT NULL, phase TEXT NOT NULL, "
    "progress_current INTEGER NOT NULL, progress_total INTEGER NOT NULL, "
    "safe_payload_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(run_id, sequence_no));",
    "CREATE TABLE IF NOT EXISTS run_control_requests ("
    "request_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES workflow_runs(run_id) ON DELETE CASCADE, "
    "kind TEXT NOT NULL, state TEXT NOT NULL, requested_at TEXT NOT NULL, acknowledged_at TEXT, "
    "idempotency_key TEXT NOT NULL UNIQUE);",
    "CREATE INDEX IF NOT EXISTS idx_workflow_runs_workspace_started "
    "ON workflow_runs(workspace_id, started_at);",
    "CREATE INDEX IF NOT EXISTS idx_workflow_runs_state_started "
    "ON workflow_runs(run_state, started_at);",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_runs_active_conflict "
    "ON workflow_runs(workspace_id, profile_id, kind) "
    "WHERE run_state IN ('queued','running','cancelling');",
    "CREATE INDEX IF NOT EXISTS idx_workflow_run_events_run_sequence "
    "ON workflow_run_events(run_id, sequence_no);",
    "CREATE INDEX IF NOT EXISTS idx_run_control_requests_run_state "
    "ON run_control_requests(run_id, state);",
)
_SCHEMA_CHECKSUM = hashlib.sha256("\n".join(_SCHEMA).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MigrationTarget:
    path: Path
    classification: str


@dataclass(frozen=True)
class BackupReceipt:
    backup_path: str
    exact_preimage_path: str
    source_size: int
    destination_size: int
    source_sha256: str
    destination_sha256: str


@dataclass(frozen=True)
class MigrationReceipt:
    applied_versions: tuple[int, ...]
    backup: BackupReceipt
    foreign_key_violations: tuple[tuple[object, ...], ...]
    orphan_count: int
    table_counts: dict[str, int]


@dataclass(frozen=True)
class RestoreReceipt:
    restored_sha256: str
    restored_size: int


class P0MigrationRunner:
    _owners: dict[Path, int] = {}
    _owners_lock = Lock()

    def __init__(
        self,
        target: MigrationTarget,
        *,
        repository_root: Path | None = None,
        clock_iso: str = "2026-08-09T00:00:00Z",
        app_version: str = "p0a",
    ) -> None:
        self.target = MigrationTarget(Path(target.path), target.classification)
        self.repository_root = (
            repository_root or Path(__file__).resolve().parents[1]
        ).resolve()
        self.clock_iso = clock_iso
        self.app_version = app_version
        self._owner_token = id(self)
        self._guard_target_identity()

    @contextmanager
    def mutation_owner(self) -> Iterator[None]:
        path = self.target.path.resolve()
        lock_handle: BinaryIO | None = None
        with self._owners_lock:
            current = self._owners.get(path)
            if current is not None:
                raise ApplicationContractError(
                    "MUTATION_OWNER_CONFLICT", "Another migration mutation owner is active."
                )
            lock_handle = self._acquire_file_lock()
            self._owners[path] = self._owner_token
        try:
            yield
        finally:
            with self._owners_lock:
                if self._owners.get(path) == self._owner_token:
                    self._owners.pop(path, None)
                if lock_handle is not None:
                    self._release_file_lock(lock_handle)

    def _acquire_file_lock(self) -> BinaryIO:
        lock_path = self.target.path.with_name(f"{self.target.path.name}.p0a.lock")
        handle = lock_path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, 2)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as error:
            handle.close()
            raise ApplicationContractError(
                "MUTATION_OWNER_CONFLICT", "Another migration mutation owner is active."
            ) from error
        return handle

    @staticmethod
    def _release_file_lock(handle: BinaryIO) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def apply(self) -> MigrationReceipt:
        self._guard_source()
        with self.mutation_owner():
            backup = self._backup()
            connection = sqlite3.connect(self.target.path, timeout=0)
            try:
                connection.execute("PRAGMA busy_timeout=0")
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("BEGIN IMMEDIATE")
                applied = self._apply_schema(connection)
                connection.commit()
                foreign_keys = tuple(
                    tuple(row) for row in connection.execute("PRAGMA foreign_key_check")
                )
                orphan_count = self._orphan_count(connection)
                table_counts = {
                    table: int(
                        connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                    )
                    for table in sorted(P0_TABLES)
                }
            except Exception:
                connection.close()
                self._restore_backup_unlocked(backup)
                raise
            finally:
                try:
                    connection.close()
                except Exception:
                    pass
            return MigrationReceipt(
                applied, backup, foreign_keys, orphan_count, table_counts
            )

    def restore_backup(self, backup: BackupReceipt) -> RestoreReceipt:
        with self.mutation_owner():
            return self._restore_backup_unlocked(backup)

    def _restore_backup_unlocked(self, backup: BackupReceipt) -> RestoreReceipt:
        shutil.copyfile(backup.exact_preimage_path, self.target.path)
        restored_sha256 = _sha256(self.target.path)
        if restored_sha256 != backup.source_sha256:
            raise ApplicationContractError(
                "MIGRATION_RESTORE_VERIFY_FAILED", "Backup restore checksum mismatch."
            )
        return RestoreReceipt(restored_sha256, self.target.path.stat().st_size)

    def _guard_target_identity(self) -> None:
        path = self.target.path.resolve()
        operational = (
            self.repository_root / "data" / "profiles" / "store_profiles.db"
        ).resolve()
        if (
            self.target.classification not in {"deterministic_fixture", "verified_copy"}
            or path == operational
            or path.name != "store_profiles.db"
        ):
            raise ApplicationContractError(
                "MIGRATION_OPERATIONAL_DB_FORBIDDEN",
                "Operational store_profiles.db migration is forbidden.",
            )

    def _guard_source(self) -> None:
        path = self.target.path
        if not path.is_file() or path.stat().st_size <= 0:
            raise ApplicationContractError(
                "MIGRATION_SOURCE_INVALID", "Migration source must be non-empty SQLite."
            )
        try:
            uri = f"file:{path.resolve().as_posix()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.DatabaseError as error:
            raise ApplicationContractError(
                "MIGRATION_SOURCE_INVALID", "Migration source must be valid SQLite."
            ) from error
        if integrity != "ok":
            raise ApplicationContractError(
                "MIGRATION_SOURCE_INVALID", "Migration source failed integrity check."
            )

    def _backup(self) -> BackupReceipt:
        guard = sqlite3.connect(self.target.path, timeout=0)
        try:
            guard.execute("PRAGMA busy_timeout=0")
            guard.execute("BEGIN IMMEDIATE")
            source_hash = _sha256(self.target.path)
            stem = f"{self.target.path.name}.{source_hash[:12]}"
            raw_path = self.target.path.with_name(f"{stem}.p0a-preimage")
            sqlite_path = self.target.path.with_name(f"{stem}.p0a-sqlite-backup")
            shutil.copyfile(self.target.path, raw_path)
            guard.rollback()
        finally:
            guard.close()

        source = sqlite3.connect(self.target.path, timeout=0)
        destination = sqlite3.connect(sqlite_path)
        try:
            source.execute("PRAGMA busy_timeout=0")
            source.backup(destination)
            destination.commit()
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ApplicationContractError(
                    "MIGRATION_BACKUP_VERIFY_FAILED", "SQLite backup integrity check failed."
                )
        finally:
            destination.close()
            source.close()
        raw_hash = _sha256(raw_path)
        if raw_hash != source_hash or _sha256(self.target.path) != source_hash:
            raise ApplicationContractError(
                "MIGRATION_BACKUP_VERIFY_FAILED", "Exact preimage checksum mismatch."
            )
        sqlite_hash = _sha256(sqlite_path)
        return BackupReceipt(
            str(sqlite_path),
            str(raw_path),
            self.target.path.stat().st_size,
            sqlite_path.stat().st_size,
            source_hash,
            sqlite_hash,
        )

    def _apply_schema(self, connection: sqlite3.Connection) -> tuple[int, ...]:
        for statement in _SCHEMA:
            connection.execute(statement)
        existing = connection.execute(
            "SELECT checksum FROM schema_migrations WHERE version=1"
        ).fetchone()
        if existing:
            if existing[0] != _SCHEMA_CHECKSUM:
                raise ApplicationContractError(
                    "MIGRATION_CHECKSUM_MISMATCH", "Migration version 1 checksum mismatch."
                )
            return ()
        connection.execute(
            "INSERT INTO schema_migrations(version,name,checksum,applied_at,app_version) "
            "VALUES(1,'p0_application_contract',?,?,?)",
            (_SCHEMA_CHECKSUM, self.clock_iso, self.app_version),
        )
        database_uid = hashlib.sha256(
            str(self.target.path.resolve()).encode("utf-8")
        ).hexdigest()
        for key, value_json in (
            ("database_uid", f'"{database_uid}"'),
            ("minimum_reader_version", '"1"'),
            ("p0_application_contract", '"ready"'),
        ):
            connection.execute(
                "INSERT OR REPLACE INTO app_meta(key,value_json,updated_at) VALUES(?,?,?)",
                (key, value_json, self.clock_iso),
            )
        return (1,)

    @staticmethod
    def _orphan_count(connection: sqlite3.Connection) -> int:
        events = connection.execute(
            "SELECT COUNT(*) FROM workflow_run_events e LEFT JOIN workflow_runs r "
            "ON r.run_id=e.run_id WHERE r.run_id IS NULL"
        ).fetchone()[0]
        controls = connection.execute(
            "SELECT COUNT(*) FROM run_control_requests c LEFT JOIN workflow_runs r "
            "ON r.run_id=c.run_id WHERE r.run_id IS NULL"
        ).fetchone()[0]
        return int(events) + int(controls)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
