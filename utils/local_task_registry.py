"""Local Apify-style task registry for launcher and automation flows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from models.report_request import ReportRequest
from models.task_actor import RunManifest
from utils.kb_loader import KBLoader
from utils.run_manifest import build_onboarding_manifest, write_run_manifest
from utils.site_onboarding import run_site_onboarding
from utils.storage_report_builder import build_excel_report_from_storage, build_report_filter_options
from utils.store_catalog_registry import DiscoverFunc, get_store_export_backend
from utils.store_export_runtime import build_store_export_payload, write_store_export

TaskFunc = Callable[..., Awaitable[RunManifest]]


@dataclass(frozen=True)
class LocalTask:
    """One launcher-callable local task definition."""

    task_name: str
    description: str
    run_func: TaskFunc
    compatibility_alias: bool = False


def list_local_tasks(*, include_compatibility: bool = False) -> list[str]:
    """Return registered local task names."""
    return sorted(
        name
        for name, task in _TASKS.items()
        if include_compatibility or not task.compatibility_alias
    )


async def run_local_task(
    task_name: str,
    task_input: dict[str, Any],
    *,
    root_dir: Path | str,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    """Run one registered local task and return its manifest."""
    task = _TASKS.get(str(task_name or ""))
    if not task:
        raise ValueError(f"Unsupported local task: {task_name}")
    return await task.run_func(
        task_input=task_input,
        root_dir=Path(root_dir),
        discover_func=discover_func,
    )


async def _run_store_catalog_export_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    shop = _required_text(task_input, "shop", task_name="store_catalog_export")
    intent = _required_text(task_input, "intent", task_name="store_catalog_export")
    task_name = str(task_input.get("_task_name") or "store_catalog_export")
    backend = get_store_export_backend(shop, intent)
    kb = KBLoader(str(root_dir / "knowledge_base")).load_shop(backend.shop)
    output_dir = root_dir / "data"
    payload = await build_store_export_payload(
        backend=backend,
        category_name=str(task_input.get("category") or backend.default_category),
        category_url=str(task_input.get("category_url") or ""),
        attempts=int(task_input.get("attempts") or 3),
        listen_seconds=int(task_input.get("listen_seconds") or 15),
        headless=task_input.get("headless"),
        manual_wait=bool(task_input.get("manual_wait") or False),
        browser_runtime=str(task_input.get("browser_runtime") or "camoufox"),
        kb_categories=kb.categories,
        discover_func=discover_func,
        expand_intent=bool(task_input.get("expand_intent", True)),
    )
    write_store_export(payload, output_dir, task_name=task_name)
    return RunManifest(**payload["run_manifest"])


def _required_text(task_input: dict[str, Any], field: str, *, task_name: str) -> str:
    value = str(task_input.get(field) or "").strip()
    if not value:
        raise ValueError(f"{task_name} requires explicit {field}")
    return value


async def _run_pyaterochka_catalog_export_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    payload = {**task_input, "shop": "pyaterochka", "intent": "fish_catalog", "_task_name": "pyaterochka_catalog_export"}
    return await _run_store_catalog_export_task(task_input=payload, root_dir=root_dir, discover_func=discover_func)


async def _run_pyaterochka_wine_export_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    payload = {**task_input, "shop": "pyaterochka", "intent": "wine_catalog", "_task_name": "pyaterochka_wine_export"}
    return await _run_store_catalog_export_task(task_input=payload, root_dir=root_dir, discover_func=discover_func)


async def _run_site_onboarding_discovery_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    del discover_func
    result = await asyncio.to_thread(
        run_site_onboarding,
        site_url=str(task_input.get("site_url") or ""),
        intent=str(task_input.get("intent") or ""),
        root_dir=root_dir,
        require_operator_confirmation=bool(task_input.get("require_operator_confirmation") or False),
        headless=task_input.get("headless"),
        manual_wait=bool(task_input.get("manual_wait") or False),
        listen_seconds=int(task_input.get("listen_seconds") or 6),
        research_mode=str(task_input.get("research_mode") or "live"),
        browser_runtime=str(task_input.get("browser_runtime") or "camoufox"),
        selected_categories=[
            str(item)
            for item in (task_input.get("selected_categories") or [])
        ],
    )
    manifest_path = Path(result.artifact_paths.runtime_report_dir) / "run_manifest.json"
    manifest = build_onboarding_manifest(
        result=result,
        task_input=task_input,
        manifest_path=manifest_path,
    )
    manifest.summary["active_profile_id"] = result.active_profile_id
    manifest.summary["active_profile_version_id"] = result.active_profile_version_id
    manifest.summary["streamed_categories"] = list(result.streamed_categories)
    manifest.summary["current_phase"] = result.current_phase
    manifest.summary["research_mode"] = result.research_mode
    profile_snapshot_path = str(result.diagnostics_summary.get("profile_snapshot_path") or "")
    if profile_snapshot_path:
        manifest.artifact_paths["profile_snapshot_path"] = profile_snapshot_path
    write_run_manifest(manifest, manifest_path)
    return manifest


async def _run_store_report_export_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    del discover_func
    request = ReportRequest(**task_input)
    result = build_excel_report_from_storage(
        request,
        db_path=root_dir / "data" / "products.db",
        output_dir=root_dir / "data" / "reports",
    )
    status = "ok" if result.products_count > 0 else "empty"
    manifest = RunManifest(
        task_name="store_report_export",
        shop=request.selection.shop,
        intent=request.selection.intent,
        input=task_input,
        status=status,
        artifact_paths={
            "excel_path": str(result.report_path),
            "db_path": str(root_dir / "data" / "products.db"),
        },
        summary={
            "products_count": result.products_count,
            "categories": result.categories,
            "filters_applied": result.filters_applied,
            "report_summary": result.report_summary,
        },
    )
    manifest_path = root_dir / "data" / "reports" / f"{request.output_name or request.selection.intent}_run_manifest.json"
    manifest.artifact_paths["manifest_path"] = str(manifest_path)
    write_run_manifest(manifest, manifest_path)
    return manifest


async def _run_store_report_filter_options_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
) -> RunManifest:
    del discover_func
    request = ReportRequest(**task_input)
    result = build_report_filter_options(
        request,
        db_path=root_dir / "data" / "products.db",
    )
    return RunManifest(
        task_name="store_report_filter_options",
        shop=request.selection.shop,
        intent=request.selection.intent,
        input=task_input,
        status="ok" if result.products_count > 0 else "empty",
        artifact_paths={
            "db_path": str(root_dir / "data" / "products.db"),
        },
        summary=result.model_dump(mode="json"),
    )


_TASKS: dict[str, LocalTask] = {
    "store_catalog_export": LocalTask(
        task_name="store_catalog_export",
        description="Export selected runtime-ready store catalog products into local JSON and SQLite.",
        run_func=_run_store_catalog_export_task,
    ),
    "pyaterochka_fish_export": LocalTask(
        task_name="pyaterochka_fish_export",
        description="Compatibility alias for Pyaterochka selected catalog export.",
        run_func=_run_pyaterochka_catalog_export_task,
        compatibility_alias=True,
    ),
    "pyaterochka_catalog_export": LocalTask(
        task_name="pyaterochka_catalog_export",
        description="Compatibility alias for Pyaterochka selected catalog export.",
        run_func=_run_pyaterochka_catalog_export_task,
        compatibility_alias=True,
    ),
    "pyaterochka_wine_export": LocalTask(
        task_name="pyaterochka_wine_export",
        description="Compatibility alias for Pyaterochka wine catalog export.",
        run_func=_run_pyaterochka_wine_export_task,
        compatibility_alias=True,
    ),
    "site_onboarding_discovery": LocalTask(
        task_name="site_onboarding_discovery",
        description="Run guided catalog discovery/onboarding for one site URL.",
        run_func=_run_site_onboarding_discovery_task,
    ),
    "store_report_export": LocalTask(
        task_name="store_report_export",
        description="Build a filtered local Excel report from stored products.",
        run_func=_run_store_report_export_task,
    ),
    "store_report_filter_options": LocalTask(
        task_name="store_report_filter_options",
        description="Collect available report filter values from stored products.",
        run_func=_run_store_report_filter_options_task,
    ),
}
