"""Store identity helpers for the launcher shell and controller."""

from __future__ import annotations

from models.launcher_state import LauncherAppState


def active_store_code(state: LauncherAppState) -> str:
    """Return the current store code, preferring a discovered profile."""
    return str(state.profile.shop or state.selection.shop or "").strip()


def active_store_display_name(state: LauncherAppState) -> str:
    """Return a user-facing current store label."""
    return str(
        state.profile.display_name
        or state.profile.domain
        or state.profile.site_url
        or active_store_code(state)
        or ""
    ).strip()
