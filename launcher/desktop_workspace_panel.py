"""Project workspace summary panel for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_workspace_journal import list_workspace_journal_events
from models.launcher_state import LauncherAppState


def build_workspace_box(shell: Any, qtwidgets: Any) -> Any:
    """Build a compact project workspace summary."""
    box = qtwidgets.QGroupBox("Рабочее пространство")
    box.setObjectName("launcherWorkspaceBox")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(4)
    shell.workspace_label = qtwidgets.QLabel("")
    shell.workspace_label.setObjectName("launcherWorkspaceLabel")
    shell.workspace_label.setWordWrap(True)
    layout.addWidget(shell.workspace_label)
    shell.workspace_journal_label = qtwidgets.QLabel("")
    shell.workspace_journal_label.setObjectName("launcherWorkspaceJournalLabel")
    shell.workspace_journal_label.setWordWrap(True)
    layout.addWidget(shell.workspace_journal_label)
    return box


def refresh_workspace_box(shell: Any) -> None:
    """Refresh the visible workspace summary."""
    label = getattr(shell, "workspace_label", None)
    if label is None:
        return
    profiles = []
    controller = getattr(shell, "controller", None)
    if controller is not None and hasattr(controller, "list_workspace_profiles"):
        profiles = controller.list_workspace_profiles()
    label.setText(build_workspace_summary_text(shell.state, profiles))
    journal_label = getattr(shell, "workspace_journal_label", None)
    if journal_label is not None:
        events = list_workspace_journal_events(controller, limit=3) if controller is not None else []
        journal_label.setText(build_workspace_journal_text(events))


def build_workspace_summary_text(state: LauncherAppState, profiles: list[dict[str, Any]]) -> str:
    """Return concise Russian workspace status text."""
    workspace_name = state.workspace.name or "Основное рабочее пространство"
    parts = [f"Рабочее пространство: {workspace_name}", f"магазины: {len(profiles)}"]
    latest = _latest_profile_name(profiles)
    if latest:
        parts.append(f"последний: {latest}")
    return " | ".join(parts)


def _latest_profile_name(profiles: list[dict[str, Any]]) -> str:
    if not profiles:
        return ""
    first = profiles[0]
    return str(first.get("display_name") or first.get("domain") or first.get("site_url") or "")


def build_workspace_journal_text(events: list[dict[str, Any]]) -> str:
    """Return concise text for recent workspace journal events."""
    if not events:
        return "Журнал: событий пока нет."
    parts = []
    for event in _prioritized_journal_events(events):
        title = str(event.get("title") or event.get("event_type") or "Событие")
        status = str(event.get("status") or "info")
        parts.append(f"{_status_label(status)} {title}")
    return "Журнал: " + " | ".join(parts)


def _prioritized_journal_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep recent success/current events above older failed noise."""
    if not events:
        return []
    first_status = str(events[0].get("status") or "")
    if first_status == "succeeded":
        failures = [event for event in events if str(event.get("status") or "") == "failed"]
        if failures:
            return [events[0], failures[0]]
        return events[:2]
    return events[:2]


def _status_label(status: str) -> str:
    return {
        "succeeded": "Успешно:",
        "failed": "Ошибка:",
        "warning": "Внимание:",
    }.get(status, "Инфо:")
