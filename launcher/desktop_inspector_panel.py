"""Launcher V4 persistent right inspector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from launcher.desktop_profile_session_panel import build_profile_session_box
from models.launcher_state import LauncherAppState


@dataclass(frozen=True)
class InspectorSection:
    key: str
    title: str
    priority: int


@dataclass(frozen=True)
class RouteContext:
    title: str
    text: str
    show_profile_session: bool = False


INSPECTOR_SECTIONS = (
    InspectorSection("product_or_context", "product/context", 10),
    InspectorSection("profile_session", "store/save summary", 20),
    InspectorSection("task_attention", "task attention", 30),
    InspectorSection("quick_actions", "quick actions", 40),
)


def inspector_section_priorities() -> dict[str, int]:
    """Return stable inspector section priority order."""
    return {section.key: section.priority for section in INSPECTOR_SECTIONS}


def build_right_inspector(shell: Any, qtwidgets: Any) -> Any:
    """Build the fixed V4 right inspector."""
    panel = qtwidgets.QFrame()
    panel.setObjectName("launcherRightInspector")
    panel.setMinimumWidth(280)
    panel.setMaximumWidth(300)
    layout = qtwidgets.QVBoxLayout(panel)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(12)

    title = qtwidgets.QLabel("")
    title.setObjectName("launcherInspectorTitle")
    shell.inspector_title_label = title
    layout.addWidget(title)
    route_group = qtwidgets.QGroupBox("Контекст")
    route_group.setObjectName("launcherRouteContextBox")
    route_layout = qtwidgets.QVBoxLayout(route_group)
    route_label = qtwidgets.QLabel("")
    route_label.setObjectName("launcherRouteContextLabel")
    route_label.setWordWrap(True)
    route_layout.addWidget(route_label)
    product_detail_text = qtwidgets.QTextEdit()
    product_detail_text.setObjectName("launcherProductDetailText")
    product_detail_text.setReadOnly(True)
    product_detail_text.setMinimumHeight(220)
    route_layout.addWidget(product_detail_text)
    shell.inspector_route_context_group = route_group
    shell.inspector_route_context_label = route_label
    shell.product_detail_text = product_detail_text
    layout.addWidget(route_group)
    profile_session_box = build_profile_session_box(shell, qtwidgets)
    shell.inspector_profile_session_box = profile_session_box
    layout.addWidget(profile_session_box)
    layout.addWidget(_build_task_attention_group(shell, qtwidgets))
    layout.addWidget(_build_quick_actions(shell, qtwidgets))
    layout.addStretch(1)
    refresh_right_inspector(shell)
    return panel


def refresh_right_inspector(shell: Any) -> None:
    """Refresh persistent inspector labels from the launcher state."""
    context = route_context_for_key(_active_route_key(shell))
    title_label = getattr(shell, "inspector_title_label", None)
    if title_label is not None:
        title_label.setText(context.title)
    context_label = getattr(shell, "inspector_route_context_label", None)
    if context_label is not None:
        context_label.setText(context.text)
    product_detail_text = getattr(shell, "product_detail_text", None)
    if product_detail_text is not None:
        product_detail_text.setVisible(_active_route_key(shell) == "products")
    profile_session_box = getattr(shell, "inspector_profile_session_box", None)
    if profile_session_box is not None:
        profile_session_box.setVisible(context.show_profile_session)
    task_label = getattr(shell, "inspector_task_label", None)
    if task_label is not None:
        task_label.setText(build_task_summary_text(shell.state))
    task_group = getattr(shell, "inspector_task_group", None)
    if task_group is not None:
        task_group.setVisible(shell.state.task.status == "failed")


def build_task_summary_text(state: LauncherAppState) -> str:
    """Return a user-facing warning for failed tasks."""
    if state.task.status == "failed" and state.task.last_error:
        return "Последняя задача завершилась с ошибкой. Подробности доступны во вкладке диагностики."
    return ""


def route_context_for_key(route_key: str) -> RouteContext:
    """Return right-panel context rules for a launcher route."""
    contexts = {
        "research": RouteContext(
            "Магазин и сохранения",
            "Выберите сайт магазина, проверьте настройки исследования и сохраните удачное состояние.",
            show_profile_session=True,
        ),
        "catalog": RouteContext(
            "Каталог",
            "Проверьте найденные разделы и выберите категории для сбора товаров.",
            show_profile_session=True,
        ),
        "products": RouteContext(
            "Товары",
            "Здесь будет карточка товара. Выберите строку таблицы, чтобы видеть подробности без лишней сводки.",
        ),
        "report": RouteContext(
            "Отчёт",
            "Проверьте область отчёта, выбранные товары и последний Excel-файл перед сохранением.",
            show_profile_session=True,
        ),
        "diagnostics": RouteContext(
            "Диагностика",
            "Смотрите подробности ошибок и технический журнал в основной области диагностики.",
        ),
        "proxy": RouteContext(
            "Прокси",
            "Настройки прокси относятся к запуску браузера и диагностике доступа к магазину.",
        ),
        "favorites": RouteContext(
            "Избранное",
            "Быстрый доступ к сохранённым магазинам, разделам и товарам.",
        ),
    }
    return contexts.get(route_key, contexts["research"])


def _active_route_key(shell: Any) -> str:
    active_key = str(getattr(shell, "active_route_key", "") or "").strip()
    if active_key:
        return active_key
    tabs = getattr(shell, "workflow_tabs", None)
    if tabs is None:
        return "research"
    route_by_index = {
        0: "research",
        1: "catalog",
        2: "products",
        3: "report",
        4: "proxy",
        5: "diagnostics",
        6: "favorites",
    }
    return route_by_index.get(tabs.currentIndex(), "research")


def _build_task_attention_group(shell: Any, qtwidgets: Any) -> Any:
    group = qtwidgets.QGroupBox("Требует внимания")
    group.setObjectName("launcherInspectorTaskAttentionBox")
    layout = qtwidgets.QVBoxLayout(group)
    shell.inspector_task_label = qtwidgets.QLabel("")
    shell.inspector_task_label.setObjectName("launcherInspectorTaskLabel")
    shell.inspector_task_label.setWordWrap(True)
    layout.addWidget(shell.inspector_task_label)
    shell.inspector_task_group = group
    return group


def _build_quick_actions(shell: Any, qtwidgets: Any) -> Any:
    group = qtwidgets.QGroupBox("Быстрые действия")
    layout = qtwidgets.QVBoxLayout(group)
    diagnostics_button = qtwidgets.QPushButton("Диагностика")
    diagnostics_button.setObjectName("launcherInspectorDiagnosticsButton")
    diagnostics_button.clicked.connect(lambda: _select_tab(shell, "diagnostics"))
    layout.addWidget(diagnostics_button)
    report_dir_button = qtwidgets.QPushButton("Папка отчётов")
    report_dir_button.setObjectName("launcherInspectorReportDirButton")
    report_dir_button.clicked.connect(shell._on_open_report_dir)
    layout.addWidget(report_dir_button)
    return group


def _select_tab(shell: Any, key: str) -> None:
    selector = getattr(shell, "select_navigation_item", None)
    if callable(selector):
        selector(key)
