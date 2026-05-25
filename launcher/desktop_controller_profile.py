"""Profile snapshot helpers for the desktop launcher controller."""

from __future__ import annotations

from typing import Any

from utils.launcher_profile_snapshot import write_launcher_profile_snapshot


def persist_launcher_profile_snapshot(controller: Any, task_name: str) -> None:
    """Persist one Launcher V2 workspace snapshot for the current controller state."""
    snapshot_path = write_launcher_profile_snapshot(
        controller.state,
        base_dir=controller.root_dir / "data" / "launcher_profiles",
        task_name=task_name,
    )
    if snapshot_path is None:
        return
    path_text = str(snapshot_path)
    controller.state.result.artifact_paths["launcher_profile_snapshot_path"] = path_text
    controller.state.profile.diagnostics["launcher_profile_snapshot_path"] = path_text
