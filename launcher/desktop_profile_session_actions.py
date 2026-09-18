"""UI actions for the launcher profile/session panel."""

from __future__ import annotations

from typing import Any

from launcher.desktop_shell_helpers import current_combo_value
from launcher.desktop_store_identity import active_store_code


def select_workspace_profile(shell: Any) -> None:
    """Switch active workspace profile without starting browser runtime."""
    combo = getattr(shell, "profile_selector_combo", None)
    if combo is None or combo.currentIndex() < 0:
        return
    profile_id = str(combo.currentData() or "").strip()
    if not profile_id:
        return
    workspace_id = str(shell.state.workspace.workspace_id or "default").strip() or "default"
    shell.state.workspace_selection.workspace_id = workspace_id
    shell.state.workspace_selection.selected_profile_id = profile_id
    profile = _profile_row(shell, profile_id)
    if profile:
        _apply_profile_row(shell, profile)
    sessions = shell.controller.list_profile_sessions(profile_id=profile_id)
    version_id = _selected_version_id(profile, sessions)
    shell.state.workspace_selection.selected_version_id = version_id
    if version_id:
        shell.controller.load_profile_session(
            workspace_id=workspace_id,
            profile_id=profile_id,
            version_id=version_id,
        )
    else:
        shell.controller.save_state()
    if hasattr(shell.controller, "load_workspace_favorites"):
        shell.controller.load_workspace_favorites()
    shell._refresh_ui()


def open_latest_profile_session(shell: Any) -> None:
    """Load the selected or latest saved profile session and refresh widgets."""
    if getattr(shell, "category_list", None) is not None:
        shell._update_state_from_widgets()
    combo = getattr(shell, "profile_session_combo", None)
    if combo is not None and combo.currentIndex() >= 0:
        version_id = str(combo.currentData() or "").strip()
        profile_id = str(shell.state.profile.profile_id or "").strip()
        workspace_id = str(shell.state.workspace.workspace_id or "default").strip()
        if version_id and profile_id:
            shell.controller.load_profile_session(
                workspace_id=workspace_id,
                profile_id=profile_id,
                version_id=version_id,
            )
            shell._refresh_ui()
            return
    shop = active_store_code(shell.state) or current_combo_value(shell.shop_combo)
    shell.controller.load_latest_profile_session(shop=shop, site_url=shell._site_url())
    shell._refresh_ui()


def save_profile_session(shell: Any) -> None:
    """Persist the current profile session and refresh launcher widgets."""
    if getattr(shell, "category_list", None) is not None:
        shell._update_state_from_widgets()
    shell.controller.save_profile_session()
    shell._refresh_ui()


def _profile_row(shell: Any, profile_id: str) -> dict[str, Any]:
    for row in shell.controller.list_workspace_profiles():
        if str(row.get("profile_id") or "").strip() == profile_id:
            return row
    return {}


def _apply_profile_row(shell: Any, row: dict[str, Any]) -> None:
    shell.state.profile.profile_id = str(row.get("profile_id") or "")
    shell.state.profile.site_url = str(row.get("site_url") or "")
    shell.state.profile.domain = str(row.get("domain") or "")
    shell.state.profile.shop = str(row.get("shop") or "")
    shell.state.profile.display_name = str(row.get("display_name") or "")


def _selected_version_id(profile: dict[str, Any], sessions: list[dict[str, Any]]) -> str:
    version_id = str(profile.get("latest_version_id") or "").strip()
    if version_id:
        return version_id
    if sessions:
        return str(sessions[0].get("version_id") or "").strip()
    return ""
