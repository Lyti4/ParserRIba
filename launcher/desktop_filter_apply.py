"""Apply launcher filters to the visible product workspace."""

from __future__ import annotations

from typing import Any

from launcher.desktop_filter_panel import collect_filter_selections
from launcher.desktop_filter_summary import refresh_selected_filter_summary
from launcher.desktop_report_panel import refresh_report_columns
from launcher.desktop_result_table import build_result_table
from launcher.desktop_view_helpers import build_result_caption_text


def apply_filter_change(shell: Any) -> None:
    """Sync filter widgets into state and refresh the product table."""
    if getattr(shell, "_refreshing_filter_widgets", False) or shell.result_table is None:
        return
    shell.controller.set_filters(collect_filter_selections(shell))
    table = build_result_table(shell.state)
    rows = table.get("rows")
    shown_count = len(rows) if isinstance(rows, list) else 0
    shell.state.task.message = f"Отбор применён. Показано товаров: {shown_count}."
    if shell.result_caption_label is not None:
        shell.result_caption_label.setText(build_result_caption_text(shell.state))
    refresh_selected_filter_summary(shell)
    refresh_report_columns(shell)
    shell._refresh_result_table()
    shell._refresh_action_buttons()
