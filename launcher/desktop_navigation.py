"""Launcher V4 navigation rail."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NAV_TAB_INDEX = {
    "research": 0,
    "catalog": 1,
    "products": 2,
    "report": 3,
    "proxy": 4,
    "diagnostics": 5,
    "favorites": 6,
}


@dataclass(frozen=True)
class NavigationItem:
    key: str
    label: str
    enabled: bool = True
    availability: str = "available"


NAV_ITEMS = (
    NavigationItem("research", "\u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435"),
    NavigationItem("catalog", "\u041a\u0430\u0442\u0430\u043b\u043e\u0433"),
    NavigationItem("products", "\u0422\u043e\u0432\u0430\u0440\u044b"),
    NavigationItem("report", "\u041e\u0442\u0447\u0451\u0442"),
    NavigationItem("profile", "\u041f\u0440\u043e\u0444\u0438\u043b\u044c", enabled=False, availability="disabled"),
    NavigationItem("diagnostics", "\u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430"),
    NavigationItem("proxy", "\u041f\u0440\u043e\u043a\u0441\u0438"),
    NavigationItem("favorites", "\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435"),
    NavigationItem("price_history", "\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0446\u0435\u043d", enabled=False, availability="planned"),
    NavigationItem("scheduler", "\u041f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0449\u0438\u043a", enabled=False, availability="planned"),
    NavigationItem("stores", "\u041c\u0430\u0433\u0430\u0437\u0438\u043d\u044b", enabled=False, availability="planned"),
)


def navigation_state_for_tab(
    active_key: str,
    *,
    completed_keys: set[str] | None = None,
    warning_keys: set[str] | None = None,
) -> dict[str, str]:
    """Return visual state for every navigation item."""
    completed = completed_keys or set()
    warnings = warning_keys or set()
    states: dict[str, str] = {}
    for item in NAV_ITEMS:
        if item.availability == "planned":
            states[item.key] = "planned"
        elif not item.enabled:
            states[item.key] = "disabled"
        elif item.key == active_key:
            states[item.key] = "active"
        elif item.key in warnings:
            states[item.key] = "warning"
        elif item.key in completed:
            states[item.key] = "completed"
        else:
            states[item.key] = "idle"
    return states


def navigation_availability() -> dict[str, str]:
    """Return route availability for honest future-module display."""
    return {item.key: item.availability for item in NAV_ITEMS}


def build_navigation_rail(shell: Any, qtwidgets: Any) -> Any:
    """Build the left V4 navigation rail."""
    rail = qtwidgets.QFrame()
    rail.setObjectName("launcherNavigationRail")
    rail.setMinimumWidth(150)
    rail.setMaximumWidth(170)
    layout = qtwidgets.QVBoxLayout(rail)
    layout.setContentsMargins(10, 12, 10, 12)
    layout.setSpacing(6)
    title = qtwidgets.QLabel("ParserRIba")
    title.setObjectName("launcherNavigationTitle")
    layout.addWidget(title)
    shell.navigation_buttons = {}
    for item in NAV_ITEMS:
        button = qtwidgets.QPushButton(item.label)
        button.setObjectName(f"launcherNavigation_{item.key}")
        button.setProperty("routeAvailability", item.availability)
        button.setEnabled(item.enabled)
        button.setCheckable(item.enabled)
        if not item.enabled:
            button.setToolTip(_disabled_route_hint(item))
        if item.enabled and item.key in NAV_TAB_INDEX:
            button.clicked.connect(lambda _checked=False, key=item.key: select_navigation_item(shell, key))
        shell.navigation_buttons[item.key] = button
        layout.addWidget(button)
    layout.addStretch(1)
    shell.select_navigation_item = lambda key: select_navigation_item(shell, key)
    return rail


def select_navigation_item(shell: Any, active_key: str) -> None:
    """Switch the legacy workflow tab and sync V4 navigation state."""
    if navigation_availability().get(active_key) != "available":
        _sync_navigation_buttons(shell, active_key)
        return
    tabs = getattr(shell, "workflow_tabs", None)
    index = NAV_TAB_INDEX.get(active_key)
    if tabs is not None and index is not None:
        tabs.setCurrentIndex(index)
    _sync_navigation_buttons(shell, active_key)


def sync_navigation_from_tab(shell: Any, tab_index: int) -> None:
    """Sync V4 navigation state after the user switches a tab directly."""
    for key, index in NAV_TAB_INDEX.items():
        if index == tab_index:
            _sync_navigation_buttons(shell, key)
            return


def _sync_navigation_buttons(shell: Any, active_key: str) -> None:
    shell.active_route_key = active_key
    buttons = getattr(shell, "navigation_buttons", {})
    states = navigation_state_for_tab(active_key)
    for key, button in buttons.items():
        if button is not None:
            state = states.get(key, "idle")
            button.setChecked(state == "active")
            button.setProperty("navigationState", state)
    if getattr(shell, "inspector_title_label", None) is not None:
        from launcher.desktop_inspector_panel import refresh_right_inspector

        refresh_right_inspector(shell)


def _disabled_route_hint(item: NavigationItem) -> str:
    if item.availability == "planned":
        return "\u0420\u0430\u0437\u0434\u0435\u043b \u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d \u0438 \u043f\u043e\u043a\u0430 \u043d\u0435 \u0433\u043e\u0442\u043e\u0432."
    return "\u0414\u0430\u043d\u043d\u044b\u0435 \u044d\u0442\u043e\u0433\u043e \u0440\u0430\u0437\u0434\u0435\u043b\u0430 \u043f\u043e\u043a\u0430 \u043f\u043e\u043a\u0430\u0437\u0430\u043d\u044b \u0432 \u0438\u043d\u0441\u043f\u0435\u043a\u0442\u043e\u0440\u0435."
