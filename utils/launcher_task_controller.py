"""Launcher-facing helpers for invoking local ParserRIba tasks."""

from __future__ import annotations

from pathlib import Path

from utils.launcher_report_task_controller import (
    run_launcher_fish_report_export,
    run_launcher_fish_report_filter_options,
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
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
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
    """Run the launcher fish export task through the local task adapter."""
    return _run_category_export(
        task_name="pyaterochka_fish_export",
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
    """Run the launcher wine export task through the local task adapter."""
    return _run_category_export(
        task_name="pyaterochka_wine_export",
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


def _run_category_export(
    *,
    task_name: str,
    root_dir: Path | str,
    category: str,
    category_url: str,
    attempts: int,
    listen_seconds: int,
    headless: bool | str | None,
    manual_wait: bool,
    expand_intent: bool,
    python_executable: str | None,
    show_summary: bool,
    timeout_seconds: int,
) -> LocalTaskProcessResult:
    """Run one category export task through the local task adapter."""
    return run_local_task_subprocess(
        task_name=task_name,
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
        timeout_seconds=timeout_seconds,
    )
