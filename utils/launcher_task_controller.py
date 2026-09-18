"""Launcher-facing helpers for invoking local ParserRIba tasks."""

from __future__ import annotations

from pathlib import Path

from models.browser_runtime import BrowserRuntimeKind
from utils.launcher_report_task_controller import (
    run_launcher_fish_report_export,
    run_launcher_fish_report_filter_options,
    run_launcher_pyaterochka_report_export,
    run_launcher_pyaterochka_report_filter_options,
    run_launcher_report_export,
    run_launcher_report_filter_options,
    run_launcher_wine_report_export,
    run_launcher_wine_report_filter_options,
)
from utils.local_task_adapter import LocalTaskProcessResult, run_local_task_subprocess


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
    browser_runtime: str = "camoufox",
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int | None = 900,
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
            "browser_runtime": browser_runtime,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
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
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Compatibility alias for Pyaterochka fish catalog export."""
    return run_launcher_pyaterochka_export(
        intent="fish_catalog",
        root_dir=root_dir,
        category=category,
        category_url=category_url,
        attempts=attempts,
        listen_seconds=listen_seconds,
        headless=headless,
        manual_wait=manual_wait,
        expand_intent=expand_intent,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
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
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Compatibility alias for Pyaterochka wine catalog export."""
    return run_launcher_pyaterochka_export(
        intent="wine_catalog",
        root_dir=root_dir,
        category=category,
        category_url=category_url,
        attempts=attempts,
        listen_seconds=listen_seconds,
        headless=headless,
        manual_wait=manual_wait,
        expand_intent=expand_intent,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_pyaterochka_export(
    *,
    intent: str,
    root_dir: Path | str,
    category: str,
    category_url: str = "",
    attempts: int = 3,
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    expand_intent: bool = True,
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Compatibility helper for Pyaterochka catalog export with explicit intent."""
    return run_launcher_store_export(
        shop="pyaterochka",
        intent=intent,
        root_dir=root_dir,
        category=category,
        category_url=category_url,
        attempts=attempts,
        listen_seconds=listen_seconds,
        headless=headless,
        manual_wait=manual_wait,
        expand_intent=expand_intent,
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )


def run_launcher_store_export(
    *,
    shop: str,
    intent: str,
    root_dir: Path | str,
    category: str,
    category_url: str,
    attempts: int,
    listen_seconds: int,
    headless: bool | str | None,
    manual_wait: bool,
    expand_intent: bool,
    browser_runtime: BrowserRuntimeKind = "camoufox",
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int,
) -> LocalTaskProcessResult:
    """Run one profile-selected store export task through the local task adapter."""
    return run_local_task_subprocess(
        task_name="store_catalog_export",
        task_input={
            "shop": shop,
            "intent": intent,
            "category": category,
            "category_url": category_url,
            "attempts": attempts,
            "listen_seconds": listen_seconds,
            "headless": headless,
            "manual_wait": manual_wait,
            "browser_runtime": browser_runtime,
            "expand_intent": expand_intent,
        },
        root_dir=Path(root_dir),
        python_executable=python_executable,
        show_summary=show_summary,
        timeout_seconds=timeout_seconds,
    )
