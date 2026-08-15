"""Stateful desktop launcher controller over local task actions."""

from __future__ import annotations

import os
import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any, Callable, Mapping

from application.contracts import ApplicationContractError
from application.source_profile_catalog import inspect_declared_source_catalog
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
from models.task_actor import RunManifest
from utils.launcher_settings import LauncherSettingsStore
from utils.local_task_adapter import LocalTaskProcessResult
from utils.source_adapter_tasks import build_source_adapter_collection_request

TaskRunner = Callable[..., LocalTaskProcessResult]
PathOpener = Callable[[str], None]

_NON_INVALIDATING_SOURCE_COLLECTION_CODES = frozenset(
    {
        "SOURCE_COLLECTION_INPUT_INVALID",
        "COLLECTION_RUN_ID_ARTIFACT_INVALID",
        "COLLECTION_SCOPE_REQUIRED",
        "COLLECTION_SCOPE_INVALID",
        "COLLECTION_SCOPE_DUPLICATE",
    }
)


def _source_collection_failure_invalidates_catalog(error: Exception) -> bool:
    return not (
        isinstance(error, ApplicationContractError)
        and error.code in _NON_INVALIDATING_SOURCE_COLLECTION_CODES
    )


def _serialize_local_task_process_result(result: LocalTaskProcessResult) -> dict[str, Any]:
    payload = {
        field.name: getattr(result, field.name)
        for field in fields(LocalTaskProcessResult)
        if field.name != "manifest"
    }
    payload["manifest"] = result.manifest.model_dump(mode="json")
    return payload


def _deserialize_local_task_process_result(payload: Mapping[str, Any]) -> LocalTaskProcessResult:
    result_payload = dict(payload)
    manifest_payload = result_payload.pop("manifest", None)
    if not isinstance(manifest_payload, Mapping):
        raise ValueError("Source collection worker returned an invalid manifest payload.")
    return LocalTaskProcessResult(
        manifest=RunManifest(**dict(manifest_payload)),
        **result_payload,
    )


def _run_source_catalog_inspection_worker(
    *,
    source_profile_id: str,
    source_locator: str | None,
) -> dict[str, Any]:
    """Inspect one declared source without touching launcher or Qt state."""
    try:
        inspected = inspect_declared_source_catalog(source_profile_id, source_locator)
        nodes = [node.model_dump(mode="json") for node in inspected.catalog_nodes]
    except Exception as error:
        outcome = {
            "status": "failed",
            "error_code": error.code if isinstance(error, ApplicationContractError) else "",
            "error_message": str(error),
        }
        json.dumps(outcome, ensure_ascii=False)
        return outcome
    outcome = {
        "status": "finished",
        "source_profile_id": inspected.source_profile.source_profile_id,
        "source_locator": inspected.source_profile.source_locator,
        "source_nodes": nodes,
    }
    json.dumps(outcome, ensure_ascii=False)
    return outcome


def _run_source_adapter_collection_worker(
    *,
    runner: TaskRunner,
    root_dir: Path,
    timeout_seconds: int,
    collection_run_id: str,
    source_profile_id: str,
    catalog_node_ids: list[str],
    source_locator: str | None,
) -> dict[str, Any]:
    """Run source preflight/subprocess without touching launcher or Qt state."""
    task_input: dict[str, object] = {
        "collection_run_id": collection_run_id,
        "source_profile_id": source_profile_id,
        "catalog_node_ids": list(catalog_node_ids),
    }
    if source_locator is not None:
        task_input["source_locator"] = source_locator
    try:
        request = build_source_adapter_collection_request(task_input)
        task_input = {
            "collection_run_id": request.collection_run_id,
            "source_profile_id": request.source_profile.source_profile_id,
            "catalog_node_ids": [node.catalog_node_id for node in request.catalog_nodes],
        }
        if source_locator is not None:
            task_input["source_locator"] = request.source_profile.source_locator
    except Exception as error:
        outcome = {
            "status": "failed",
            "error_code": error.code if isinstance(error, ApplicationContractError) else "",
            "error_message": str(error),
            "invalidates_catalog": _source_collection_failure_invalidates_catalog(error),
        }
        json.dumps(outcome, ensure_ascii=False)
        return outcome
    try:
        result = runner(
            root_dir=root_dir,
            task_input=task_input,
            timeout_seconds=timeout_seconds,
        )
    except Exception as error:
        outcome = {
            "status": "failed",
            "error_code": error.code if isinstance(error, ApplicationContractError) else "",
            "error_message": str(error),
            "invalidates_catalog": True,
        }
        json.dumps(outcome, ensure_ascii=False)
        return outcome
    outcome = {
        "status": "finished",
        "result": _serialize_local_task_process_result(result),
        "invalidates_catalog": result.manifest.status == "failed",
    }
    json.dumps(outcome, ensure_ascii=False)
    return outcome

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

    def source_catalog_inspection_worker_action(
        self,
        source_profile_id: str,
        source_locator: str | None = None,
    ) -> Callable[[], dict[str, Any]]:
        """Freeze source inspection inputs for the state-neutral worker."""
        return lambda: _run_source_catalog_inspection_worker(
            source_profile_id=source_profile_id,
            source_locator=source_locator,
        )

    def begin_source_catalog_inspection(self, source_profile_id: str) -> None:
        """Prepare inspection state on the GUI/controller-owning thread."""
        self._start_task("source_catalog_inspection")
        self.clear_source_adapter_catalog(source_profile_id)
        self.state.task.task_kind = "source_catalog_inspection"
        self.state.task.phase = "validate_source_catalog"
        self.state.task.progress_total = 1

    def apply_source_catalog_inspection_worker_outcome(
        self,
        outcome: object,
        source_profile_id: str,
    ) -> list[dict[str, Any]] | None:
        """Apply one JSON-safe inspection outcome on the GUI/controller-owning thread."""
        if not isinstance(outcome, Mapping):
            error = ValueError("Source catalog worker returned an invalid outcome.")
            self.fail_source_catalog_inspection_worker(error, source_profile_id)
            raise error
        if outcome.get("status") == "failed":
            self.clear_source_adapter_catalog(source_profile_id)
            error_code = str(outcome.get("error_code") or "")
            error_message = str(outcome.get("error_message") or "Source catalog inspection failed.")
            error: Exception = (
                ApplicationContractError(error_code, error_message)
                if error_code
                else RuntimeError(error_message)
            )
            self._fail_task(error)
            self.save_state()
            return None
        raw_profile_id = outcome.get("source_profile_id")
        raw_locator = outcome.get("source_locator")
        raw_nodes = outcome.get("source_nodes")
        if (
            outcome.get("status") != "finished"
            or not isinstance(raw_profile_id, str)
            or not raw_profile_id
            or not isinstance(raw_locator, str)
            or not isinstance(raw_nodes, list)
            or any(not isinstance(node, Mapping) for node in raw_nodes)
        ):
            error = ValueError("Source catalog worker returned an invalid result.")
            self.fail_source_catalog_inspection_worker(error, source_profile_id)
            raise error
        nodes = [dict(node) for node in raw_nodes]
        self.state.catalog.source_profile_id = raw_profile_id
        self.state.catalog.source_locator = raw_locator
        self.state.catalog.source_nodes = nodes
        self.state.catalog.selected_source_node_ids = []
        self.state.task.status = "succeeded"
        self.state.task.progress_current = 1
        self.state.task.message = f"Каталог источника проверен: {len(nodes)} разделов."
        self.save_state()
        return nodes

    def fail_source_catalog_inspection_worker(
        self,
        error: object,
        source_profile_id: str,
    ) -> None:
        """Fail closed when inspection background transport cannot return an outcome."""
        self.clear_source_adapter_catalog(source_profile_id)
        if self.state.task.task_name != "source_catalog_inspection":
            self._start_task("source_catalog_inspection")
        exception = error if isinstance(error, Exception) else RuntimeError(str(error))
        self._fail_task(exception)
        self.save_state()

    def inspect_source_adapter_catalog(
        self,
        source_profile_id: str,
        source_locator: str | None = None,
    ) -> list[dict[str, Any]]:
        """Synchronous public seam using the same pure-worker and GUI-apply protocol."""
        action = self.source_catalog_inspection_worker_action(
            source_profile_id,
            source_locator,
        )
        self.begin_source_catalog_inspection(source_profile_id)
        outcome = action()
        nodes = self.apply_source_catalog_inspection_worker_outcome(
            outcome,
            source_profile_id,
        )
        if nodes is not None:
            return nodes
        if isinstance(outcome, Mapping) and outcome.get("error_code"):
            raise ApplicationContractError(
                str(outcome["error_code"]),
                str(outcome.get("error_message") or "Source catalog inspection failed."),
            )
        raise RuntimeError(
            str(outcome.get("error_message") or "Source catalog inspection failed.")
            if isinstance(outcome, Mapping)
            else "Source catalog inspection failed."
        )

    def clear_source_adapter_catalog(self, source_profile_id: str = "") -> None:
        """Clear inspected source nodes when the explicit SourceProfile changes."""
        self.state.catalog.source_profile_id = source_profile_id
        self.state.catalog.source_locator = ""
        self.state.catalog.source_nodes = []
        self.state.catalog.selected_source_node_ids = []

    def set_source_adapter_catalog_selection(self, catalog_node_ids: list[str]) -> None:
        """Persist checked source CatalogNodes after validating against inspected state."""
        available_ids = {
            str(node.get("catalog_node_id") or "")
            for node in self.state.catalog.source_nodes
            if isinstance(node, dict)
        }
        if (
            len(catalog_node_ids) != len(set(catalog_node_ids))
            or any(not node_id or node_id not in available_ids for node_id in catalog_node_ids)
        ):
            raise ValueError("SOURCE_CATALOG_SELECTION_INVALID: Select only visible unique CatalogNodes.")
        self.state.catalog.selected_source_node_ids = list(catalog_node_ids)

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

    def source_adapter_collection_worker_action(
        self,
        *,
        collection_run_id: str,
        source_profile_id: str,
        catalog_node_ids: list[str],
        source_locator: str | None = None,
    ) -> Callable[[], dict[str, Any]]:
        """Freeze worker inputs without exposing mutable launcher state to the worker."""
        runner = self.source_adapter_collection_runner
        root_dir = self.root_dir
        timeout_seconds = _task_timeout_seconds(self.state.settings.listen_seconds)
        selected_ids = list(catalog_node_ids)
        return lambda: _run_source_adapter_collection_worker(
            runner=runner,
            root_dir=root_dir,
            timeout_seconds=timeout_seconds,
            collection_run_id=collection_run_id,
            source_profile_id=source_profile_id,
            catalog_node_ids=selected_ids,
            source_locator=source_locator,
        )

    def begin_source_adapter_collection(self) -> None:
        """Mark source collection running on the GUI/controller-owning thread."""
        self._start_task("source_adapter_collection")

    def apply_source_adapter_collection_worker_outcome(
        self,
        outcome: object,
        source_profile_id: str,
    ) -> LocalTaskProcessResult | None:
        """Apply one JSON-safe worker outcome on the GUI/controller-owning thread."""
        if not isinstance(outcome, Mapping):
            error = ValueError("Source collection worker returned an invalid outcome.")
            self.fail_source_adapter_collection_worker(error, source_profile_id)
            raise error
        if outcome.get("status") == "failed":
            if bool(outcome.get("invalidates_catalog", True)):
                self.clear_source_adapter_catalog(source_profile_id)
            error = ValueError("Проверьте источник, разделы и идентификатор запуска.")
            self._fail_task(error)
            self.save_state()
            return None
        result_payload = outcome.get("result")
        if outcome.get("status") != "finished" or not isinstance(result_payload, Mapping):
            error = ValueError("Source collection worker returned an invalid result.")
            self.fail_source_adapter_collection_worker(error, source_profile_id)
            raise error
        try:
            result = _deserialize_local_task_process_result(result_payload)
            if bool(outcome.get("invalidates_catalog", result.manifest.status == "failed")):
                self.clear_source_adapter_catalog(source_profile_id)
            self._apply_result(result)
        except Exception as error:
            self.clear_source_adapter_catalog(source_profile_id)
            self._fail_task(error)
            self.save_state()
            raise
        self.save_state()
        return result

    def fail_source_adapter_collection_worker(
        self,
        error: object,
        source_profile_id: str,
    ) -> None:
        """Fail closed when the background transport itself cannot return an outcome."""
        self.clear_source_adapter_catalog(source_profile_id)
        if self.state.task.task_name != "source_adapter_collection":
            self._start_task("source_adapter_collection")
        exception = error if isinstance(error, Exception) else RuntimeError(str(error))
        self._fail_task(exception)
        self.save_state()

    def run_source_adapter_collection(
        self,
        *,
        collection_run_id: str,
        source_profile_id: str,
        catalog_node_ids: list[str],
        source_locator: str | None = None,
    ) -> LocalTaskProcessResult:
        """Synchronous public seam using the same pure-worker and GUI-apply protocol."""
        action = self.source_adapter_collection_worker_action(
            collection_run_id=collection_run_id,
            source_profile_id=source_profile_id,
            catalog_node_ids=catalog_node_ids,
            source_locator=source_locator,
        )
        self.begin_source_adapter_collection()
        result = self.apply_source_adapter_collection_worker_outcome(
            action(),
            source_profile_id,
        )
        if result is None:
            raise ValueError("Проверьте источник, разделы и идентификатор запуска.")
        return result

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
