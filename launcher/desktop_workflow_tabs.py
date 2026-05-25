"""Workflow tab builders for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_filter_panel import build_filter_box
from launcher.desktop_selection_panel import build_catalog_selection_box, build_export_intent_box, build_store_selection_box
from launcher.desktop_window_sections import (
    build_catalog_actions_box,
    build_filter_actions_box,
    build_report_box,
    build_results_box,
    build_research_actions_box,
    build_settings_box,
    build_status_box,
)


def build_workflow_tabs(shell: Any, qtwidgets: Any) -> Any:
    """Build the staged Launcher V2 tab container."""
    tabs = qtwidgets.QTabWidget()
    tabs.addTab(_build_research_tab(shell, qtwidgets), "Исследование")
    tabs.addTab(_build_catalog_tab(shell, qtwidgets), "Каталог")
    tabs.addTab(build_results_box(shell, qtwidgets), "Товары")
    tabs.addTab(_build_filters_tab(shell, qtwidgets), "Фильтры")
    tabs.addTab(build_report_box(shell, qtwidgets), "Отчёт")
    return tabs


def _build_research_tab(shell: Any, qtwidgets: Any) -> Any:
    widget = qtwidgets.QWidget()
    layout = qtwidgets.QVBoxLayout(widget)
    layout.addWidget(build_store_selection_box(shell, qtwidgets))
    for builder in (build_research_actions_box, build_settings_box, build_status_box):
        layout.addWidget(builder(shell, qtwidgets))
    layout.addStretch(1)
    return widget


def _build_catalog_tab(shell: Any, qtwidgets: Any) -> Any:
    widget = qtwidgets.QWidget()
    layout = qtwidgets.QVBoxLayout(widget)
    layout.addWidget(build_export_intent_box(shell, qtwidgets))
    layout.addWidget(build_catalog_selection_box(shell, qtwidgets), stretch=1)
    layout.addWidget(build_catalog_actions_box(shell, qtwidgets))
    return widget


def _build_filters_tab(shell: Any, qtwidgets: Any) -> Any:
    widget = qtwidgets.QWidget()
    layout = qtwidgets.QVBoxLayout(widget)
    layout.addWidget(build_filter_box(shell, qtwidgets), stretch=1)
    layout.addWidget(build_filter_actions_box(shell, qtwidgets))
    return widget
