"""Run and attempt context objects for ParserRIba."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    """Return a compact UTC timestamp for reports."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class StoreState:
    """Observed store/address state for one site session."""

    store_id: str = ""
    region: str = ""
    address_detected: bool = False
    selected_store_detected: bool = False
    catalog_mode: str = ""
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""
        return asdict(self)


@dataclass
class RunContext:
    """Top-level context for one parser run."""

    store: str
    mode: str = "parse"
    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: str = field(default_factory=utc_now_iso)
    rate_profile: str = "protected-store"
    metadata: dict[str, Any] = field(default_factory=dict)

    def start_attempt(self, attempt: int, proxy: str = "", session_id: str = "") -> "AttemptContext":
        """Create an attempt context attached to this run."""
        return AttemptContext(
            run_id=self.run_id,
            store=self.store,
            mode=self.mode,
            attempt=attempt,
            proxy=proxy,
            session_id=session_id,
        )

    def summary(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""
        return asdict(self)


@dataclass
class AttemptContext:
    """Context and outcome for one parser attempt."""

    run_id: str
    store: str
    mode: str
    attempt: int
    proxy: str = ""
    session_id: str = ""
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    status: str = "running"
    reason: str = ""
    store_state: StoreState = field(default_factory=StoreState)
    metrics: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str, reason: str = "") -> None:
        """Mark the attempt as finished."""
        self.status = status
        self.reason = reason
        self.finished_at = utc_now_iso()

    def summary(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticEvent:
    """Safe report event captured during a run."""

    kind: str
    message: str
    severity: str = "info"
    path: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def summary(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""
        return asdict(self)
