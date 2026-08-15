"""Enabled-state rules for desktop launcher actions."""

from __future__ import annotations

from application.contracts import ApplicationContractError
from launcher.desktop_workspace_export import load_current_workspace
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
            "export_workspace_selected": False,
            "export_workspace_filtered": False,
            "export_workspace_all": False,
        }
    has_categories = bool(state.selection.categories)
    has_workspace = _has_current_workspace(state)
    has_workspace_filters = any(
        values for values in state.filters.found_filters.values()
    )
    return {
        "onboarding": True,
        "run_export": has_categories,
        "load_filters": has_categories,
        "build_report": has_categories,
        "save_settings": True,
        "open_excel": bool(str(state.result.excel_path or "").strip()),
        "open_folder": bool(str(state.result.report_dir or "").strip()),
        "export_workspace_selected": has_workspace
        and bool(state.selection.selected_product_ids),
        "export_workspace_filtered": has_workspace and has_workspace_filters,
        "export_workspace_all": has_workspace,
    }


def _has_current_workspace(state: LauncherAppState) -> bool:
    try:
        load_current_workspace(state)
    except (ApplicationContractError, OSError):
        return False
    return True
