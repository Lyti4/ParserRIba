"""Stateful desktop launcher controller over local task actions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from application.contracts import ApplicationContractError
from application.url_safety import is_explicit_http_url
from launcher.desktop_controller_helpers import (
    artifact_or_existing,
    available_category_names,
    capture_export_payload,
    combine_export_results,
    merge_launcher_view,
    report_dir_from_artifacts,
    reset_result_state_for_onboarding,
    result_message,
    selected_export_targets,
)
from launcher.desktop_controller_reports import apply_filter_counts_from_export_json, load_filter_options, refresh_filter_counts_after_export, run_selected_report_export
from launcher.desktop_controller_profile import persist_launcher_profile_snapshot
from launcher.desktop_controller_selection import update_selection_state
from launcher.desktop_controller_research import sync_research_state
from launcher.desktop_controller_workspace import sync_workspace_state
from launcher.desktop_workspace_export import (
    write_filtered_workspace_export,
    write_selected_workspace_export,
    write_whole_workspace_export,
)
from launcher.desktop_user_messages import (
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
from utils.source_adapter_tasks import build_source_adapter_collection_request

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
        source_adapter_collection_runner: TaskRunner | None = None,
        pyaterochka_fixture_runner: TaskRunner | None = None,
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
        self.source_adapter_collection_runner = (
            source_adapter_collection_runner or task_controller.run_launcher_source_adapter_collection
        )
        self.pyaterochka_fixture_runner = (
            pyaterochka_fixture_runner or task_controller.run_launcher_pyaterochka_application_fixture
        )
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
        return available_category_names(self.state)

    def run_onboarding_discovery(self, *, site_url: str) -> LocalTaskProcessResult:
        """Run onboarding discovery for one explicit HTTP(S) site URL."""
        if not is_explicit_http_url(site_url):
            raise ValueError(
                "ONBOARDING_URL_INVALID: An explicit absolute HTTP(S) onboarding URL is required."
            )
        site_url = site_url.strip()
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
        self.state.task.task_kind = "product_export"
        self.state.task.phase = "collect_products"
        self.state.task.progress_total = len(targets)
        results: list[LocalTaskProcessResult] = []
        captured_payloads: list[dict[str, Any]] = []
        try:
            for index, target in enumerate(targets, start=1):
                category_name = target["name"]
                self.state.task.progress_current = index
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
        refresh_filter_counts_after_export(self, categories)
        self.save_state()
        return result

    def run_source_adapter_collection(
        self,
        *,
        collection_run_id: str,
        source_profile_id: str,
        catalog_node_ids: list[str],
        source_locator: str | None = None,
    ) -> LocalTaskProcessResult:
        """Collect one explicit SourceProfile through the registered source-adapter task."""
        task_input: dict[str, object] = {
            "collection_run_id": collection_run_id,
            "source_profile_id": source_profile_id,
            "catalog_node_ids": catalog_node_ids,
        }
        if source_locator is not None:
            task_input["source_locator"] = source_locator
        try:
            request = build_source_adapter_collection_request(task_input)
        except ApplicationContractError:
            self._start_task("source_adapter_collection")
            error = ValueError("Проверьте источник, разделы и идентификатор запуска.")
            self._fail_task(error)
            raise error from None
        task_input = {
            "collection_run_id": request.collection_run_id,
            "source_profile_id": request.source_profile.source_profile_id,
            "catalog_node_ids": [node.catalog_node_id for node in request.catalog_nodes],
        }
        if source_locator is not None:
            task_input["source_locator"] = request.source_profile.source_locator
        return self._run_task(
            task_name="source_adapter_collection",
            runner=self.source_adapter_collection_runner,
            root_dir=self.root_dir,
            task_input=task_input,
            timeout_seconds=_task_timeout_seconds(self.state.settings.listen_seconds),
        )

    def export_selected_workspace_products(
        self,
        output_path: Path,
        *,
        include_provenance: bool = False,
    ) -> Path:
        """Write exactly the selected source-neutral workspace products."""
        return self._write_workspace_export(
            write_selected_workspace_export,
            output_path,
            include_provenance=include_provenance,
        )

    def export_filtered_workspace(
        self,
        output_path: Path,
        *,
        include_provenance: bool = False,
    ) -> Path:
        """Write the explicit generic-facet workspace selection."""
        return self._write_workspace_export(
            write_filtered_workspace_export,
            output_path,
            include_provenance=include_provenance,
        )

    def export_whole_workspace(
        self,
        output_path: Path,
        *,
        include_provenance: bool = False,
    ) -> Path:
        """Write the whole workspace only through this explicit action."""
        return self._write_workspace_export(
            write_whole_workspace_export,
            output_path,
            include_provenance=include_provenance,
        )

    def _write_workspace_export(
        self,
        writer: Callable[..., Path],
        output_path: Path,
        *,
        include_provenance: bool,
    ) -> Path:
        self._start_task("workspace_export")
        self.state.task.task_kind = "workspace_export"
        self.state.task.phase = "write_local_json"
        self.state.task.progress_total = 1
        try:
            written_path = writer(
                self.state,
                output_path,
                include_provenance=include_provenance,
            )
        except Exception as error:
            self._fail_task(error)
            self.save_state()
            raise
        self.state.task.status = "succeeded"
        self.state.task.progress_current = 1
        self.state.task.message = f"Экспорт рабочей области сохранён: {written_path}"
        self.state.result.json_path = str(written_path)
        self.state.result.artifact_paths["workspace_export_json"] = str(written_path)
        self.save_state()
        return written_path

    def run_pyaterochka_fixture_collection(self, *, catalog_node_ids: list[str]) -> LocalTaskProcessResult:
        """Collect explicit deterministic Pyaterochka fixture nodes into the product workspace."""
        invalid_selection = (
            not catalog_node_ids
            or any(
                not isinstance(node_id, str)
                or not node_id
                or node_id != node_id.strip()
                for node_id in catalog_node_ids
            )
            or len(set(catalog_node_ids)) != len(catalog_node_ids)
        )
        if invalid_selection:
            self._start_task("pyaterochka_application_fixture")
            error = ValueError("Выберите хотя бы один уникальный непустой fixture-раздел Пятёрочки.")
            self._fail_task(error)
            self.save_state()
            raise error
        selected_ids = list(catalog_node_ids)
        return self._run_task(
            task_name="pyaterochka_application_fixture",
            runner=self.pyaterochka_fixture_runner,
            root_dir=self.root_dir,
            task_input={"catalog_node_ids": selected_ids},
            timeout_seconds=_task_timeout_seconds(self.state.settings.listen_seconds),
        )

    def run_selected_report_export(self) -> LocalTaskProcessResult:
        """Build the selected local Excel report from stored products."""
        return run_selected_report_export(self)

    def load_filter_options(self) -> LocalTaskProcessResult:
        """Load post-capture filter options for the current selection."""
        return load_filter_options(self)

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
            self._apply_result(result)
        except Exception as error:
            self._fail_task(error)
            self.save_state()
            raise
        self.save_state()
        return result

    def _start_task(self, task_name: str) -> None:
        self.state.task.status = "running"
        self.state.task.task_name = task_name
        self.state.task.task_kind = ""
        self.state.task.phase = ""
        self.state.task.progress_current = 0
        self.state.task.progress_total = 0
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
        apply_filter_counts_from_export_json(self)
        sync_workspace_state(self.state, result)
        from application.lifecycle import launcher_status_for_manifest

        self.state.task.status = launcher_status_for_manifest(result.manifest)
        self.state.task.message = result_message(result)
        self.state.task.last_error = result.manifest.error
        selected = self.state.result.launcher_view.get("selected_categories")
        if result.manifest.task_name != "site_onboarding_discovery" and isinstance(selected, list) and selected:
            self.state.selection.categories = [str(item) for item in selected]
        phase_label = sync_research_state(self.state, result)
        if phase_label:
            self.state.task.message = f"{result_message(result)} Текущая фаза: {phase_label}"
        persist_launcher_profile_snapshot(self, result.manifest.task_name)

    def _export_runner_and_task(self) -> tuple[TaskRunner, str]:
        intent = self.state.selection.intent.strip()
        if intent == "fish_catalog":
            return self.fish_export_runner, "pyaterochka_fish_export"
        if intent == "wine_catalog":
            return self.wine_export_runner, "pyaterochka_wine_export"
        raise ValueError("Выберите явный тип экспорта перед запуском.")

    def _open_path(self, path_value: str) -> bool:
        path = str(path_value or "").strip()
        if not path:
            self.state.task.message = no_output_path_message()
            return False
        try:
            local_path = _absolute_local_path(path)
            self.path_opener(local_path)
        except (OSError, ValueError) as error:
            self.state.task.message = friendly_error_message(error)
            self.state.task.last_error = str(error)
            return False
        self.state.task.message = opened_path_message(local_path)
        self.state.task.last_error = ""
        return True


def _absolute_local_path(path: str) -> str:
    candidate = Path(str(path or "")).expanduser()
    if not candidate.is_absolute():
        raise ValueError("Artifact path must be an absolute local path.")
    return str(candidate)


def open_path_with_system_handler(path: str) -> None:
    """Open one validated local filesystem path with the platform default application."""
    local_path = _absolute_local_path(path)
    if sys.platform == "win32":
        os.startfile(local_path)  # type: ignore[attr-defined]
        return
    command = ["open", local_path] if sys.platform == "darwin" else ["xdg-open", local_path]
    subprocess.Popen(command)


def _task_timeout_seconds(listen_seconds: int) -> int:
    """Return a bounded subprocess timeout derived from launcher wait settings."""
    return max(180, int(listen_seconds) + 120)
