"""Stateful desktop launcher controller over local task actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

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
from launcher.desktop_controller_favorites_mixin import DesktopControllerFavoritesMixin
from launcher.desktop_controller_reports import apply_filter_counts_from_export_json, load_filter_options, refresh_filter_counts_after_export, run_selected_report_export
from launcher.desktop_controller_profile import persist_launcher_profile_snapshot, save_current_profile_session
from launcher.desktop_controller_profile_load import list_profile_sessions as list_saved_profile_sessions, load_latest_profile_session as load_latest_profile_session_action, load_profile_session as load_profile_session_action
from launcher.desktop_controller_open import open_controller_path
from launcher.desktop_controller_selection import update_selection_state
from launcher.desktop_controller_task_state import launcher_task_status_from_manifest, mark_product_export_started
from launcher.desktop_controller_research import sync_research_state
from launcher.desktop_controller_workspace import sync_workspace_state
from launcher.desktop_project_workspace import (
    create_controller_workspace,
    ensure_controller_workspace,
    list_controller_workspace_profiles,
    rename_controller_workspace,
    select_controller_workspace,
)
from launcher.desktop_path_opener import open_path_with_system_handler
from launcher.desktop_store_identity import active_store_code
from launcher.desktop_workspace_reset import clear_product_workspace_for_research
from launcher.desktop_workspace_journal import record_task_completed_event, record_task_failed_event
from launcher.desktop_user_messages import (
    friendly_error_message,
    no_selected_categories_message,
    settings_saved_message,
    task_progress_message,
    task_running_message,
)
from models.launcher_state import LauncherFilterState
from utils.launcher_settings import LauncherSettingsStore
from utils.local_task_adapter import LocalTaskProcessResult, run_local_task_subprocess
TaskRunner = Callable[..., LocalTaskProcessResult]; PathOpener = Callable[[str], None]
class DesktopLauncherController(DesktopControllerFavoritesMixin):
    """Manage launcher state transitions and local task execution."""
    def __init__(
        self,
        *,
        root_dir: Path | str,
        settings_store: LauncherSettingsStore | None = None,
        onboarding_runner: TaskRunner | None = None,
        store_export_runner: TaskRunner | None = None,
        report_runner: TaskRunner | None = None,
        filter_options_runner: TaskRunner | None = None,
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
        self.store_export_runner = store_export_runner or fish_export_runner or wine_export_runner or task_controller.run_launcher_store_export
        self.report_runner = report_runner or fish_report_runner or wine_report_runner or task_controller.run_launcher_report_export
        self.filter_options_runner = filter_options_runner or fish_filter_options_runner or wine_filter_options_runner or task_controller.run_launcher_report_filter_options
        self.path_opener = path_opener or open_path_with_system_handler
        ensure_controller_workspace(self)
        self.hydrate_workspace_favorites()

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
        self.state.filters = LauncherFilterState().model_copy(update=filters)

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

    def run_cloak_runtime_install(self) -> LocalTaskProcessResult:
        """Explicit first-use Cloak provisioning independent of store selection."""
        def install_runner(*, root_dir: Path, timeout_seconds: int) -> LocalTaskProcessResult:
            return run_local_task_subprocess(
                task_name="cloak_runtime_install",
                task_input={},
                root_dir=root_dir,
                timeout_seconds=timeout_seconds,
            )

        return self._run_task(
            task_name="cloak_runtime_install",
            runner=install_runner,
            root_dir=self.root_dir,
            timeout_seconds=900,
        )

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
            browser_runtime=self.state.settings.browser_runtime,
            timeout_seconds=_research_timeout_seconds(
                self.state.settings.listen_seconds,
                manual_wait=self.state.settings.manual_wait,
                headless=self.state.settings.headless,
            ),
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
            "shop": active_store_code(self.state),
            "intent": self.state.selection.intent,
            "attempts": self.state.settings.attempts,
            "listen_seconds": self.state.settings.listen_seconds,
            "headless": self.state.settings.headless,
            "manual_wait": self.state.settings.manual_wait,
            "browser_runtime": self.state.settings.browser_runtime,
            "expand_intent": False,
            "timeout_seconds": _task_timeout_seconds(self.state.settings.listen_seconds),
        }
        self._start_task(task_name)
        mark_product_export_started(self.state, total_targets=len(targets))
        self.save_state()
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
            self.save_state()
            raise
        result = combine_export_results(results, categories, captured_payloads=captured_payloads)
        self._apply_result(result)
        refresh_filter_counts_after_export(self, categories)
        self.save_state()
        return result

    def run_selected_report_export(self) -> LocalTaskProcessResult:
        """Build the selected local Excel report from stored products."""
        return run_selected_report_export(self)
    def load_filter_options(self) -> LocalTaskProcessResult:
        """Load post-capture filter options for the current selection."""
        return load_filter_options(self)

    def load_latest_profile_session(self, *, shop: str = "", site_url: str = "") -> bool:
        loaded = load_latest_profile_session_action(self, shop=shop, site_url=site_url); self.save_state(); return loaded

    def load_profile_session(self, *, workspace_id: str = "", profile_id: str = "", version_id: str = "") -> bool:
        loaded = load_profile_session_action(self, workspace_id=workspace_id, profile_id=profile_id, version_id=version_id); self.save_state(); return loaded

    def list_profile_sessions(self, *, profile_id: str = "") -> list[dict[str, Any]]:
        return list_saved_profile_sessions(self, profile_id=profile_id)

    def save_profile_session(self) -> bool:
        saved = save_current_profile_session(self); self.save_state(); return saved

    def create_workspace(self, name: str) -> dict[str, Any]:
        workspace = create_controller_workspace(self, name); self.save_state(); return workspace

    def rename_workspace(self, workspace_id: str, name: str) -> dict[str, Any]:
        workspace = rename_controller_workspace(self, workspace_id, name); self.save_state(); return workspace

    def select_workspace(self, workspace_id: str) -> bool:
        selected = select_controller_workspace(self, workspace_id); self.save_state(); return selected

    def list_workspace_profiles(self) -> list[dict[str, str]]:
        return list_controller_workspace_profiles(self)

    def open_excel(self) -> bool:
        """Open the latest Excel artifact if it exists."""
        return open_controller_path(self, self.path_opener, self.state.result.excel_path)
    def open_report_dir(self) -> bool:
        """Open the latest report directory if it exists."""
        return open_controller_path(self, self.path_opener, self.state.result.report_dir)
    def open_json(self) -> bool:
        """Open the latest JSON artifact if it exists."""
        return open_controller_path(self, self.path_opener, self.state.result.json_path)
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
        self.state.task.last_error = friendly_error_message(error)
        record_task_failed_event(self)
        if self.state.task.task_name == "site_onboarding_discovery":
            self.state.research.current_status = "failed"

    def _apply_result(self, result: LocalTaskProcessResult) -> None:
        if result.manifest.task_name == "site_onboarding_discovery":
            self.state.result.excel_path = ""
            self.state.result.json_path = ""
            self.state.result.report_dir = ""
            self.state.result.launcher_view = reset_result_state_for_onboarding(self.state.result.launcher_view)
            self.state.selection.categories, self.state.selection.selected_catalog_nodes, self.state.selection.selected_product_ids = [], [], []
            self.state.selection.intent = str(result.manifest.intent or "").strip()
            clear_product_workspace_for_research(self.state)
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
        self.state.task.status = launcher_task_status_from_manifest(result.manifest.status)
        self.state.task.message = result_message(result)
        self.state.task.last_error = result.manifest.error
        selected = self.state.result.launcher_view.get("selected_categories")
        if result.manifest.task_name != "site_onboarding_discovery" and isinstance(selected, list) and selected:
            self.state.selection.categories = list(map(str, selected))
        phase_label = sync_research_state(self.state, result)
        if phase_label:
            self.state.task.message = f"{result_message(result)} Текущая фаза: {phase_label}"
        persist_launcher_profile_snapshot(self, result.manifest.task_name)
        record_task_completed_event(self, event_type=result.manifest.task_name)

    def _export_runner_and_task(self) -> tuple[TaskRunner, str]:
        return self.store_export_runner, "store_catalog_export"

def _task_timeout_seconds(listen_seconds: int) -> int: return max(900, int(listen_seconds) * 8 + 240)
def _research_timeout_seconds(
    listen_seconds: int,
    *,
    manual_wait: bool = False,
    headless: bool | str | None = None,
) -> int | None:
    del listen_seconds
    if manual_wait and headless in (False, "false", "False", "0"):
        return 900
    return 900
