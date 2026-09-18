"""Load StoreProfile snapshots back into launcher state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.launcher_state import (
    LauncherCatalogState,
    LauncherDynamicFilterState,
    LauncherFilterState,
    LauncherProductWorkspaceState,
    LauncherProfileState,
    LauncherReportState,
    LauncherSelectionState,
)
from launcher.desktop_workspace_journal import record_workspace_journal_event
from utils.store_profile_repository import StoreProfileRepository

PROFILE_SESSION_LOADED_MESSAGE = "Загружена последняя сохранённая сессия профиля."
PROFILE_SESSION_NOT_FOUND_MESSAGE = (
    "Сохранённая сессия профиля не найдена. Сначала выполните исследование или сбор товаров."
)


def list_profile_sessions(controller: Any, *, profile_id: str = "") -> list[dict[str, Any]]:
    """List saved sessions for the active workspace/profile."""
    lookup_profile_id = str(profile_id or controller.state.profile.profile_id).strip()
    if not lookup_profile_id:
        return []
    workspace_id = str(controller.state.workspace.workspace_id or "default").strip() or "default"
    return StoreProfileRepository(_profile_db_path(controller.root_dir)).list_profile_versions(
        workspace_id=workspace_id,
        profile_id=lookup_profile_id,
    )


def load_profile_session(
    controller: Any,
    *,
    workspace_id: str = "",
    profile_id: str = "",
    version_id: str = "",
) -> bool:
    """Load one persisted StoreProfile session into the controller state."""
    lookup_workspace_id = str(workspace_id or controller.state.workspace.workspace_id or "default").strip() or "default"
    lookup_profile_id = str(profile_id or controller.state.profile.profile_id).strip()
    lookup_version_id = str(version_id or controller.state.profile.profile_version_id).strip()
    if not lookup_profile_id or not lookup_version_id:
        _mark_profile_load_missing(controller)
        return False
    db_path = _profile_db_path(controller.root_dir)
    payload = StoreProfileRepository(db_path).get_profile_version(
        workspace_id=lookup_workspace_id,
        profile_id=lookup_profile_id,
        version_id=lookup_version_id,
    )
    if payload is None:
        _mark_profile_load_missing(controller)
        return False
    _apply_profile_payload(controller, payload, db_path)
    return True


def load_latest_profile_session(controller: Any, *, shop: str = "", site_url: str = "") -> bool:
    """Load the latest persisted StoreProfile session into the controller state."""
    lookup_shop = str(shop or controller.state.selection.shop or controller.state.profile.shop).strip()
    lookup_url = str(site_url or controller.state.profile.site_url).strip()
    db_path = _profile_db_path(controller.root_dir)
    payload = StoreProfileRepository(db_path).get_latest_profile_by_site(lookup_shop, lookup_url)
    if payload is None:
        _mark_profile_load_missing(controller)
        return False
    _apply_profile_payload(controller, payload, db_path)
    return True


def _profile_db_path(root_dir: Path) -> Path:
    return Path(root_dir) / "data" / "profiles" / "store_profiles.db"


def _mark_profile_load_missing(controller: Any) -> None:
    state = controller.state
    state.task.status = "failed"
    state.task.task_name = "load_profile_session"
    state.task.task_kind = "profile"
    state.task.phase = "profile_not_found"
    state.task.message = PROFILE_SESSION_NOT_FOUND_MESSAGE
    state.task.last_error = PROFILE_SESSION_NOT_FOUND_MESSAGE
    record_workspace_journal_event(
        controller,
        event_type="profile_session_load_failed",
        title="Сессия профиля не найдена",
        message=PROFILE_SESSION_NOT_FOUND_MESSAGE,
        status="failed",
    )


def _apply_profile_payload(controller: Any, payload: dict[str, Any], db_path: Path) -> None:
    state = controller.state
    profile = LauncherProfileState.model_validate(payload.get("profile") or {})
    catalog = LauncherCatalogState.model_validate(payload.get("catalog") or {})
    products = LauncherProductWorkspaceState.model_validate(payload.get("products") or {})
    dynamic_filters = LauncherDynamicFilterState.model_validate(payload.get("dynamic_filters") or {})
    filters = LauncherFilterState.model_validate(payload.get("filters") or {})
    report = LauncherReportState.model_validate(payload.get("report") or {})
    selection = LauncherSelectionState.model_validate(payload.get("selection") or {})
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}

    state.profile = profile
    state.catalog = catalog
    state.products = products
    state.dynamic_filters = dynamic_filters
    state.filters = filters
    state.report = report
    state.selection = selection
    _restore_result_state(state, result, db_path)
    _mark_profile_load_success(state)
    record_workspace_journal_event(
        controller,
        event_type="profile_session_loaded",
        title="Сессия профиля загружена",
        message=PROFILE_SESSION_LOADED_MESSAGE,
        status="succeeded",
    )


def _restore_result_state(state: Any, result: dict[str, Any], db_path: Path) -> None:
    artifact_paths = dict(result.get("artifact_paths") or {})
    artifact_paths["store_profile_db_path"] = str(db_path)
    state.result.summary = dict(result.get("summary") or {})
    state.result.artifact_paths = {
        str(key): str(value)
        for key, value in artifact_paths.items()
        if value is not None
    }
    state.result.products_count = int(result.get("products_count") or state.products.products_count or len(state.products.items))
    state.result.source_profile_id = str(result.get("source_profile_id") or state.profile.profile_id or "")
    state.result.filter_snapshot = dict(result.get("filter_snapshot") or {})
    state.result.excel_path = str(
        artifact_paths.get("excel_path")
        or state.products.excel_path
        or state.result.excel_path
        or ""
    )
    state.result.json_path = str(
        artifact_paths.get("json_path")
        or state.products.json_path
        or state.result.json_path
        or ""
    )
    state.result.report_dir = str(artifact_paths.get("report_dir") or state.result.report_dir or "")
    state.profile.diagnostics["store_profile_db_path"] = str(db_path)


def _mark_profile_load_success(state: Any) -> None:
    state.task.status = "succeeded"
    state.task.task_name = "load_profile_session"
    state.task.task_kind = "profile"
    state.task.phase = "loaded_profile_session"
    state.task.progress_current = 1
    state.task.progress_total = 1
    state.task.message = PROFILE_SESSION_LOADED_MESSAGE
    state.task.last_error = ""
    state.research.active_profile_id = state.profile.profile_id
    state.research.active_profile_version_id = state.profile.profile_version_id
