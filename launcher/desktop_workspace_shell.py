"""Launcher V4 workspace shell composition."""

from __future__ import annotations

from typing import Any

from launcher.desktop_command_strip import build_command_strip
from launcher.desktop_inspector_panel import build_right_inspector
from launcher.desktop_navigation import build_navigation_rail
from launcher.desktop_workspace_panel import build_workspace_box
from launcher.desktop_workflow_tabs import build_workflow_tabs


def build_workspace_shell(shell: Any, qtwidgets: Any) -> Any:
    """Build a V4 shell around the existing Launcher V3 workspaces."""
    container = qtwidgets.QWidget()
    root = qtwidgets.QHBoxLayout(container)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(build_navigation_rail(shell, qtwidgets), stretch=0)

    main = qtwidgets.QWidget()
    main_layout = qtwidgets.QVBoxLayout(main)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(8)
    main_layout.addWidget(build_command_strip(shell, qtwidgets), stretch=0)
    main_layout.addWidget(build_workspace_box(shell, qtwidgets), stretch=0)
    main_layout.addWidget(_build_scrollable_workflow(shell, qtwidgets), stretch=1)
    root.addWidget(main, stretch=1)
    root.addWidget(build_right_inspector(shell, qtwidgets), stretch=0)
    return container


def _build_scrollable_workflow(shell: Any, qtwidgets: Any) -> Any:
    host = qtwidgets.QWidget()
    host.setMinimumWidth(0)
    host.setSizePolicy(
        qtwidgets.QSizePolicy.Policy.Ignored,
        qtwidgets.QSizePolicy.Policy.Expanding,
    )
    layout = qtwidgets.QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(build_workflow_tabs(shell, qtwidgets))

    scroll = qtwidgets.QScrollArea()
    scroll.setObjectName("launcherControlsScrollArea")
    scroll.setWidgetResizable(True)
    qt = getattr(shell, "_qt", None)
    if qt is not None:
        scroll.setHorizontalScrollBarPolicy(qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(qtwidgets.QFrame.Shape.NoFrame)
    scroll.setWidget(host)
    return scroll
