"""Launcher-facing helpers for invoking local ParserRIba tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.local_task_adapter import LocalTaskProcessResult, run_local_task_subprocess
from utils.kb_loader import KBLoader
from utils.store_catalog_registry import get_store_export_backend


def run_launcher_onboarding_discovery(
    *,
    site_url: str,
    root_dir: Path | str,
    intent: str = "fish_catalog",
    require_operator_confirmation: bool = False,
    selected_categories: list[str] | None = None,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
    research_mode: str = "live",
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run the launcher onboarding discovery task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="site_onboarding_discovery",
        task_input={
            "site_url": site_url,
            "intent": intent,
            "require_operator_confirmation": require_operator_confirmation,
            "selected_categories": list(selected_categories or []),
            "headless": headless,
            "manual_wait": manual_wait,
            "listen_seconds": listen_seconds,
            "research_mode": research_mode,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
    )


def run_launcher_fish_export(
    *,
    root_dir: Path | str,
    category: str = "Рыба",
    category_url: str = "",
    attempts: int = 3,
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    expand_intent: bool = True,
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run the launcher fish export task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="pyaterochka_fish_export",
        task_input={
            "category": category,
            "category_url": category_url,
            "attempts": attempts,
            "listen_seconds": listen_seconds,
            "headless": headless,
            "manual_wait": manual_wait,
            "expand_intent": expand_intent,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
    )


def run_launcher_wine_export(
    *,
    root_dir: Path | str,
    category: str = "Вино",
    category_url: str = "",
    attempts: int = 3,
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    expand_intent: bool = True,
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run the launcher wine export task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="pyaterochka_wine_export",
        task_input={
            "category": category,
            "category_url": category_url,
            "attempts": attempts,
            "listen_seconds": listen_seconds,
            "headless": headless,
            "manual_wait": manual_wait,
            "expand_intent": expand_intent,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
    )


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
    )


def run_launcher_report_filter_options(
    *,
    root_dir: Path | str,
    shop: str,
    intent: str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
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
) -> LocalTaskProcessResult:
    """Run the launcher fish report export using KB-resolved categories."""
    resolved_categories = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="fish_catalog",
        categories=categories,
    )
    return run_launcher_report_export(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="fish_catalog",
        categories=resolved_categories,
        selected_product_ids=selected_product_ids,
        filters=filters,
        output_name=output_name,
        python_executable=python_executable,
        show_summary=show_summary,
    )


def run_launcher_fish_report_filter_options(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run the launcher fish filter-options task using KB-resolved categories."""
    resolved_categories = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="fish_catalog",
        categories=categories,
    )
    return run_launcher_report_filter_options(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="fish_catalog",
        categories=resolved_categories,
        python_executable=python_executable,
        show_summary=show_summary,
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
) -> LocalTaskProcessResult:
    """Run the launcher wine report export using KB-resolved categories."""
    resolved_categories = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="wine_catalog",
        categories=categories,
    )
    return run_launcher_report_export(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=resolved_categories,
        selected_product_ids=selected_product_ids,
        filters=filters,
        output_name=output_name,
        python_executable=python_executable,
        show_summary=show_summary,
    )


def run_launcher_wine_report_filter_options(
    *,
    root_dir: Path | str,
    categories: list[str] | None = None,
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run the launcher wine filter-options task using KB-resolved categories."""
    resolved_categories = _resolve_report_categories(
        root_dir=Path(root_dir),
        shop="pyaterochka",
        intent="wine_catalog",
        categories=categories,
    )
    return run_launcher_report_filter_options(
        root_dir=root_dir,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=resolved_categories,
        python_executable=python_executable,
        show_summary=show_summary,
    )


def _resolve_report_categories(
    *,
    root_dir: Path,
    shop: str,
    intent: str,
    categories: list[str] | None,
) -> list[str]:
    """Resolve launcher report categories through the store backend contract."""
    explicit_categories = [str(item).strip() for item in (categories or []) if str(item).strip()]
    if explicit_categories:
        return explicit_categories

    backend = get_store_export_backend(shop, intent)
    kb_dir = root_dir / "knowledge_base"
    if not kb_dir.exists():
        return backend.resolve_categories(backend.default_category, None)
    kb = KBLoader(str(kb_dir)).load_shop(shop)
    return backend.resolve_categories(backend.default_category, kb.categories)
