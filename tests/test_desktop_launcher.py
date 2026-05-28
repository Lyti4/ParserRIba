from pathlib import Path

import pytest

import launcher.desktop_launcher as desktop_launcher
import launcher.desktop_shell_helpers as desktop_shell_helpers


def test_load_pyside6_raises_clear_error_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import_module(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(desktop_shell_helpers, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match="PySide6 is not installed"):
        desktop_launcher.load_pyside6()


def test_desktop_launcher_shell_uses_local_settings_path(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)

    assert shell.root_dir == tmp_path
    assert shell.controller.settings_store.settings_path == tmp_path / "data" / "launcher_settings.json"
    assert shell.state.selection.shop == "pyaterochka"


def test_resolve_launcher_icon_path_points_inside_project(tmp_path: Path) -> None:
    icon_path = desktop_shell_helpers.resolve_launcher_icon_path(tmp_path)

    assert icon_path == tmp_path / "launcher" / "assets" / "parserriba_launcher.svg"


def test_resolve_launcher_icon_path_prefers_ico_when_available(tmp_path: Path) -> None:
    icon_dir = tmp_path / "launcher" / "assets"
    icon_dir.mkdir(parents=True)
    ico_path = icon_dir / "parserriba_launcher.ico"
    ico_path.write_bytes(b"ico")

    icon_path = desktop_shell_helpers.resolve_launcher_icon_path(tmp_path)

    assert icon_path == ico_path


def test_desktop_launcher_does_not_expose_raw_json_button(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.create_window()

    assert "open_json" not in shell.action_buttons


def test_desktop_launcher_wraps_controls_in_scroll_area(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()

    scroll_areas = window.findChildren(shell._qtwidgets.QScrollArea)

    assert window is not None
    assert scroll_areas


def test_desktop_launcher_exposes_workflow_tabs(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()

    tabs = window.findChild(shell._qtwidgets.QTabWidget)

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Исследование",
        "Каталог",
        "Товары",
        "Фильтры",
        "Отчёт",
    ]


def test_desktop_launcher_research_button_is_renamed(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.create_window()

    assert shell.action_buttons["onboarding"].text() == "Исследование"


def test_desktop_launcher_keeps_export_intent_out_of_research_tab(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()

    tabs = window.findChild(shell._qtwidgets.QTabWidget)
    research_labels = [item.text() for item in tabs.widget(0).findChildren(shell._qtwidgets.QLabel)]
    catalog_labels = [item.text() for item in tabs.widget(1).findChildren(shell._qtwidgets.QLabel)]

    assert "Раздел" not in research_labels
    assert "Тип сбора" not in catalog_labels
    assert shell.intent_combo is None


def test_desktop_launcher_does_not_autoselect_discovered_categories(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.catalog.full_tree = [
        {"name": "Рыба", "url": "https://example.test/fish"},
        {"name": "Морепродукты", "url": "https://example.test/seafood"},
    ]

    shell.create_window()

    assert shell.category_list.count() == 0
    assert shell.category_list.selectedItems() == []


def test_desktop_launcher_renders_full_catalog_tree_and_syncs_checked_nodes(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.catalog.full_tree = [
        {
            "name": "Каталог",
            "url": "https://5ka.ru/catalog/",
            "children": [
                {"name": "Рыба", "url": "https://5ka.ru/catalog/fish/", "children": []},
                {"name": "Морепродукты", "url": "https://5ka.ru/catalog/seafood/", "children": []},
            ],
        }
    ]

    shell.create_window()
    root = shell.catalog_tree.topLevelItem(0)
    root.child(1).setCheckState(0, shell._qt.CheckState.Checked)

    assert shell.catalog_tree.topLevelItemCount() == 1
    assert shell.state.selection.categories == ["Морепродукты"]
    assert shell.state.selection.selected_catalog_nodes == [
        {"name": "Морепродукты", "url": "https://5ka.ru/catalog/seafood/"}
    ]
    assert "выбрано 1: Морепродукты" in shell.catalog_context_label.text()
    assert "структура: плоский пул разделов" in shell.catalog_context_label.text()


def test_desktop_launcher_exposes_research_mode_widget(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.research.mode = "quiet"

    shell.create_window()

    assert shell.research_mode_combo is not None
    assert shell.research_mode_combo.currentData() == "quiet"


def test_desktop_launcher_updates_research_mode_from_widgets(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.create_window()

    shell.research_mode_combo.setCurrentIndex(shell.research_mode_combo.findData("quiet"))
    shell._update_state_from_widgets()

    assert shell.state.research.mode == "quiet"


def test_desktop_launcher_runs_long_actions_in_background_thread(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.create_window()

    scheduled: list[object] = []
    shell._start_background_action = lambda action: scheduled.append(action)

    shell._run_ui_action(lambda: "done")

    assert len(scheduled) == 1
    assert shell.state.task.status == "running"


def test_desktop_launcher_can_select_all_visible_products(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"fish-1","category":"Рыба","name":"Треска","brand":"Море","price":{"current":199.99},"in_stock":true},'
            '{"id":"fish-2","category":"Рыба","name":"Форель","brand":"Река","price":{"current":299.99},"in_stock":true}'
            ']}'
        ),
        encoding="utf-8",
    )
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.result.json_path = str(json_path)
    shell.create_window()

    shell._on_select_all_results()

    assert shell.state.selection.selected_product_ids == ["fish-1", "fish-2"]


def test_desktop_launcher_shows_selected_product_details(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"fish-1","category":"Рыба","name":"Треска","brand":"Море",'
            '"price":{"current":199.99},"in_stock":true,'
            '"product_link":"https://example.test/product/fish-1",'
            '"raw_data":{"supplier":"Океан","producer":"Завод","fat":"12%"}}'
            ']}'
        ),
        encoding="utf-8",
    )
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.result.json_path = str(json_path)
    shell.create_window()

    shell._on_select_all_results()

    details = shell.product_detail_text.toPlainText()
    assert "Товар: Треска" in details
    assert "Ссылка: https://example.test/product/fish-1" in details
    assert '"fat": "12%"' in details


def test_desktop_launcher_shows_product_details_from_structured_workspace(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.products.items = [
        {
            "id": "fish-1",
            "category": "Fish",
            "name": "Cod",
            "brand": "Nord",
            "price": {"current": 199.99},
            "in_stock": True,
            "product_link": "https://example.test/product/fish-1",
            "raw_data": {"supplier": "Nord supplier", "fat": "12%"},
        }
    ]
    shell.create_window()

    shell._on_select_all_results()

    details = shell.product_detail_text.toPlainText()
    assert "Cod" in details
    assert "https://example.test/product/fish-1" in details
    assert '"fat": "12%"' in details


def test_desktop_launcher_load_filters_populates_dynamic_filter_scroll(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.products.items = [
        {
            "id": "mayo-1",
            "category": "Майонез",
            "name": "Майонез 67",
            "brand": "Бренд",
            "raw_data": {"supplier": "Завод", "fat_percent": "67%"},
        }
    ]
    shell.create_window()

    shell._run_ui_action_sync_for_tests(shell.controller.load_filter_options)

    scroll_area = shell.window.findChild(shell._qtwidgets.QScrollArea, "launcherDynamicFiltersScrollArea")
    assert scroll_area is not None
    assert shell.filter_widgets["suppliers"].count() == 1
    assert shell.found_filter_widgets["fat_percent"].count() == 1
    assert "Фильтры построены по разделу:" in shell.filter_context_label.text()
    assert "товаров: 1" in shell.filter_context_label.text()


def test_desktop_launcher_apply_filters_updates_product_table(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.products.items = [
        {
            "id": "ice-1",
            "category": "Мороженое",
            "name": "Пломбир",
            "brand": "Бренд",
            "raw_data": {"supplier": "Фабрика"},
            "in_stock": True,
        },
        {
            "id": "mayo-1",
            "category": "Майонез",
            "name": "Майонез",
            "brand": "Бренд",
            "raw_data": {"supplier": "Завод"},
            "in_stock": True,
        },
    ]
    shell.state.dynamic_filters.counts = {
        "categories": {"Мороженое": 1, "Майонез": 1},
    }
    shell.create_window()
    category_widget = shell.filter_widgets["categories"]
    category_widget.item(0).setSelected(True)

    shell._on_apply_filters()

    table = shell.result_table
    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "Майонез"
    assert shell.state.filters.categories == ["Майонез"]
    assert "Показано товаров: 1" in shell.state.task.message


def test_desktop_launcher_show_all_products_clears_active_filters(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.products.items = [
        {
            "id": "ice-1",
            "category": "Мороженое",
            "name": "Пломбир",
            "brand": "Бренд",
            "raw_data": {"supplier": "Фабрика"},
            "in_stock": True,
        },
        {
            "id": "mayo-1",
            "category": "Майонез",
            "name": "Майонез",
            "brand": "Бренд",
            "raw_data": {"supplier": "Завод"},
            "in_stock": True,
        },
    ]
    shell.state.dynamic_filters.counts = {
        "categories": {"Мороженое": 1, "Майонез": 1},
    }
    shell.state.filters.categories = ["Майонез"]
    shell.create_window()

    shell._on_show_all_products()

    assert shell.result_table.rowCount() == 2
    assert shell.state.filters.categories == []
    assert shell.state.task.message == "Показаны все товары: 2."


def test_desktop_launcher_can_clear_selected_products(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        '{"products":[{"id":"fish-1","category":"Рыба","name":"Треска","brand":"Море","price":{"current":199.99},"in_stock":true}]}',
        encoding="utf-8",
    )
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.result.json_path = str(json_path)
    shell.state.selection.selected_product_ids = ["fish-1"]
    shell.create_window()

    shell._on_clear_selected_products()

    assert shell.state.selection.selected_product_ids == []
