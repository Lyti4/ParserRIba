"""Async deterministic shared application workflow."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable

from application.contracts import (
    ApplicationContractError,
    CancelRunCommand,
    EventJournal,
    EventType,
    RunApplicationFixtureCommand,
    RunState,
    TerminalOutcome,
    WorkflowRunResult,
)
from application.fixture import fixture_data


class CancellationBoundary(str, Enum):
    BEFORE_START = "before_start"
    DURING_PROGRESS = "during_progress"
    BEFORE_COMMIT = "before_commit"


BoundaryObserver = Callable[[CancellationBoundary, str], None | Awaitable[None]]
FixtureDataProvider = Callable[[], dict[str, Any]]


class ApplicationWorkflow:
    def __init__(
        self,
        *,
        boundary_observer: BoundaryObserver | None = None,
        fixture_data_provider: FixtureDataProvider = fixture_data,
    ) -> None:
        self._cancelled_run_ids: set[str] = set()
        self._run_clients: dict[str, str] = {}
        self._terminal_run_ids: set[str] = set()
        self._boundary_observer = boundary_observer
        self._fixture_data_provider = fixture_data_provider

    def request_cancel(self, command: CancelRunCommand) -> None:
        if command.run_id in self._terminal_run_ids:
            raise ApplicationContractError(
                "CONTROL_RUN_TERMINAL", "A terminal run cannot be cancelled."
            )
        owner = self._run_clients.get(command.run_id)
        if owner is None:
            raise ApplicationContractError(
                "CONTROL_RUN_NOT_ACTIVE", "Cancellation target run is not active."
            )
        if owner != command.client_id:
            raise ApplicationContractError(
                "CONTROL_CLIENT_NOT_OWNER", "Only the run client may request cancellation."
            )
        self._cancelled_run_ids.add(command.run_id)

    async def run_fixture(self, command: RunApplicationFixtureCommand) -> WorkflowRunResult:
        if command.run_id in self._terminal_run_ids:
            raise ApplicationContractError(
                "RUN_ALREADY_TERMINAL", "A terminal run ID cannot be started again."
            )
        owner = self._run_clients.get(command.run_id)
        if owner is not None and owner != command.client_id:
            raise ApplicationContractError(
                "RUN_CLIENT_CONFLICT", "Run ID is already owned by another client."
            )
        self._run_clients[command.run_id] = command.client_id
        journal = EventJournal(run_id=command.run_id, created_at=command.clock_iso)
        await self._observe(CancellationBoundary.BEFORE_START, command.run_id)
        if command.run_id in self._cancelled_run_ids:
            return self._cancelled(command, journal)
        journal.append(EventType.RUN_STARTED, phase="research", progress_current=0, progress_total=3)
        data = self._fixture_data_provider()
        journal.append(EventType.PROGRESS, phase="catalog", progress_current=1, progress_total=3, catalog_node_count=len(data["catalog_nodes"]))
        await asyncio.sleep(0)
        await self._observe(CancellationBoundary.DURING_PROGRESS, command.run_id)
        if command.run_id in self._cancelled_run_ids:
            return self._cancelled(command, journal)
        journal.append(EventType.PROGRESS, phase="products", progress_current=2, progress_total=3, product_count=len(data["products"]), selected_product_count=len(data["selected_product_ids"]))
        await self._observe(CancellationBoundary.BEFORE_COMMIT, command.run_id)
        if command.run_id in self._cancelled_run_ids:
            return self._cancelled(command, journal)
        artifact_dir = Path(command.artifact_dir or command.output_dir or command.root_dir or ".")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        report_path = artifact_dir / "fixture_report.json"
        report = {
            "catalog_nodes": list(data["catalog_nodes"]),
            "products": list(data["products"]),
            "research": data["research"],
            "run_id": command.run_id,
            "selected_product_ids": list(data["selected_product_ids"]),
            "terminal_outcome": "ready",
        }
        source_catalog_node_ids = data.get("source_catalog_node_ids")
        if source_catalog_node_ids is not None:
            report["source_catalog_node_ids"] = list(source_catalog_node_ids)
        report_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        temporary = report_path.with_suffix(".json.tmp")
        temporary.write_bytes(report_bytes)
        temporary.replace(report_path)
        report_sha256 = hashlib.sha256(report_bytes).hexdigest()
        journal.append(EventType.TERMINAL, phase="report", progress_current=3, progress_total=3, reason_code="WORKFLOW_READY", message="Fixture workflow ready.", report_sha256=report_sha256, terminal_outcome="ready")
        artifact_paths = {"report_json": str(report_path)}
        store_path: Path | None = None
        if command.root_dir:
            try:
                store_path = self._prepare_fixture_store(Path(command.root_dir), command.clock_iso)
                artifact_paths["store_profiles_db"] = str(store_path)
            except Exception:
                report_path.unlink(missing_ok=True)
                raise
        result_summary = {
            "selected_product_ids": list(data["selected_product_ids"]),
            "report_sha256": report_sha256,
        }
        if source_catalog_node_ids is not None:
            result_summary["source_catalog_node_ids"] = list(source_catalog_node_ids)
        result = WorkflowRunResult(
            run_id=command.run_id,
            run_state=RunState.TERMINAL,
            terminal_outcome=TerminalOutcome.READY,
            reason_code="WORKFLOW_READY",
            message="Fixture workflow ready.",
            retryable=False,
            started_at=command.clock_iso,
            finished_at=command.clock_iso,
            artifact_paths=artifact_paths,
            result=result_summary,
            events=journal.events,
        )
        if store_path is not None:
            self._persist_fixture_run(store_path, command, result)
        self._terminal_run_ids.add(command.run_id)
        return result

    def _prepare_fixture_store(self, root_dir: Path, clock_iso: str) -> Path:
        from application.migration import MigrationTarget, P0MigrationRunner

        store_path = root_dir / "data" / "profiles" / "store_profiles.db"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        if not store_path.exists() or store_path.stat().st_size == 0:
            with sqlite3.connect(store_path) as connection:
                connection.execute("PRAGMA user_version=1")
                connection.commit()
        P0MigrationRunner(
            MigrationTarget(store_path, "deterministic_fixture"),
            repository_root=Path(__file__).resolve().parents[1],
            clock_iso=clock_iso,
        ).apply()
        return store_path

    def _persist_fixture_run(
        self,
        store_path: Path,
        command: RunApplicationFixtureCommand,
        result: WorkflowRunResult,
    ) -> None:
        from application.migration import MigrationTarget, P0MigrationRunner

        runner = P0MigrationRunner(
            MigrationTarget(store_path, "deterministic_fixture"),
            repository_root=Path(__file__).resolve().parents[1],
            clock_iso=command.clock_iso,
        )
        with runner.mutation_owner(), sqlite3.connect(store_path, timeout=0) as connection:
            connection.execute("PRAGMA busy_timeout=0")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM workflow_run_events WHERE run_id=?", (command.run_id,))
            connection.execute("DELETE FROM run_control_requests WHERE run_id=?", (command.run_id,))
            connection.execute("DELETE FROM workflow_runs WHERE run_id=?", (command.run_id,))
            connection.execute(
                "INSERT INTO workflow_runs(run_id,workspace_id,profile_id,kind,run_state,terminal_outcome,reason_code,started_at,finished_at,manifest_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    command.run_id,
                    command.workspace_id,
                    command.profile_id,
                    "application_workflow_fixture",
                    result.run_state.value,
                    result.terminal_outcome.value,
                    result.reason_code,
                    result.started_at,
                    result.finished_at,
                    json.dumps(result.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
                ),
            )
            for event in result.events:
                connection.execute(
                    "INSERT INTO workflow_run_events(event_id,run_id,sequence_no,event_type,phase,progress_current,progress_total,safe_payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        f"{command.run_id}:{event.sequence:04d}",
                        command.run_id,
                        event.sequence,
                        event.event_type.value,
                        event.phase,
                        event.progress_current,
                        event.progress_total,
                        json.dumps(
                            event.model_dump(mode="json")["payload"],
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        event.created_at,
                    ),
                )
            if result.terminal_outcome is TerminalOutcome.CANCELLED:
                connection.execute(
                    "INSERT INTO run_control_requests(request_id,run_id,kind,state,requested_at,acknowledged_at,idempotency_key) VALUES(?,?,?,?,?,?,?)",
                    (
                        f"{command.run_id}:cancel",
                        command.run_id,
                        "cancel",
                        "acknowledged",
                        command.clock_iso,
                        command.clock_iso,
                        f"{command.client_id}:{command.run_id}:cancel",
                    ),
                )
            connection.commit()

    async def _observe(self, boundary: CancellationBoundary, run_id: str) -> None:
        if self._boundary_observer is None:
            return
        observed = self._boundary_observer(boundary, run_id)
        if inspect.isawaitable(observed):
            await observed

    def _cancelled(self, command: RunApplicationFixtureCommand, journal: EventJournal) -> WorkflowRunResult:
        journal.append(EventType.TERMINAL, phase="cancelled", progress_current=len(journal.events), progress_total=3, reason_code="WORKFLOW_CANCELLED", message="Fixture workflow cancelled.", terminal_outcome="cancelled")
        artifact_paths: dict[str, str] = {}
        store_path: Path | None = None
        if command.root_dir:
            store_path = self._prepare_fixture_store(Path(command.root_dir), command.clock_iso)
            artifact_paths["store_profiles_db"] = str(store_path)
        result = WorkflowRunResult(
            run_id=command.run_id,
            run_state=RunState.TERMINAL,
            terminal_outcome=TerminalOutcome.CANCELLED,
            reason_code="WORKFLOW_CANCELLED",
            message="Fixture workflow cancelled.",
            retryable=False,
            started_at=command.clock_iso,
            finished_at=command.clock_iso,
            artifact_paths=artifact_paths,
            events=journal.events,
        )
        if store_path is not None:
            self._persist_fixture_run(store_path, command, result)
        self._terminal_run_ids.add(command.run_id)
        return result
