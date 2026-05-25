"""Research-state helpers for the desktop launcher controller."""

from __future__ import annotations

from launcher.desktop_ui_text import display_research_phase
from models.launcher_state import LauncherAppState
from utils.local_task_adapter import LocalTaskProcessResult

RESEARCH_KEYS = (
    "research_mode",
    "current_phase",
    "active_profile_id",
    "active_profile_version_id",
    "streamed_categories",
)


def sync_research_state(
    state: LauncherAppState,
    result: LocalTaskProcessResult,
) -> str | None:
    """Sync research metadata from a task result into launcher state."""
    summary = dict(result.manifest.summary or {})
    view = state.result.launcher_view
    if result.manifest.task_name != "site_onboarding_discovery" and not any(
        key in summary or key in view for key in RESEARCH_KEYS
    ):
        return None
    streamed = summary.get("streamed_categories", view.get("streamed_categories", []))
    state.research.mode = str(
        summary.get("research_mode") or view.get("research_mode") or state.research.mode or "live"
    )
    state.research.current_phase = str(
        summary.get("current_phase") or view.get("current_phase") or state.research.current_phase or ""
    )
    state.research.current_status = str(result.manifest.status or "")
    state.research.active_profile_id = str(summary.get("active_profile_id") or view.get("active_profile_id") or "")
    state.research.active_profile_version_id = str(
        summary.get("active_profile_version_id") or view.get("active_profile_version_id") or ""
    )
    state.research.streamed_categories = [str(item) for item in streamed] if isinstance(streamed, list) else []
    view["research_mode"] = state.research.mode
    view["current_phase"] = state.research.current_phase
    view["active_profile_id"] = state.research.active_profile_id
    view["active_profile_version_id"] = state.research.active_profile_version_id
    view["streamed_categories"] = list(state.research.streamed_categories)
    if result.manifest.task_name == "site_onboarding_discovery" and state.research.current_phase:
        return display_research_phase(state.research.current_phase)
    return None
