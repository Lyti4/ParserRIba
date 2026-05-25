"""User-facing desktop launcher messages."""

from __future__ import annotations


def friendly_error_message(error: Exception) -> str:
    """Map low-level exceptions to concise desktop-friendly text."""
    message = str(error or "").strip()
    lowered = message.casefold()
    if "pyside6 is not installed" in lowered:
        return "PySide6 не установлен. Установи desktop-зависимости перед запуском лаунчера."
    if "unsupported local task" in lowered:
        return "Выбранное действие лаунчера сейчас недоступно."
    if "no such file" in lowered or "cannot find the file" in lowered:
        return "Нужный локальный файл или отчёт не найден."
    if "timeout" in lowered:
        return "Операция превысила допустимое время ожидания."
    if "captcha" in lowered or "challenge" in lowered:
        return "Сайт запросил ручную проверку. Нужна помощь оператора."
    if message:
        return message
    return "Действие лаунчера завершилось ошибкой."


def no_output_path_message() -> str:
    """Return one friendly message for missing artifact paths."""
    return "Пока нет файла или папки для открытия."


def no_selected_categories_message() -> str:
    """Return one friendly message when product collection has no selected nodes."""
    return "Сначала выберите один или несколько разделов каталога."


def settings_saved_message() -> str:
    """Return one friendly message for persisted launcher settings."""
    return "Настройки лаунчера сохранены."


def task_running_message(task_name: str) -> str:
    """Return one user-facing message for a running launcher task."""
    return f"Выполняется: {task_name}"


def task_completed_message(task_name: str) -> str:
    """Return one user-facing message for a completed launcher task."""
    return f"Завершено: {task_name}"


def task_progress_message(task_name: str, category_name: str, index: int, total: int) -> str:
    """Return one progress message for a multi-category export."""
    return f"Выполняется: {task_name} [{index}/{total}] — {category_name}"


def empty_filter_options_message() -> str:
    """Explain why the filter panel has no useful values yet."""
    return "Пока доступны только категории. Сначала собери товары, чтобы появились поставщики, бренды и другие фильтры."


def opened_path_message(path: str) -> str:
    """Return one user-facing message for an opened file or folder."""
    return f"Открыто: {path}"
