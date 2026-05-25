"""Pure helpers for desktop launcher presentation."""

from __future__ import annotations

from pathlib import Path


from launcher.desktop_result_table import build_result_table
from launcher.desktop_ui_text import (
    display_research_mode,
    display_research_phase,
    display_shop,
    display_task_name,
    display_task_status,
)
from models.launcher_state import LauncherAppState


def build_status_text(state: LauncherAppState) -> str:
    """Build one concise launcher status line."""
    task = state.task
    research = state.research
    parts = [
        f"Магазин: {display_shop(state.selection.shop)}",
        f"Режим исследования: {display_research_mode(research.mode)}",
    ]
    if task.task_name == "site_onboarding_discovery" or task.status == "running":
        parts.insert(1, f"Задача: {display_task_name(task.task_name or 'site_onboarding_discovery')}")
        parts.insert(2, f"Статус: {display_task_status(task.status)}")
    if research.current_phase:
        parts.append(f"Этап: {display_research_phase(research.current_phase)}")
    if task.status == "running":
        parts.append("Интерфейс: занят")
    return " | ".join(parts)


def build_summary_text(state: LauncherAppState) -> str:
    """Build a compact human-readable summary for the current launcher result."""
    lines: list[str] = []
    if state.task.task_name in {"site_onboarding_discovery", ""} and state.task.message.strip():
        lines.append(state.task.message.strip())
    if state.task.status == "running":
        lines.append("Лаунчер ожидает завершения текущего действия.")
    if state.task.last_error:
        lines.append(f"Последняя ошибка: {state.task.last_error}")
    _append_research_summary(lines, state)

    catalog_type = _catalog_type(state)
    if catalog_type:
        lines.append(f"Тип каталога: {catalog_type}")
    category_tree = _category_tree(state)
    if isinstance(category_tree, list) and category_tree:
        names = [
            str(item.get("name") or "").strip()
            for item in category_tree
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        lines.append(f"Разделов каталога найдено: {len(category_tree)}")
        if names:
            lines.append(f"Найденные разделы: {', '.join(names[:6])}")
    full_catalog_links = state.catalog.full_links or _view_list(state, "full_catalog_links")
    full_catalog_tree = state.catalog.full_tree or _view_list(state, "full_catalog_tree")
    if isinstance(full_catalog_links, list) and full_catalog_links:
        lines.append(f"Полный каталог: найдено URL разделов: {len(full_catalog_links)}")
        names = [
            str(item.get("name") or "").strip()
            for item in full_catalog_links
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        if names:
            lines.append(f"Первые разделы полного каталога: {', '.join(names[:8])}")
    elif isinstance(full_catalog_tree, list) and full_catalog_tree:
        lines.append(f"Полный каталог: корневых разделов: {len(full_catalog_tree)}")

    return "\n".join(lines) if lines else "Пока нет данных."


def build_result_caption_text(state: LauncherAppState) -> str:
    """Build one short result caption for the table area."""
    parts = _result_context_parts(state)
    return " | ".join(parts) if parts else "Пока нет строк результата."


def build_result_rows(state: LauncherAppState) -> list[list[str]]:
    """Build rows for the launcher result table."""
    table = build_result_table(state)
    rows = table.get("rows")
    return rows if isinstance(rows, list) else []


def _append_research_summary(lines: list[str], state: LauncherAppState) -> None:
    research = state.research
    diagnostics = _diagnostics(state)
    lines.append(f"Режим исследования: {display_research_mode(research.mode)}")
    if research.current_phase:
        lines.append(f"Текущий этап: {display_research_phase(research.current_phase)}")
    if research.active_profile_id or research.active_profile_version_id:
        lines.append(
            "Активный профиль: "
            f"{research.active_profile_id or 'не задан'} / {research.active_profile_version_id or 'не задан'}"
        )
    if research.streamed_categories:
        lines.append(f"Поток разделов: {', '.join(research.streamed_categories[:6])}")
    elif research.mode == "quiet" and _category_tree(state):
        lines.append("Поток разделов скрыт до завершения исследования.")
    if isinstance(diagnostics, dict) and diagnostics.get("partial_research"):
        lines.append("Предупреждение: частично исследовано.")


def _append_top_counts(lines: list[str], title: str, counts: object) -> None:
    if not isinstance(counts, dict) or not counts:
        return
    pairs = sorted(
        ((str(name), int(count)) for name, count in counts.items()),
        key=lambda item: (-item[1], item[0]),
    )[:3]
    lines.append(f"{title}: {', '.join(f'{name}={count}' for name, count in pairs)}")


def _append_wine_breakdown(lines: list[str], breakdown: object) -> None:
    if not isinstance(breakdown, dict):
        return
    for title, key in (
        ("Типы вина", "style_counts"),
        ("Алкогольный тип", "alcohol_type_counts"),
        ("Классы сахара", "sugar_class_counts"),
        ("Цвета", "color_counts"),
    ):
        _append_top_counts(lines, title, breakdown.get(key))


def _append_result_context(lines: list[str], state: LauncherAppState) -> None:
    lines.extend(_result_context_parts(state))


def _result_context_parts(state: LauncherAppState) -> list[str]:
    table = build_result_table(state)
    rows = table.get("rows")
    row_count = len(rows) if isinstance(rows, list) else 0
    parts: list[str] = []
    if row_count == 0:
        report_summary = _report_summary(state)
        category_counts = report_summary.get("category_counts") if isinstance(report_summary, dict) else None
        if isinstance(category_counts, dict):
            row_count = len(category_counts)
    if row_count:
        parts.append(f"Строк показано: {row_count}")
    selected_count = len(state.selection.selected_product_ids)
    if selected_count:
        parts.append(f"Выбрано товаров: {selected_count}")
    active_filters = _active_filter_parts(state)
    if state.result.json_path and Path(state.result.json_path).exists():
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u043e\u0442\u0444\u0438\u043b\u044c\u0442\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 JSON \u0432\u044b\u0433\u0440\u0443\u0437\u043a\u0438" if active_filters else "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: JSON \u0432\u044b\u0433\u0440\u0443\u0437\u043a\u0438")
    elif _report_summary(state):
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u0441\u0432\u043e\u0434\u043a\u0430 \u043f\u043e \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u043e\u043c\u0443 \u043e\u0442\u0447\u0451\u0442\u0443")
    elif state.catalog.full_tree or state.result.launcher_view.get("full_catalog_tree"):
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u043f\u043e\u043b\u043d\u044b\u0439 \u043a\u0430\u0442\u0430\u043b\u043e\u0433 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u044f")
    elif _category_tree(state):
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435 \u043c\u0430\u0433\u0430\u0437\u0438\u043d\u0430")
    if state.result.json_path and Path(state.result.json_path).exists():
        if selected_count:
            parts.append("\u041e\u0442\u0447\u0451\u0442 \u0431\u0443\u0434\u0435\u0442 \u043f\u043e\u0441\u0442\u0440\u043e\u0435\u043d \u043f\u043e \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u043c \u0442\u043e\u0432\u0430\u0440\u0430\u043c")
        elif row_count:
            parts.append("\u041c\u043e\u0436\u043d\u043e \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0435 \u0442\u043e\u0432\u0430\u0440\u044b \u043f\u0435\u0440\u0435\u0434 \u0441\u0431\u043e\u0440\u043a\u043e\u0439 Excel")
    if active_filters:
        parts.append(f"Активные фильтры: {', '.join(active_filters)}")
    return parts


def _active_filter_parts(state: LauncherAppState) -> list[str]:
    parts: list[str] = []
    for label, values in (
        ("поставщики", state.filters.suppliers),
        ("бренды", state.filters.brands),
        ("категории", state.filters.categories),
        ("типы вина", state.filters.wine_styles),
        ("алкогольный тип", state.filters.alcohol_types),
        ("сахар", state.filters.sugar_classes),
        ("цвет", state.filters.colors),
    ):
        if values:
            parts.append(f"{label}={len(values)}")
    if state.filters.min_price is not None or state.filters.max_price is not None:
        parts.append("цена=1")
    if state.filters.in_stock is not None:
        parts.append("наличие=1")
    if state.filters.strict_missing:
        parts.append("строгий режим=1")
    return parts


def _report_summary(state: LauncherAppState) -> dict:
    summary = state.result.summary.get("report_summary")
    if isinstance(summary, dict):
        return summary
    view_summary = state.result.launcher_view.get("report_summary")
    return view_summary if isinstance(view_summary, dict) else {}


def _diagnostics(state: LauncherAppState) -> dict:
    if state.profile.diagnostics:
        return dict(state.profile.diagnostics)
    diagnostics = state.result.summary.get("diagnostics_summary")
    if isinstance(diagnostics, dict):
        return diagnostics
    view_diagnostics = state.result.launcher_view.get("diagnostics_summary")
    return view_diagnostics if isinstance(view_diagnostics, dict) else {}


def _category_tree(state: LauncherAppState) -> list:
    category_tree = state.result.summary.get("category_tree")
    if isinstance(category_tree, list) and category_tree:
        return category_tree
    view_tree = state.result.launcher_view.get("category_tree")
    if isinstance(view_tree, list) and view_tree:
        return view_tree
    return state.catalog.full_tree


def _catalog_type(state: LauncherAppState) -> str:
    if state.catalog.catalog_type:
        return state.catalog.catalog_type
    discovery = state.result.summary.get("catalog_discovery")
    if not isinstance(discovery, dict):
        discovery = state.result.launcher_view.get("catalog_discovery")
    return str(discovery.get("surface_type") or "") if isinstance(discovery, dict) else ""


def _view_list(state: LauncherAppState, key: str) -> list:
    value = state.result.launcher_view.get(key)
    return value if isinstance(value, list) else []
