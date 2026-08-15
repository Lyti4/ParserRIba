"""Launcher-facing helpers for report and filter local tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.local_task_adapter import LocalTaskProcessResult, run_local_task_subprocess


def run_launcher_report_export(
    *,
    root_dir: Path | str,
    shop: str,
    intent: str,
    categories: list[str] | None = None,
    selected_product_ids: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    output_name: str = "",
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher report export task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="store_report_export",
        task_input={
            "selection": {
                "shop": shop,
                "intent": intent,
                "categories": list(categories or []),
                "selected_product_ids": list(selected_product_ids or []),
            },
            "filters": dict(filters or {}),
            "output_name": output_name,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_report_filter_options(
    *,
    root_dir: Path | str,
    shop: str,
    intent: str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher report filter-options task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="store_report_filter_options",
        task_input={
            "selection": {
                "shop": shop,
                "intent": intent,
                "categories": list(categories or []),
            },
            "filters": {},
            "output_name": "",
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_fish_report_export(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    selected_product_ids: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    output_name: str = "pyaterochka_fish_report",
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher fish report export using KB-resolved categories."""
    resolved = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="fish_catalog",
        categories=categories,
    )
    return run_launcher_report_export(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="fish_catalog",
        categories=resolved,
        selected_product_ids=selected_product_ids,
        filters=filters,
        output_name=output_name,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_fish_report_filter_options(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher fish filter-options task using KB-resolved categories."""
    resolved = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="fish_catalog",
        categories=categories,
    )
    return run_launcher_report_filter_options(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="fish_catalog",
        categories=resolved,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_wine_report_export(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    selected_product_ids: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    output_name: str = "pyaterochka_wine_report",
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher wine report export using KB-resolved categories."""
    resolved = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="wine_catalog",
        categories=categories,
    )
    return run_launcher_report_export(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=resolved,
        selected_product_ids=selected_product_ids,
        filters=filters,
        output_name=output_name,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_wine_report_filter_options(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run the launcher wine filter-options task using KB-resolved categories."""
    resolved = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="wine_catalog",
        categories=categories,
    )
    return run_launcher_report_filter_options(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=resolved,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def _resolve_report_categories(
    *,
    root_dir: Path,
    shop: str,
    intent: str,
    categories: list[str] | None,
) -> list[str]:
    """Keep report categories limited to explicit launcher selection."""
    del root_dir, shop, intent
    return [str(item).strip() for item in (categories or []) if str(item).strip()]
