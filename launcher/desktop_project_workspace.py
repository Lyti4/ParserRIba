"""Project workspace controller helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.launcher_state import LauncherAppState
from utils.store_profile_repository import StoreProfileRepository


def profile_db_path(root_dir: Path) -> Path:
    """Return the central local profile/workspace database path."""
    return Path(root_dir) / "data" / "profiles" / "store_profiles.db"


def ensure_controller_workspace(controller: Any) -> dict[str, Any]:
    """Ensure the controller has an active project workspace."""
    db_path = profile_db_path(controller.root_dir)
    if not db_path.exists() and not str(controller.state.workspace.workspace_id or "").strip():
        workspace = _default_workspace()
        _apply_workspace_state(controller.state, workspace)
        return workspace
    repository = StoreProfileRepository(db_path)
    workspace_id = str(controller.state.workspace.workspace_id or "").strip()
    workspace = repository.get_workspace(workspace_id) if workspace_id else repository.ensure_default_workspace()
    if workspace is None:
        workspace = repository.ensure_default_workspace()
    _apply_workspace_state(controller.state, workspace)
    return workspace


def create_controller_workspace(controller: Any, name: str) -> dict[str, Any]:
    """Create and select a project workspace."""
    workspace = StoreProfileRepository(profile_db_path(controller.root_dir)).create_workspace(name)
    _apply_workspace_state(controller.state, workspace)
    return workspace


def rename_controller_workspace(controller: Any, workspace_id: str, name: str) -> dict[str, Any]:
    """Rename a project workspace and select it when present."""
    workspace = StoreProfileRepository(profile_db_path(controller.root_dir)).rename_workspace(workspace_id, name)
    if workspace:
        _apply_workspace_state(controller.state, workspace)
    return workspace


def select_controller_workspace(controller: Any, workspace_id: str) -> bool:
    """Select an existing project workspace."""
    workspace = StoreProfileRepository(profile_db_path(controller.root_dir)).get_workspace(workspace_id)
    if workspace is None:
        return False
    _apply_workspace_state(controller.state, workspace)
    return True


def list_controller_workspace_profiles(controller: Any) -> list[dict[str, str]]:
    """Return profiles owned by the active project workspace."""
    workspace = ensure_controller_workspace(controller)
    return StoreProfileRepository(profile_db_path(controller.root_dir)).list_profiles(
        workspace_id=str(workspace["workspace_id"])
    )


def _apply_workspace_state(state: LauncherAppState, workspace: dict[str, Any]) -> None:
    state.workspace.workspace_id = str(workspace.get("workspace_id") or "default")
    state.workspace.name = str(workspace.get("name") or "Основное рабочее пространство")
    state.workspace.description = str(workspace.get("description") or "")
    state.workspace.is_default = bool(workspace.get("is_default"))
    settings = workspace.get("settings")
    state.workspace.settings = dict(settings) if isinstance(settings, dict) else {}


def _default_workspace() -> dict[str, Any]:
    return {
        "workspace_id": "default",
        "name": "Основное рабочее пространство",
        "description": "",
        "settings": {},
        "is_default": True,
    }
