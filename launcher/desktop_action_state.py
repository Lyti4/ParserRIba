"""Enabled-state rules for desktop launcher actions."""

from __future__ import annotations

from models.launcher_state import LauncherAppState


def build_action_enabled_map(state: LauncherAppState) -> dict[str, bool]:
    """Return one stable enabled map for launcher action buttons."""
    if state.task.status == "running":
        return {
            "onboarding": False,
            "run_export": False,
            "load_filters": False,
            "build_report": False,
            "save_settings": False,
            "open_excel": False,
            "open_folder": False,
        }
    has_categories = bool(state.selection.categories)
    return {
        "onboarding": True,
        "run_export": has_categories,
        "load_filters": has_categories,
        "build_report": has_categories,
        "save_settings": True,
        "open_excel": bool(str(state.result.excel_path or "").strip()),
        "open_folder": bool(str(state.result.report_dir or "").strip()),
    }
