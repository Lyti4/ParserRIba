"""Workspace favorite helpers for local StoreProfile storage."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.store_profile_payloads import json_text, json_value, slug

SECRET_KEY_MARKERS = (
    "auth",
    "bearer",
    "captcha",
    "cookie",
    "credential",
    "password",
    "proxy",
    "secret",
    "token",
)


def ensure_secret_safe(value: Any, *, path: str = "payload") -> None:
    """Reject favorite metadata that appears to contain credentials."""
    if isinstance(value, dict):
        for key, nested in value.items():
            clean_key = str(key).lower()
            if any(marker in clean_key for marker in SECRET_KEY_MARKERS):
                raise ValueError(f"{path}.{key} is not safe for favorites")
            ensure_secret_safe(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            ensure_secret_safe(nested, path=f"{path}[{index}]")


def favorite_id_for(*, workspace_id: str, profile_id: str, favorite_type: str, stable_key: str) -> str:
    """Build a stable favorite id for one workspace target."""
    raw = f"{workspace_id}:{profile_id}:{favorite_type}:{stable_key}"
    return f"fav:{slug(raw)}"


def result_id_for(*, refresh_run_id: str, favorite_id: str) -> str:
    """Build a stable refresh result id."""
    return f"{slug(refresh_run_id)}:{slug(favorite_id)}"


def favorite_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a workspace_favorites row to a plain dictionary."""
    return {
        "favorite_id": str(row["favorite_id"]),
        "workspace_id": str(row["workspace_id"]),
        "profile_id": str(row["profile_id"]),
        "favorite_type": str(row["favorite_type"]),
        "display_label": str(row["display_label"]),
        "store_label": str(row["store_label"]),
        "stable_key": str(row["stable_key"]),
        "source_version_id": str(row["source_version_id"]),
        "payload": json_value(row, "payload_json") or {},
        "refresh_capability": str(row["refresh_capability"]),
        "last_refresh_status": str(row["last_refresh_status"]),
        "last_refresh_message": str(row["last_refresh_message"]),
        "last_refreshed_at": str(row["last_refreshed_at"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def refresh_run_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a favorite_refresh_runs row to a plain dictionary."""
    return {
        "refresh_run_id": str(row["refresh_run_id"]),
        "workspace_id": str(row["workspace_id"]),
        "requested_scope": str(row["requested_scope"]),
        "overall_status": str(row["overall_status"]),
        "requested_count": int(row["requested_count"]),
        "success_count": int(row["success_count"]),
        "skipped_count": int(row["skipped_count"]),
        "failed_count": int(row["failed_count"]),
        "started_at": str(row["started_at"]),
        "finished_at": str(row["finished_at"]),
    }


def refresh_result_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a favorite_refresh_results row to a plain dictionary."""
    return {
        "result_id": str(row["result_id"]),
        "refresh_run_id": str(row["refresh_run_id"]),
        "favorite_id": str(row["favorite_id"]),
        "workspace_id": str(row["workspace_id"]),
        "profile_id": str(row["profile_id"]),
        "status": str(row["status"]),
        "reason": str(row["reason"]),
        "saved_version_id": str(row["saved_version_id"]),
        "artifact_refs": json_value(row, "artifact_refs_json") or {},
        "created_at": str(row["created_at"]),
    }


def safe_json_text(value: Any, *, path: str) -> str:
    """Validate and serialize secret-safe favorite metadata."""
    ensure_secret_safe(value, path=path)
    return json_text(value or {})


def resolve_favorite_refresh_target(favorite: dict[str, Any]) -> dict[str, Any]:
    """Return a fail-closed refresh decision for one favorite row."""
    favorite_type = str(favorite.get("favorite_type") or "").strip()
    capability = str(favorite.get("refresh_capability") or "unresolved").strip()
    profile_id = str(favorite.get("profile_id") or "").strip()
    stable_key = str(favorite.get("stable_key") or "").strip()
    if favorite_type not in {"store", "catalog_node", "product"}:
        return _decision("failed", "unknown favorite type")
    if not stable_key:
        return _decision("skipped", "missing stable target key")
    if favorite_type in {"catalog_node", "product"} and not profile_id:
        return _decision("failed", "missing owning store profile")
    if capability in {"unsupported", "unresolved"}:
        return _decision("skipped", "favorite target is not refreshable yet")
    if favorite_type == "product":
        return _decision("skipped", "product refresh needs a product adapter target")
    return _decision("supported", "")


def _decision(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "reason": reason}
