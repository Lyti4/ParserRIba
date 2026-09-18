"""Payload helpers for StoreProfile repository rows."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any


def json_row(row: sqlite3.Row | None, column: str) -> dict[str, Any] | None:
    """Decode a JSON object from one SQLite row column."""
    if not row:
        return None
    value = json.loads(str(row[column]))
    return value if isinstance(value, dict) else None


def json_value(row: sqlite3.Row | None, column: str) -> Any:
    """Decode any JSON value from one SQLite row column."""
    if not row:
        return None
    return json.loads(str(row[column]))


def price_observation_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a price-observation SQLite row to a plain dictionary."""
    return {
        "product_id": str(row["product_id"]),
        "product_url": str(row["product_url"]),
        "category": str(row["category"]),
        "price": float(row["price"]),
        "old_price": row["old_price"],
        "in_stock": bool(row["in_stock"]),
        "captured_at": str(row["captured_at"]),
        "session_id": str(row["session_id"]),
    }


def workspace_id_from_payload(payload: dict[str, Any]) -> str:
    """Return the owning project workspace id for one launcher payload."""
    workspace = payload.get("project_workspace") if isinstance(payload.get("project_workspace"), dict) else {}
    explicit = str(workspace.get("workspace_id") or "").strip() if isinstance(workspace, dict) else ""
    return explicit or "default"


def profile_id_from_payload(profile: dict[str, Any]) -> str:
    """Return a stable profile id from explicit profile data or site identity."""
    explicit = str(profile.get("profile_id") or "").strip()
    if explicit:
        return explicit
    return slug(str(profile.get("domain") or profile.get("site_url") or "profile"))


def runtime_status_from_payload(payload: dict[str, Any]) -> str:
    """Infer launcher profile runtime status without exposing technical noise."""
    diagnostics = payload["profile"].get("diagnostics") or {}
    if isinstance(diagnostics, dict):
        value = str(diagnostics.get("runtime_status") or diagnostics.get("status") or "").strip()
        if value:
            return value
    return "runtime_ready" if payload["products"].get("items") else "discovery_only"


def json_text(value: Any) -> str:
    """Serialize JSON with stable ordering and Russian text preserved."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def utc_timestamp() -> str:
    """Return an ISO UTC timestamp for profile rows."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


def slug(value: str) -> str:
    """Return a filesystem/SQLite friendly id fragment."""
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return normalized.strip("._-") or "profile"
