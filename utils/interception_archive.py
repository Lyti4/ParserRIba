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
        "api_first": _compact_api_first(result.get("api_first") or {}),
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


def _compact_api_first(api_first: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_count": api_first.get("candidate_count", 0),
        "ready_count": api_first.get("ready_count", 0),
        "missing_field_counts": api_first.get("missing_field_counts", {}),
        "field_coverage": api_first.get("field_coverage", {}),
        "mapper_readiness": api_first.get("mapper_readiness", {}),
        "samples": [_compact_api_first_sample(item) for item in (api_first.get("samples") or [])[:10]],
    }


def _compact_api_first_sample(sample: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "source_id": sample.get("source_id", ""),
        "name": sample.get("name", ""),
        "price": sample.get("price"),
        "image": sample.get("image", ""),
        "link": sample.get("link", ""),
        "availability": sample.get("availability"),
        "missing_fields": sample.get("missing_fields", []),
    }
    return {key: value for key, value in compact.items() if value not in ("", None, [])}


def _safe_name(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    return "_".join(part for part in safe.split("_") if part)[:60] or "category"
