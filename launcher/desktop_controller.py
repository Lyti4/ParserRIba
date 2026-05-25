"""Stateful desktop launcher controller over local task actions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from launcher.desktop_controller_helpers import (
    artifact_or_existing,
    capture_export_payload,
    combine_export_results,
    discovered_category_names,
    has_rich_filter_counts,
    merge_launcher_view,
    report_dir_from_artifacts,
    reset_result_state_for_onboarding,
    result_message,
    selected_export_targets,
)
from launcher.desktop_controller_selection import update_selection_state
from launcher.desktop_controller_research import sync_research_state
from launcher.desktop_export_facets import build_available_filter_counts_from_export_json
from launcher.desktop_user_messages import (
    empty_filter_options_message,
    friendly_error_message,
    no_selected_categories_message,
    no_output_path_message,
    opened_path_message,
    settings_saved_message,
    task_progress_message,
    task_running_message,
)
from utils.launcher_settings import LauncherSettingsStore
from utils.local_task_adapter import LocalTaskProcessResult

TaskRunner = Callable[..., LocalTaskProcessResult]
PathOpener = Callable[[str], None]

class DesktopLauncherController:
    """Manage launcher state transitions and local task execution."""

    def __init__(
        self,
        *,
        root_dir: Path | str,
        settings_store: LauncherSettingsStore | None = None,
        onboarding_runner: TaskRunner | None = None,
        fish_export_runner: TaskRunner | None = None,
        wine_export_runner: TaskRunner | None = None,
        fish_report_runner: TaskRunner | None = None,
        wine_report_runner: TaskRunner | None = None,
        fish_filter_options_runner: TaskRunner | None = None,
        wine_filter_options_runner: TaskRunner | None = None,
        path_opener: PathOpener | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.settings_store = settings_store or LauncherSettingsStore(
            self.root_dir / "data" / "launcher_settings.json"
        )
        self.state = self.settings_store.load_app_state()
        from utils import launcher_task_controller as task_controller

        self.onboarding_runner = onboarding_runner or task_controller.run_launcher_onboarding_discovery
        self.fish_export_runner = fish_export_runner or task_controller.run_launcher_fish_export
        self.wine_export_runner = wine_export_runner or task_controller.run_launcher_wine_export
        self.fish_report_runner = fish_report_runner or task_controller.run_launcher_fish_report_export
        self.wine_report_runner = wine_report_runner or task_controller.run_launcher_wine_report_export
        self.fish_filter_options_runner = (
            fish_filter_options_runner or task_controller.run_launcher_fish_report_filter_options
        )
        self.wine_filter_options_runner = (
            wine_filter_options_runner or task_controller.run_launcher_wine_report_filter_options
        )
        self.path_opener = path_opener or open_path_with_system_handler

    def set_selection(
        self,
        *,
        shop: str | None = None,
        intent: str | None = None,
        categories: list[str] | None = None,
        selected_catalog_nodes: list[dict[str, Any]] | None = None, selected_product_ids: list[str] | None = None,
    ) -> None:
        """Update current launcher selection state."""
        update_selection_state(
            self.state.selection,
            shop=shop,
            intent=intent,
            categories=categories,
            selected_catalog_nodes=selected_catalog_nodes,
            selected_product_ids=selected_product_ids,
        )

    def set_filters(self, filters: dict[str, Any]) -> None:
        """Replace current filter state from a plain mapping."""
        self.state.filters = self.state.filters.model_copy(update=filters)

    def set_settings(self, settings: dict[str, Any]) -> None:
        """Replace launcher settings from a plain mapping."""
        self.state.settings = self.state.settings.model_copy(update=settings)

    def save_state(self) -> Path:
        """Persist the current launcher app state."""
        return self.settings_store.save_app_state(self.state)

    def save_settings(self) -> Path:
        """Persist launcher settings and surface one user-facing message."""
        settings_path = self.save_state()
        self.state.task.message = settings_saved_message()
        return settings_path

    def list_available_categories(self) -> list[str]:
        """Return discovered categories for the currently researched target only."""
        view = self.state.result.launcher_view
        if view.get("shop") != self.state.selection.shop or view.get("intent") != self.state.selection.intent:
            return []
        return discovered_category_names(view)

    def run_onboarding_discovery(self, *, site_url: str) -> LocalTaskProcessResult:
        """Run onboarding discovery for a site URL."""
        return self._run_task(
            task_name="site_onboarding_discovery",
            runner=self.onboarding_runner,
            site_url=site_url,
            root_dir=self.root_dir,
            intent=self.state.selection.intent,
            selected_categories=[],
            headless=self.state.settings.headless,
            manual_wait=self.state.settings.manual_wait,
            listen_seconds=self.state.settings.listen_seconds,
            research_mode=self.state.research.mode,
            timeout_seconds=_task_timeout_seconds(self.state.settings.listen_seconds),
        )

    def run_selected_export(self) -> LocalTaskProcessResult:
        """Run the selected live export for every chosen launcher category."""
        runner, task_name = self._export_runner_and_task()
        targets = selected_export_targets(
            self.state.selection.categories,
            self.state.selection.selected_catalog_nodes,
            self.state.selection.intent,
        )
        categories = [target["name"] for target in targets]
        if not targets:
            self._start_task(task_name)
            error = ValueError(no_selected_categories_message())
            self._fail_task(error)
            self.save_state()
            raise error
        common = {
            "root_dir": self.root_dir,
            "attempts": self.state.settings.attempts,
            "listen_seconds": self.state.settings.listen_seconds,
            "headless": self.state.settings.headless,
            "manual_wait": self.state.settings.manual_wait,
            "expand_intent": False,
            "timeout_seconds": _task_timeout_seconds(self.state.settings.listen_seconds),
        }
        self._start_task(task_name)
        results: list[LocalTaskProcessResult] = []
        captured_payloads: list[dict[str, Any]] = []
        try:
            for index, target in enumerate(targets, start=1):
                category_name = target["name"]
                self.state.task.message = task_progress_message(task_name, category_name, index, len(categories))
                result = runner(category=category_name, category_url=target.get("url", ""), **common)
                results.append(result)
                payload = capture_export_payload(result)
                if payload is not None:
                    captured_payloads.append(payload)
        except Exception as error:
            self._fail_task(error)
            raise
        result = combine_export_results(results, categories, captured_payloads=captured_payloads)
        self._apply_result(result)
        self._refresh_filter_counts_after_export(categories)
        self.save_state()
        return result

    def run_selected_report_export(self) -> LocalTaskProcessResult:
        """Build the selected local Excel report from stored products."""
        runner = self.wine_report_runner if self.state.selection.intent == "wine_catalog" else self.fish_report_runner
        output_name = "pyaterochka_wine_report" if self.state.selection.intent == "wine_catalog" else "pyaterochka_fish_report"
        return self._run_task(
            task_name="store_report_export",
            runner=runner,
            root_dir=self.root_dir,
            categories=self.state.selection.categories,
            selected_product_ids=self.state.selection.selected_product_ids,
            filters=self.state.filters.model_dump(mode="json"),
            output_name=output_name,
            timeout_seconds=120,
        )

    def load_filter_options(self) -> LocalTaskProcessResult:
        """Load post-capture filter options for the current selection."""
        runner = self.wine_filter_options_runner if self.state.selection.intent == "wine_catalog" else self.fish_filter_options_runner
        result = self._run_task(
            task_name="store_report_filter_options",
            runner=runner,
            root_dir=self.root_dir,
            categories=self.state.selection.categories,
            timeout_seconds=120,
        )
        if not has_rich_filter_counts(self.state.result.launcher_view.get("available_filter_counts")):
            self.state.task.message = empty_filter_options_message()
            self.save_state()
        return result

    def open_excel(self) -> bool:
        """Open the latest Excel artifact if it exists."""
        return self._open_path(self.state.result.excel_path)
    def open_report_dir(self) -> bool:
        """Open the latest report directory if it exists."""
        return self._open_path(self.state.result.report_dir)
    def open_json(self) -> bool:
        """Open the latest JSON artifact if it exists."""
        return self._open_path(self.state.result.json_path)

    def _run_task(self, *, task_name: str, runner: TaskRunner, **kwargs: Any) -> LocalTaskProcessResult:
        self._start_task(task_name)
        try:
            result = runner(**kwargs)
        except Exception as error:
            self._fail_task(error)
            self.save_state()
            raise
        self._apply_result(result)
        self.save_state()
        return result

    def _start_task(self, task_name: str) -> None:
        self.state.task.status = "running"
        self.state.task.task_name = task_name
        self.state.task.message = task_running_message(task_name)
        self.state.task.last_error = ""
        if task_name == "site_onboarding_discovery":
            self.state.research.current_status = "running"
            self.state.research.current_phase = "open_site"
            self.state.research.streamed_categories = []

    def _fail_task(self, error: Exception) -> None:
        self.state.task.status = "failed"
        self.state.task.message = friendly_error_message(error)
        self.state.task.last_error = str(error)
        if self.state.task.task_name == "site_onboarding_discovery":
            self.state.research.current_status = "failed"

    def _apply_result(self, result: LocalTaskProcessResult) -> None:
        if result.manifest.task_name == "site_onboarding_discovery":
            self.state.result.excel_path = ""
            self.state.result.json_path = ""
            self.state.result.report_dir = ""
            self.state.result.launcher_view = reset_result_state_for_onboarding(self.state.result.launcher_view)
            self.state.selection.categories = []
            self.state.selection.selected_catalog_nodes = []
            self.state.selection.selected_product_ids = []
        artifacts = dict(result.manifest.artifact_paths or {})
        self.state.result.launcher_view = merge_launcher_view(
            dict(self.state.result.launcher_view),
            dict(result.launcher_view or {}),
        )
        self.state.result.excel_path = artifact_or_existing(artifacts.get("excel_path"), self.state.result.excel_path)
        self.state.result.json_path = artifact_or_existing(artifacts.get("json_path"), self.state.result.json_path)
        self.state.result.report_dir = report_dir_from_artifacts(artifacts, existing_report_dir=self.state.result.report_dir)
        filter_counts = build_available_filter_counts_from_export_json(self.state.result.json_path)
        if filter_counts:
            found_filters = filter_counts.pop("found_filters", {})
            self.state.result.launcher_view["available_filter_counts"] = filter_counts
            if found_filters:
                self.state.result.launcher_view["found_filters"] = found_filters
        self.state.task.status = "succeeded" if result.manifest.status != "failed" else "failed"
        self.state.task.message = result_message(result)
        self.state.task.last_error = result.manifest.error
        selected = self.state.result.launcher_view.get("selected_categories")
        if result.manifest.task_name != "site_onboarding_discovery" and isinstance(selected, list) and selected:
            self.state.selection.categories = [str(item) for item in selected]
        phase_label = sync_research_state(self.state, result)
        if phase_label:
            self.state.task.message = f"{result_message(result)} Текущая фаза: {phase_label}"

    def _export_runner_and_task(self) -> tuple[TaskRunner, str]:
        return (
            (self.wine_export_runner, "pyaterochka_wine_export")
            if self.state.selection.intent == "wine_catalog"
            else (self.fish_export_runner, "pyaterochka_fish_export")
        )

    def _refresh_filter_counts_after_export(self, categories: list[str]) -> None:
        runner = self.wine_filter_options_runner if self.state.selection.intent == "wine_catalog" else self.fish_filter_options_runner
        try:
            filter_result = runner(root_dir=self.root_dir, categories=categories, timeout_seconds=120)
        except Exception:
            return
        counts = dict(filter_result.available_filter_counts or {})
        if counts:
            found_filters = counts.pop("found_filters", {})
            self.state.result.launcher_view["available_filter_counts"] = counts
            if found_filters:
                self.state.result.launcher_view["found_filters"] = found_filters

    def _open_path(self, path_value: str) -> bool:
        path = str(path_value or "").strip()
        if not path:
            self.state.task.message = no_output_path_message()
            return False
        try:
            self.path_opener(path)
        except OSError as error:
            self.state.task.message = friendly_error_message(error)
            self.state.task.last_error = str(error)
            return False
        self.state.task.message = opened_path_message(path)
        self.state.task.last_error = ""
        return True


def open_path_with_system_handler(path: str) -> None:
    """Open a local path with the platform default application."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    command = ["open", path] if sys.platform == "darwin" else ["xdg-open", path]
    subprocess.Popen(command)


def _task_timeout_seconds(listen_seconds: int) -> int:
    """Return a bounded subprocess timeout derived from launcher wait settings."""
    return max(180, int(listen_seconds) + 120)
