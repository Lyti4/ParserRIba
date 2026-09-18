"""Pure helpers for desktop launcher presentation."""

from __future__ import annotations

from pathlib import Path


from launcher.desktop_result_table import build_result_table
from launcher.desktop_state_readers import (
    catalog_discovery,
    category_tree,
    diagnostics_summary,
    full_catalog_links,
    full_catalog_tree,
    product_items,
    report_summary,
)
from launcher.desktop_store_identity import active_store_display_name
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
        f"Магазин: {display_shop(active_store_display_name(state))}",
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
    if state.task.status == "failed" and state.task.last_error:
        lines.append(f"Последняя ошибка: {state.task.last_error}")
    _append_research_summary(lines, state)

    catalog_type = _catalog_type(state)
    if catalog_type:
        lines.append(f"Тип каталога: {catalog_type}")
    tree = _category_tree(state)
    if tree:
        names = [
            str(item.get("name") or "").strip()
            for item in tree
            if str(item.get("name") or "").strip()
        ]
        lines.append(f"Разделов каталога найдено: {len(tree)}")
        if names:
            lines.append(f"Найденные разделы: {', '.join(names[:6])}")
    catalog_links = full_catalog_links(state)
    catalog_tree = full_catalog_tree(state)
    if catalog_links:
        lines.append(f"Полный каталог: найдено URL разделов: {len(catalog_links)}")
        names = [
            str(item.get("name") or "").strip()
            for item in catalog_links
            if str(item.get("name") or "").strip()
        ]
        if names:
            lines.append(f"Первые разделы полного каталога: {', '.join(names[:8])}")
    elif catalog_tree:
        lines.append(f"Полный каталог: корневых разделов: {len(catalog_tree)}")

    return "\n".join(lines) if lines else "Пока нет данных."


def build_result_caption_text(state: LauncherAppState) -> str:
    """Build one short result caption for the table area."""
    parts = _result_context_parts(state)
    return " | ".join(parts) if parts else "Пока нет строк результата."


def build_product_workspace_summary_text(state: LauncherAppState) -> str:
    """Build an always-visible product table summary."""
    products = product_items(state)
    shown_count = len(build_result_rows(state)) if products else 0
    selected_count = len(state.selection.selected_product_ids)
    return (
        f"\u0422\u043e\u0432\u0430\u0440\u044b: {len(products)} | "
        f"\u041f\u043e\u043a\u0430\u0437\u0430\u043d\u043e: {shown_count} | "
        f"\u0412\u044b\u0431\u0440\u0430\u043d\u043e: {selected_count}"
    )


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


def _append_result_context(lines: list[str], state: LauncherAppState) -> None:
    lines.extend(_result_context_parts(state))


def _result_context_parts(state: LauncherAppState) -> list[str]:
    table = build_result_table(state)
    rows = table.get("rows")
    row_count = len(rows) if isinstance(rows, list) else 0
    parts: list[str] = []
    products = product_items(state)
    empty_export_text = _empty_export_text(state)
    if products:
        parts.append(f"Показано {row_count} из {len(products)} товаров")
    if not products and empty_export_text:
        parts.append(empty_export_text)
    if row_count == 0:
        report_summary = _report_summary(state)
        category_counts = report_summary.get("category_counts") if isinstance(report_summary, dict) else None
        if isinstance(category_counts, dict):
            row_count = len(category_counts)
    if row_count and not products:
        parts.append(f"Строк показано: {row_count}")
    selected_count = len(state.selection.selected_product_ids)
    if selected_count:
        parts.append(f"Выбрано товаров: {selected_count}")
    active_filters = _active_filter_parts(state)
    if state.result.json_path and Path(state.result.json_path).exists() and not empty_export_text:
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u043e\u0442\u0444\u0438\u043b\u044c\u0442\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 JSON \u0432\u044b\u0433\u0440\u0443\u0437\u043a\u0438" if active_filters else "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: JSON \u0432\u044b\u0433\u0440\u0443\u0437\u043a\u0438")
    elif _report_summary(state):
        parts.append("\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: \u0441\u0432\u043e\u0434\u043a\u0430 \u043f\u043e \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u043e\u043c\u0443 \u043e\u0442\u0447\u0451\u0442\u0443")
    if state.result.json_path and Path(state.result.json_path).exists() and not empty_export_text:
        if selected_count:
            parts.append("\u041e\u0442\u0447\u0451\u0442 \u0431\u0443\u0434\u0435\u0442 \u043f\u043e\u0441\u0442\u0440\u043e\u0435\u043d \u043f\u043e \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u043c \u0442\u043e\u0432\u0430\u0440\u0430\u043c")
        elif row_count:
            parts.append("\u041c\u043e\u0436\u043d\u043e \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0435 \u0442\u043e\u0432\u0430\u0440\u044b \u043f\u0435\u0440\u0435\u0434 \u0441\u0431\u043e\u0440\u043a\u043e\u0439 Excel")
    if active_filters:
        parts.append(f"Активные фильтры: {', '.join(active_filters)}")
    return parts


def _empty_export_text(state: LauncherAppState) -> str:
    summary = state.result.summary
    if str(summary.get("products_count") or "") not in {"", "0"}:
        return ""
    attempt = summary.get("attempt")
    reason = str((attempt or {}).get("reason") or "") if isinstance(attempt, dict) else ""
    if not reason:
        return ""
    if "captcha" in reason or "challenge" in reason or "antibot" in reason:
        return f"Сбор остановлен защитой сайта: {reason}"
    return f"Сбор завершился без карточек товаров: {reason}"


def _active_filter_parts(state: LauncherAppState) -> list[str]:
    parts: list[str] = []
    for label, values in (
        ("поставщики", state.filters.suppliers),
        ("бренды", state.filters.brands),
        ("категории", state.filters.categories),
        ("подкатегории", state.filters.subcategories),
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
    return report_summary(state)


def _diagnostics(state: LauncherAppState) -> dict:
    return diagnostics_summary(state)


def _category_tree(state: LauncherAppState) -> list:
    return category_tree(state)


def _catalog_type(state: LauncherAppState) -> str:
    if state.catalog.catalog_type:
        return state.catalog.catalog_type
    discovery = catalog_discovery(state)
    return str(discovery.get("surface_type") or "") if isinstance(discovery, dict) else ""
