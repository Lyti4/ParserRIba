"""Safe archive writer for interception diagnostics."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def build_interception_archive(result: dict[str, Any]) -> dict[str, Any]:
    """Build compact safe interception archive payload."""
    events = result.get("events") or []
    return {
        "shop": result.get("shop", ""),
        "category": result.get("category", ""),
        "category_url": result.get("category_url", ""),
        "run": result.get("run") or {},
        "attempt": result.get("attempt") or {},
        "interception": result.get("interception") or {},
        "site_errors": result.get("site_errors") or {},
        "events": [_compact_event(event) for event in events],
        "archived_at": datetime.now().isoformat(timespec="seconds"),
    }


def write_interception_archive(result: dict[str, Any], output_dir: Path | str) -> Path:
    """Write compact interception archive and return its path."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    category = _safe_name(str(result.get("category") or "category"))
    path = target_dir / f"pyaterochka_{category}_interception.json"
    payload = build_interception_archive(result)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": event.get("method", ""),
        "status": event.get("status"),
        "url": event.get("url", ""),
        "route_type": event.get("route_type", ""),
        "content_type": event.get("content_type", ""),
        "response_size": event.get("response_size", 0),
        "payload_kind": event.get("payload_kind", ""),
        "empty_products_payload": event.get("empty_products_payload"),
        "candidate_product_count": event.get("candidate_product_count", 0),
        "sample_products": event.get("sample_products", [])[:5],
        "schema_hints": event.get("schema_hints", {}),
        "payload_preview": event.get("payload_preview", ""),
        "replay_candidate": event.get("replay_candidate", False),
        "error": event.get("error", ""),
    }


def _safe_name(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in safe.split("_") if part)[:60] or "category"
