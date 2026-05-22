"""User-facing Russian UI text for the desktop launcher."""

from __future__ import annotations


WINDOW_TITLE = "ParserRIba Лаунчер"
LAUNCHER_TITLE = "ParserRIba Desktop Launcher"

SHOP_LABELS = {
    "pyaterochka": "Пятёрочка",
}

INTENT_LABELS = {
    "fish_catalog": "Рыбная продукция",
    "wine_catalog": "Вино",
}

TASK_STATUS_LABELS = {
    "idle": "ожидание",
    "running": "выполняется",
    "succeeded": "успешно",
    "failed": "ошибка",
}

TASK_NAME_LABELS = {
    "site_onboarding_discovery": "Исследование магазина",
    "pyaterochka_fish_export": "Сбор товаров",
    "pyaterochka_wine_export": "Сбор товаров",
    "store_report_filter_options": "Загрузка фильтров",
    "store_report_export": "Сбор Excel",
}

FILTER_TITLES = {
    "suppliers": "Поставщики",
    "brands": "Бренды",
    "wine_styles": "Тип вина",
    "alcohol_types": "Алкогольный тип",
    "sugar_classes": "Сахар",
    "colors": "Цвет",
}

RESEARCH_MODE_LABELS = {
    "live": "Пошаговое исследование",
    "quiet": "Только итоговый результат",
}

RESEARCH_PHASE_LABELS = {
    "open_site": "Открытие сайта",
    "collect_surface": "Поиск структуры каталога",
    "validate_nodes": "Проверка разделов",
    "collect_hints": "Сбор признаков и маршрутов",
    "persist_profile": "Сохранение профиля",
    "build_tree": "Подготовка дерева",
}

STOCK_OPTION_ANY = "Любое"
STOCK_OPTION_IN_STOCK = "В наличии"
STOCK_OPTION_OUT_OF_STOCK = "Нет в наличии"

RESULT_TABLE_HEADERS = [
    "Категория",
    "Товар",
    "Бренд",
    "Поставщик",
    "Тип",
    "Алкогольный тип",
    "Цена",
    "В наличии",
    "Ссылка",
]

REPORT_TABLE_HEADERS = ["Категория", "Товаров", "Топ поставщик", "Топ бренд"]


def display_shop(value: str) -> str:
    """Return one Russian display label for a store code."""
    return SHOP_LABELS.get(value, value)


def display_intent(value: str) -> str:
    """Return one Russian display label for an intent code."""
    return INTENT_LABELS.get(value, value)


def display_task_status(value: str) -> str:
    """Return one Russian display label for a task status."""
    return TASK_STATUS_LABELS.get(value, value)


def display_task_name(value: str) -> str:
    """Return one Russian display label for an internal task name."""
    return TASK_NAME_LABELS.get(value, value)


def display_research_mode(value: str) -> str:
    """Return one Russian display label for a research mode."""
    return RESEARCH_MODE_LABELS.get(value, value or "не задан")


def display_research_phase(value: str) -> str:
    """Return one Russian display label for a research phase."""
    return RESEARCH_PHASE_LABELS.get(value, value or "не указан")


def display_stock_label(in_stock: bool) -> str:
    """Return one Russian stock label for a table row."""
    return STOCK_OPTION_IN_STOCK if in_stock else STOCK_OPTION_OUT_OF_STOCK
