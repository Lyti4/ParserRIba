"""Workflow tab builders for the desktop launcher."""

from __future__ import annotations

from typing import Any

from launcher.desktop_error_panel import build_error_box
from launcher.desktop_favorites import build_favorites_box
from launcher.desktop_filter_panel import build_filter_box
from launcher.desktop_proxy_panel import build_proxy_box
from launcher.desktop_report_panel import build_report_box
from launcher.desktop_selection_panel import build_catalog_selection_box, build_store_selection_box
from launcher.desktop_window_sections import (
    build_catalog_actions_box,
    build_results_box,
    build_research_actions_box,
    build_settings_box,
    build_status_box,
)
from launcher.desktop_navigation import sync_navigation_from_tab


def build_workflow_tabs(shell: Any, qtwidgets: Any) -> Any:
    """Build the staged Launcher V3 tab container."""
    tabs = qtwidgets.QTabWidget()
    tabs.addTab(_build_research_tab(shell, qtwidgets), "Исследование")
    tabs.addTab(_build_catalog_tab(shell, qtwidgets), "Каталог")
    tabs.addTab(_build_products_tab(shell, qtwidgets), "Товары")
    tabs.addTab(build_report_box(shell, qtwidgets), "Отчёт")
    tabs.addTab(build_proxy_box(shell, qtwidgets), "Прокси")
    tabs.addTab(build_error_box(shell, qtwidgets), "Диагностика")
    tabs.addTab(build_favorites_box(shell, qtwidgets), "\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435")
    tabs.tabBar().hide()
    tabs.currentChanged.connect(lambda index: sync_navigation_from_tab(shell, index))
    shell.workflow_tabs = tabs
    sync_navigation_from_tab(shell, tabs.currentIndex())
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
    layout.addWidget(build_catalog_selection_box(shell, qtwidgets), stretch=1)
    layout.addWidget(build_catalog_actions_box(shell, qtwidgets))
    return widget


def _build_products_tab(shell: Any, qtwidgets: Any) -> Any:
    """Build one product workspace with filters and products side by side."""
    widget = qtwidgets.QWidget()
    layout = qtwidgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    filter_box = build_filter_box(shell, qtwidgets)
    shell.filter_box = filter_box
    filter_box.setMinimumWidth(240)
    filter_box.setMaximumWidth(360)
    layout.addWidget(filter_box, stretch=0)
    layout.addWidget(build_results_box(shell, qtwidgets), stretch=1)
    return widget
