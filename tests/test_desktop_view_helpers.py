from pathlib import Path

from launcher.desktop_view_helpers import (
    build_result_caption_text,
    build_result_rows,
    build_status_text,
    build_summary_text,
)
from models.launcher_state import LauncherAppState


def test_build_status_text_uses_russian_task_labels() -> None:
    state = LauncherAppState()
    state.selection.shop = "pyaterochka"
    state.selection.intent = "wine_catalog"
    state.task.task_name = "store_report_export"
    state.task.status = "running"

    text = build_status_text(state)

    assert "Магазин: Пятёрочка" in text
    assert "Раздел:" not in text
    assert "Задача: Сбор Excel" in text
    assert "Статус: выполняется" in text
    assert "Режим исследования: Пошаговое исследование" in text
    assert "Интерфейс: занят" in text


def test_build_result_rows_reads_export_json(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        '{"products":[{"category":"Рыба","name":"Треска","brand":"Море","price":{"current":199.99},"in_stock":true}]}',
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)

    rows = build_result_rows(state)

    assert rows == [["Рыба", "Треска", "Море", "Море", "", "", "199.99", "В наличии", ""]]


def test_build_result_rows_falls_back_to_report_summary() -> None:
    state = LauncherAppState()
    state.result.launcher_view = {
        "report_summary": {
            "category_counts": {
                "Рыба": 10,
                "Морепродукты": 5,
            }
        }
    }

    rows = build_result_rows(state)

    assert rows == [
        ["Рыба", "10", "", ""],
        ["Морепродукты", "5", "", ""],
    ]


def test_build_summary_text_uses_report_and_filter_data() -> None:
    state = LauncherAppState()
    state.task.message = "Готово"
    state.result.excel_path = "C:/tmp/reports/fish.xlsx"
    state.result.json_path = "C:/tmp/reports/fish.json"
    state.filters.suppliers = ["Море", "Океан"]
    state.filters.strict_missing = True
    state.result.launcher_view = {
        "report_summary": {
            "products_count": 12,
            "categories": ["Рыба", "Морепродукты"],
            "category_counts": {"Рыба": 7, "Морепродукты": 5},
            "supplier_counts": {"Море": 7, "Океан": 5, "Река": 2},
        },
        "available_filter_counts": {
            "suppliers": {"Море": 7, "Океан": 5},
        },
    }

    summary = build_summary_text(state)
    caption = build_result_caption_text(state)

    assert "Готово" in summary
    assert "Файл Excel: fish.xlsx" in summary
    assert "Файл JSON: fish.json" in summary
    assert "Товаров в отчёте" not in summary
    assert "Строк показано: 2" in caption
    assert "Источник: сводка по сохранённому отчёту" in caption
    assert "Активные фильтры: поставщики=2, строгий режим=1" in caption


def test_build_summary_text_includes_running_hint_and_last_error() -> None:
    state = LauncherAppState()
    state.task.status = "running"
    state.task.last_error = "proxy timeout"

    summary = build_summary_text(state)

    assert "Лаунчер ожидает завершения текущего действия." in summary
    assert "Последняя ошибка: proxy timeout" in summary


def test_build_summary_text_keeps_export_breakdown_out_of_research_summary() -> None:
    state = LauncherAppState()
    state.result.launcher_view = {
        "export_summary": {
            "products_count": 4,
            "wine_breakdown": {
                "style_counts": {"Тихое": 3, "Игристое": 1},
                "alcohol_type_counts": {"Безалкогольное": 4},
                "sugar_class_counts": {"Полусладкое": 2, "Сухое": 2},
                "color_counts": {"Белое": 3, "Красное": 1},
            },
        }
    }

    summary = build_summary_text(state)

    assert "Товаров в выгрузке" not in summary
    assert "Типы вина" not in summary


def test_build_summary_text_marks_report_summary_source() -> None:
    state = LauncherAppState()
    state.result.launcher_view = {
        "report_summary": {
            "products_count": 2,
            "category_counts": {"Рыба": 2},
        }
    }

    summary = build_summary_text(state)
    caption = build_result_caption_text(state)

    assert "Строк показано: 1" not in summary
    assert "Строк показано: 1" in caption
    assert "Источник: сводка по сохранённому отчёту" in caption


def test_build_result_caption_text_renders_result_context() -> None:
    state = LauncherAppState()
    state.filters.suppliers = ["Море"]
    state.result.launcher_view = {
        "report_summary": {
            "category_counts": {"Рыба": 2},
        }
    }

    caption = build_result_caption_text(state)

    assert "Строк показано: 1" in caption
    assert "Источник: сводка по сохранённому отчёту" in caption
    assert "Активные фильтры: поставщики=1" in caption


def test_build_result_caption_text_marks_filtered_export_json(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        '{"products":[{"category":"Вино","name":"OddBird","brand":"OddBird","price":{"current":699.99},"in_stock":true}]}',
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)
    state.filters.brands = ["OddBird"]

    caption = build_result_caption_text(state)

    assert "Строк показано: 1" in caption
    assert "Источник: отфильтрованный JSON выгрузки" in caption
    assert "Активные фильтры: бренды=1" in caption


def test_build_result_caption_text_shows_selected_product_scope(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        '{"products":[{"id":"wine-1","category":"Вино","name":"OddBird","brand":"OddBird","price":{"current":699.99},"in_stock":true}]}',
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)
    state.selection.selected_product_ids = ["wine-1"]

    caption = build_result_caption_text(state)

    assert "Выбрано товаров: 1" in caption
    assert "Отчёт будет построен по выбранным товарам" in caption


def test_build_result_caption_text_prompts_for_explicit_product_selection(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        '{"products":[{"id":"wine-1","category":"Вино","name":"OddBird","brand":"OddBird","price":{"current":699.99},"in_stock":true}]}',
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)

    caption = build_result_caption_text(state)

    assert "Можно выбрать конкретные товары перед сборкой Excel" in caption


def test_build_summary_text_shows_store_research_result() -> None:
    state = LauncherAppState()
    state.task.message = "Исследование магазина завершено. Найдено разделов: 2"
    state.research.current_phase = "build_tree"
    state.research.active_profile_id = "profile-1"
    state.research.active_profile_version_id = "version-2"
    state.research.streamed_categories = ["Рыба", "Морепродукты"]
    state.result.launcher_view = {
        "category_tree": [
            {"name": "Рыба", "url": "https://example.test/fish"},
            {"name": "Морепродукты", "url": "https://example.test/seafood"},
        ],
        "catalog_discovery": {"surface_type": "category_tree"},
    }

    summary = build_summary_text(state)
    caption = build_result_caption_text(state)

    assert "Исследование магазина завершено. Найдено разделов: 2" in summary
    assert "Текущий этап: Подготовка дерева" in summary
    assert "Активный профиль: profile-1 / version-2" in summary
    assert "Поток разделов: Рыба, Морепродукты" in summary
    assert "Тип каталога: category_tree" in summary
    assert "Разделов каталога найдено: 2" in summary
    assert "Найденные разделы: Рыба, Морепродукты" in summary
    assert "Источник: исследование магазина" in caption


def test_build_summary_text_shows_full_catalog_result() -> None:
    state = LauncherAppState()
    state.result.launcher_view = {
        "full_catalog_tree": [
            {
                "name": "Каталог",
                "url": "https://example.test/catalog",
                "children": [{"name": "Рыба", "url": "https://example.test/catalog/fish", "children": []}],
            }
        ],
        "full_catalog_links": [
            {"name": "Каталог", "url": "https://example.test/catalog"},
            {"name": "Рыба", "url": "https://example.test/catalog/fish"},
        ],
        "catalog_discovery": {"surface_type": "category_tree"},
    }

    summary = build_summary_text(state)
    rows = build_result_rows(state)
    caption = build_result_caption_text(state)

    assert "Полный каталог: найдено URL разделов: 2" in summary
    assert "Первые разделы полного каталога: Каталог, Рыба" in summary
    assert rows == [
        ["0", "Каталог", "https://example.test/catalog", "1"],
        ["1", "Рыба", "https://example.test/catalog/fish", "0"],
    ]
    assert "Источник: полный каталог исследования" in caption


def test_build_summary_text_hides_quiet_stream_until_completion() -> None:
    state = LauncherAppState()
    state.research.mode = "quiet"
    state.research.current_phase = "persist_profile"
    state.result.launcher_view = {
        "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
    }

    summary = build_summary_text(state)

    assert "Режим исследования: Только итоговый результат" in summary
    assert "Текущий этап: Сохранение профиля" in summary
    assert "Поток разделов скрыт до завершения исследования." in summary
