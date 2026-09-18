"""Profile snapshot helpers for the desktop launcher controller."""

from __future__ import annotations

from typing import Any

from utils.launcher_profile_snapshot import write_launcher_profile_snapshot
from utils.store_profile_repository import StoreProfileRepository
from launcher.desktop_workspace_journal import record_workspace_journal_event

NO_PROFILE_TO_SAVE_MESSAGE = "Профиль ещё не создан. Сначала выполните исследование сайта."
PROFILE_SAVED_MESSAGE = "Профиль магазина сохранён."


def persist_launcher_profile_snapshot(controller: Any, task_name: str) -> bool:
    """Persist one Launcher V3 workspace snapshot for the current controller state."""
    if _is_partial_onboarding_snapshot(controller, task_name):
        return False
    snapshot_path = write_launcher_profile_snapshot(
        controller.state,
        base_dir=controller.root_dir / "data" / "launcher_profiles",
        task_name=task_name,
    )
    if snapshot_path is None:
        return False
    path_text = str(snapshot_path)
    controller.state.result.artifact_paths["launcher_profile_snapshot_path"] = path_text
    controller.state.profile.diagnostics["launcher_profile_snapshot_path"] = path_text
    profile_db_path = controller.root_dir / "data" / "profiles" / "store_profiles.db"
    saved = StoreProfileRepository(profile_db_path).save_launcher_state(
        controller.state,
        task_name=task_name,
    )
    if not saved:
        return False
    db_path_text = str(profile_db_path)
    controller.state.result.artifact_paths["store_profile_db_path"] = db_path_text
    controller.state.profile.diagnostics["store_profile_db_path"] = db_path_text
    controller.state.profile.diagnostics["store_profile_id"] = saved["profile_id"]
    controller.state.profile.diagnostics["store_profile_version_id"] = saved["version_id"]
    return True


def save_current_profile_session(controller: Any) -> bool:
    """Persist the current profile/workspace by explicit launcher command."""
    if not _has_current_profile(controller):
        controller.state.task.status = "failed"
        controller.state.task.task_name = "save_profile_session"
        controller.state.task.task_kind = "profile"
        controller.state.task.message = NO_PROFILE_TO_SAVE_MESSAGE
        controller.state.task.last_error = NO_PROFILE_TO_SAVE_MESSAGE
        return False
    saved = persist_launcher_profile_snapshot(controller, "manual_profile_save")
    controller.state.task.task_name = "save_profile_session"
    controller.state.task.task_kind = "profile"
    if saved:
        controller.state.task.status = "succeeded"
        controller.state.task.message = PROFILE_SAVED_MESSAGE
        controller.state.task.last_error = ""
        record_workspace_journal_event(
            controller,
            event_type="manual_profile_save",
            title="Профиль сохранён",
            message=PROFILE_SAVED_MESSAGE,
            status="succeeded",
        )
        return True
    controller.state.task.status = "failed"
    controller.state.task.message = NO_PROFILE_TO_SAVE_MESSAGE
    controller.state.task.last_error = NO_PROFILE_TO_SAVE_MESSAGE
    return False


def _has_current_profile(controller: Any) -> bool:
    profile = controller.state.profile
    return bool(str(profile.profile_id or profile.site_url or "").strip())


def _is_partial_onboarding_snapshot(controller: Any, task_name: str) -> bool:
    if task_name != "site_onboarding_discovery":
        return False
    diagnostics = getattr(controller.state.profile, "diagnostics", {}) or {}
    return bool(diagnostics.get("partial_research"))
