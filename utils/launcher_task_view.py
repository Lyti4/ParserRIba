"""Normalized launcher-facing task views."""

from __future__ import annotations

from typing import Any

from models.task_actor import RunManifest


def build_launcher_task_view(
    *,
    manifest: RunManifest,
    summary_text: str = "",
    report_summary: dict[str, Any] | None = None,
    export_summary: dict[str, Any] | None = None,
    available_filter_counts: dict[str, dict[str, int]] | None = None,
    category_tree: list[dict[str, Any]] | None = None,
    selected_categories: list[str] | None = None,
    diagnostics_summary: dict[str, Any] | None = None,
    catalog_discovery: dict[str, Any] | None = None,
    intent_category_links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one unified launcher view-model for any local task result."""
    summary = dict(manifest.summary or {})
    categories = summary.get("categories")
    products_count = summary.get("products_count")
    return {
        "task_name": manifest.task_name,
        "status": manifest.status,
        "shop": manifest.shop,
        "intent": manifest.intent,
        "summary_text": summary_text,
        "artifact_paths": dict(manifest.artifact_paths or {}),
        "products_count": int(products_count) if isinstance(products_count, int) else 0,
        "categories": list(categories) if isinstance(categories, list) else [],
        "selected_categories": list(selected_categories or []),
        "category_tree": list(category_tree or []),
        "report_summary": dict(report_summary or {}),
        "export_summary": dict(export_summary or {}),
        "available_filter_counts": dict(available_filter_counts or {}),
        "diagnostics_summary": dict(diagnostics_summary or {}),
        "catalog_discovery": dict(catalog_discovery or {}),
        "intent_category_links": list(intent_category_links or []),
        "research_mode": str(summary.get("research_mode") or ""),
        "current_phase": str(summary.get("current_phase") or ""),
        "active_profile_id": str(summary.get("active_profile_id") or ""),
        "active_profile_version_id": str(summary.get("active_profile_version_id") or ""),
        "streamed_categories": list(summary.get("streamed_categories") or []),
        "partial_research": bool(summary.get("partial_research")),
    }
