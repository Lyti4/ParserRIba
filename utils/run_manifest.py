"""Helpers for building and writing local task run manifests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from models.onboarding import OnboardingResult
from models.task_actor import RunManifest
from utils.export_summary import build_export_summary


def build_store_export_manifest(
    *,
    payload: dict[str, Any],
    export_path: Path,
    db_path: Path,
    manifest_path: Path,
    excel_path: Path | None = None,
    task_name: str = "store_catalog_export",
) -> RunManifest:
    """Build a manifest from a normalized store export payload."""
    products_count = int(payload.get("products_count") or 0)
    status = "ok" if products_count > 0 else "empty"
    artifact_paths = {
        "json_path": str(export_path),
        "db_path": str(db_path),
        "manifest_path": str(manifest_path),
    }
    if excel_path is not None:
        artifact_paths["excel_path"] = str(excel_path)
    export_summary = build_export_summary(payload)
    return RunManifest(
        task_name=task_name,
        shop=str(payload.get("shop") or "store"),
        intent=str(payload.get("intent") or "fish_catalog"),
        input={
            "category": str(payload.get("category") or ""),
            "categories": list(payload.get("categories") or []),
            "attempts_requested": int(payload.get("attempts_requested") or 0),
        },
        status=status,
        artifact_paths=artifact_paths,
        summary={
            "backend": str(payload.get("shop") or "store"),
            "products_count": products_count,
            "stored_products_count": int(payload.get("stored_products_count") or 0),
            "attempts_used": int(payload.get("attempts_used") or 0),
            "categories": list(payload.get("categories") or []),
            "attempt": payload.get("attempt") or {},
            "proxy_summary": {"mode": "local", "paid_services": False},
            "wine_breakdown": export_summary["wine_breakdown"],
            "export_summary": export_summary,
        },
    )


def build_onboarding_manifest(
    *,
    result: OnboardingResult,
    task_input: dict[str, Any],
    manifest_path: Path,
) -> RunManifest:
    """Build a manifest from a guided onboarding result."""
    return RunManifest(
        task_name="site_onboarding_discovery",
        shop=result.shop_slug,
        intent=result.intent,
        input=task_input,
        status=result.status,
        artifact_paths={
            "session_state_path": result.artifact_paths.session_state_path,
            "runtime_db_path": result.artifact_paths.runtime_db_path,
            "runtime_report_dir": result.artifact_paths.runtime_report_dir,
            "manifest_path": str(manifest_path),
        },
        summary={
            "site_url": result.site_url,
            "category_count": len(result.category_tree),
            "category_tree": [node.model_dump(mode="json") for node in result.category_tree],
            "selected_categories": list(result.selected_categories),
            "diagnostics_summary": result.diagnostics_summary,
            "catalog_discovery": dict(result.diagnostics_summary.get("catalog_discovery") or {}),
            "intent_category_links": list(result.diagnostics_summary.get("intent_category_links") or []),
        },
    )


def write_run_manifest(manifest: RunManifest, manifest_path: Path) -> Path:
    """Write one run manifest as JSON."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.finished_at = datetime.utcnow()
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path
