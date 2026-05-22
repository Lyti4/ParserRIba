"""Widget enabled-state helpers for the desktop launcher."""

from __future__ import annotations

from typing import Any


def apply_widget_enabled_state(shell: Any) -> None:
    """Apply running/idle enabled state to launcher input widgets."""
    enabled = shell.state.task.status != "running"
    for widget in (
        shell.site_url_input,
        shell.shop_combo,
        shell.intent_combo,
        shell.category_list,
        shell.headless_checkbox,
        shell.manual_wait_checkbox,
        shell.attempts_spin,
        shell.listen_seconds_spin,
    ):
        if widget is not None:
            widget.setEnabled(enabled)
    for widget in shell.filter_widgets.values():
        widget.setEnabled(enabled)
    for widget in getattr(shell, "filter_extra_widgets", []):
        widget.setEnabled(enabled)
    for widget in getattr(shell, "category_action_buttons", []):
        widget.setEnabled(enabled)
    for widget in getattr(shell, "filter_action_buttons", []):
        widget.setEnabled(enabled)
