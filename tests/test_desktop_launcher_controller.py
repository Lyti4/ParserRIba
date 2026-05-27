import json
from pathlib import Path

import pytest

from launcher.desktop_controller import DesktopLauncherController, open_path_with_system_handler
from launcher.desktop_controller_helpers import selected_export_categories
from launcher.desktop_user_messages import (
    empty_filter_options_message,
    no_selected_categories_message,
    no_output_path_message,
    opened_path_message,
    settings_saved_message,
)
from models.task_actor import RunManifest
from utils.local_task_adapter import build_local_task_process_result


def test_desktop_launcher_controller_updates_selection_and_filters(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)

    controller.set_selection(shop="pyaterochka", intent="wine_catalog", categories=["Безалкогольное вино"])
    controller.set_filters({"suppliers": ["Free Feather"], "strict_missing": True})
    controller.set_settings({"headless": False, "listen_seconds": 12})

    assert controller.state.selection.intent == "wine_catalog"
    assert controller.state.selection.categories == ["Безалкогольное вино"]
    assert controller.state.filters.suppliers == ["Free Feather"]
    assert controller.state.filters.strict_missing is True
    assert controller.state.settings.headless is False
    assert controller.state.settings.listen_seconds == 12


def test_desktop_launcher_controller_shows_no_categories_before_research(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.state.result.launcher_view = {}

    assert controller.list_available_categories() == []


def test_desktop_launcher_controller_prefers_discovered_categories_for_matching_target(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.state.result.launcher_view = {
        "shop": "pyaterochka",
        "intent": "fish_catalog",
        "category_tree": [
            {"name": "Рыба", "url": "https://example.test/fish"},
            {"name": "Морепродукты", "url": "https://example.test/seafood"},
        ],
    }

    assert controller.list_available_categories() == ["Рыба", "Морепродукты"]


def test_desktop_launcher_controller_reads_available_categories_from_structured_catalog(
    tmp_path: Path,
) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.state.result.launcher_view = {}
    controller.state.catalog.full_tree = [
        {
            "name": "Каталог",
            "url": "https://example.test/catalog/",
            "children": [
                {"name": "Готовая еда", "url": "https://example.test/catalog/ready/"},
                {"name": "Рыба", "url": "https://example.test/catalog/fish/"},
            ],
        }
    ]

    assert controller.list_available_categories() == ["Готовая еда", "Рыба"]


def test_desktop_launcher_controller_prefers_summary_categories_over_catalog_root(
    tmp_path: Path,
) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.state.result.summary = {
        "category_tree": [
            {"name": "Морепродукты", "url": "https://example.test/catalog/seafood/"}
        ]
    }
    controller.state.catalog.full_tree = [
        {
            "name": "Каталог",
            "children": [
                {"name": "Готовая еда", "url": "https://example.test/catalog/ready/"}
            ],
        }
    ]

    assert controller.list_available_categories() == ["Морепродукты"]


def test_desktop_launcher_controller_ignores_stale_discovery_for_other_intent(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.set_selection(intent="wine_catalog")
    controller.state.result.launcher_view = {
        "shop": "pyaterochka",
        "intent": "fish_catalog",
        "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
    }

    assert controller.list_available_categories() == []


def test_desktop_launcher_controller_applies_report_export_result(tmp_path: Path) -> None:
    def fake_wine_report_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="wine_catalog",
                status="ok",
                artifact_paths={
                    "excel_path": str(tmp_path / "data" / "reports" / "wine.xlsx"),
                    "manifest_path": str(tmp_path / "data" / "reports" / "manifest.json"),
                },
                summary={
                    "products_count": 1,
                    "categories": ["Безалкогольное вино"],
                    "report_summary": {
                        "products_count": 1,
                        "categories": ["Безалкогольное вино"],
                        "category_counts": {"Безалкогольное вино": 1},
                        "supplier_counts": {"Free Feather": 1},
                        "brand_counts": {"Free Feather": 1},
                        "wine_breakdown": {
                            "style_counts": {"Тихое": 1},
                            "alcohol_type_counts": {"Безалкогольное": 1},
                            "sugar_class_counts": {"Полусладкое": 1},
                            "color_counts": {"Белое": 1},
                        },
                    },
                },
            ),
            stderr="Task: store_report_export\nProducts: 1\n",
        )

    controller = DesktopLauncherController(root_dir=tmp_path, wine_report_runner=fake_wine_report_runner)
    controller.set_selection(intent="wine_catalog", categories=["Безалкогольное вино"])

    result = controller.run_selected_report_export()

    assert result.manifest.task_name == "store_report_export"
    assert controller.state.task.status == "succeeded"
    assert controller.state.result.excel_path.endswith("wine.xlsx")
    assert controller.state.result.report_dir.endswith("reports")
    assert controller.state.result.launcher_view["report_summary"]["supplier_counts"] == {"Free Feather": 1}


def test_desktop_launcher_controller_marks_failure_state(tmp_path: Path) -> None:
    def failing_runner(**kwargs):
        del kwargs
        raise RuntimeError("boom")

    controller = DesktopLauncherController(root_dir=tmp_path, wine_report_runner=failing_runner)
    controller.set_selection(intent="wine_catalog")

    with pytest.raises(RuntimeError, match="boom"):
        controller.run_selected_report_export()

    assert controller.state.task.status == "failed"
    assert controller.state.task.task_name == "store_report_export"
    assert controller.state.task.last_error == "boom"


def test_selected_export_categories_does_not_inject_default_category() -> None:
    assert selected_export_categories([], "fish_catalog") == []
    assert selected_export_categories([" Рыба ", ""], "fish_catalog") == ["Рыба"]


def test_desktop_launcher_controller_rejects_export_without_selected_categories(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.set_selection(intent="fish_catalog", categories=[])

    with pytest.raises(ValueError, match=no_selected_categories_message()):
        controller.run_selected_export()

    assert controller.state.task.status == "failed"
    assert controller.state.task.message == no_selected_categories_message()


def test_desktop_launcher_controller_runs_selected_export_for_every_category(tmp_path: Path) -> None:
    seen_categories: list[str] = []
    json_dir = tmp_path / "data"
    json_dir.mkdir(parents=True)

    def fake_fish_export_runner(**kwargs):
        assert kwargs["expand_intent"] is False
        category_name = kwargs["category"]
        seen_categories.append(category_name)
        json_path = json_dir / f"{category_name}.json"
        json_path.write_text(
            (
                '{"products":[{"category":"%s","name":"Product %s","brand":"Brand %s",'
                '"subcategory":"Style %s","raw_data":{"supplier":"Supplier %s","alcohol_type":"Безалкогольное","country":"Норвегия"}}]}'
            )
            % (category_name, category_name, category_name, category_name, category_name),
            encoding="utf-8",
        )
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="pyaterochka_fish_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={"json_path": str(json_path)},
                summary={
                    "products_count": 2,
                    "categories": [category_name],
                    "export_summary": {
                        "products_count": 2,
                        "categories": [category_name],
                    },
                },
            ),
            stderr="Task: pyaterochka_fish_export\nProducts: 2\n",
        )

    def fake_filter_runner(**kwargs):
        assert kwargs["categories"] == ["Рыба", "Морепродукты"]
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_filter_options",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={},
                summary={
                    "available_filter_counts": {
                        "suppliers": {"Supplier Рыба": 1, "Supplier Морепродукты": 1},
                    }
                },
            )
        )

    controller = DesktopLauncherController(
        root_dir=tmp_path,
        fish_export_runner=fake_fish_export_runner,
        fish_filter_options_runner=fake_filter_runner,
    )
    controller.set_selection(intent="fish_catalog", categories=["Рыба", "Морепродукты"])

    result = controller.run_selected_export()

    assert seen_categories == ["Рыба", "Морепродукты"]
    assert result.export_summary is not None
    assert result.export_summary["products_count"] == 4
    assert result.export_summary["categories"] == ["Рыба", "Морепродукты"]
    assert controller.state.result.json_path.endswith("_selected.json")
    combined_payload = json.loads(Path(controller.state.result.json_path).read_text(encoding="utf-8"))
    assert len(controller.state.products.items) == combined_payload["products_count"] == 2
    assert len(combined_payload["products"]) == 2
    assert controller.state.result.launcher_view["available_filter_counts"]["suppliers"] == {
        "Supplier Рыба": 1,
        "Supplier Морепродукты": 1,
    }
    assert controller.state.dynamic_filters.counts["suppliers"] == {
        "Supplier Рыба": 1,
        "Supplier Морепродукты": 1,
    }
    assert controller.state.products.discovered_fields == {"country": {"Норвегия": 2}}


def test_desktop_launcher_controller_save_settings_sets_message(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)

    settings_path = controller.save_settings()

    assert settings_path == tmp_path / "data" / "launcher_settings.json"
    assert controller.state.task.message == settings_saved_message()


def test_desktop_launcher_controller_open_json_without_target_sets_message(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)

    opened = controller.open_json()

    assert opened is False
    assert controller.state.task.message == no_output_path_message()


def test_desktop_launcher_controller_open_excel_uses_injected_path_opener(tmp_path: Path) -> None:
    opened_paths: list[str] = []

    def fake_opener(path: str) -> None:
        opened_paths.append(path)

    controller = DesktopLauncherController(root_dir=tmp_path, path_opener=fake_opener)
    controller.state.result.excel_path = str(tmp_path / "data" / "reports" / "fish.xlsx")

    opened = controller.open_excel()

    assert opened is True
    assert opened_paths == [controller.state.result.excel_path]
    assert controller.state.task.message == opened_path_message(controller.state.result.excel_path)


def test_open_path_with_system_handler_uses_linux_opener(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_popen(command: list[str]) -> None:
        captured["command"] = command

    monkeypatch.setattr("launcher.desktop_controller.sys.platform", "linux")
    monkeypatch.setattr("launcher.desktop_controller.subprocess.Popen", fake_popen)

    open_path_with_system_handler("/tmp/report.xlsx")

    assert captured["command"] == ["xdg-open", "/tmp/report.xlsx"]


def test_desktop_launcher_controller_preserves_report_result_when_loading_filters(tmp_path: Path) -> None:
    def fake_report_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={
                    "excel_path": str(tmp_path / "data" / "reports" / "fish.xlsx"),
                    "json_path": str(tmp_path / "data" / "reports" / "fish.json"),
                },
                summary={
                    "report_summary": {
                        "products_count": 2,
                        "categories": ["Рыба"],
                        "category_counts": {"Рыба": 2},
                    }
                },
            ),
            stderr="Task: store_report_export\nProducts: 2\n",
        )

    def fake_filter_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_filter_options",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={},
                summary={"available_filter_counts": {"suppliers": {"Море": 2}}},
            ),
            stderr="Task: store_report_filter_options\n",
        )

    controller = DesktopLauncherController(
        root_dir=tmp_path,
        fish_report_runner=fake_report_runner,
        fish_filter_options_runner=fake_filter_runner,
    )
    controller.set_selection(intent="fish_catalog", categories=["Рыба"])

    controller.run_selected_report_export()
    controller.load_filter_options()

    assert controller.state.result.excel_path.endswith("fish.xlsx")
    assert controller.state.result.json_path.endswith("fish.json")
    assert controller.state.result.launcher_view["report_summary"]["products_count"] == 2
    assert controller.state.result.launcher_view["available_filter_counts"]["suppliers"] == {"Море": 2}
    assert controller.state.dynamic_filters.counts["suppliers"] == {"Море": 2}


def test_desktop_launcher_controller_explains_empty_filter_options(tmp_path: Path) -> None:
    def fake_filter_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_filter_options",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={},
                summary={
                    "available_filter_counts": {
                        "categories": {"Рыба": 12},
                        "suppliers": {},
                        "brands": {},
                    }
                },
            ),
            stderr="Task: store_report_filter_options\n",
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_filter_options_runner=fake_filter_runner)
    controller.set_selection(intent="fish_catalog", categories=["Рыба"])

    controller.load_filter_options()

    assert controller.state.task.message == empty_filter_options_message()


def test_desktop_launcher_controller_store_research_clears_stale_report_state(tmp_path: Path) -> None:
    def fake_onboarding_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="pyaterochka",
                intent="fish_catalog",
                status="runtime_ready",
                artifact_paths={},
                summary={
                    "category_count": 2,
                    "category_tree": [
                        {"name": "Рыба", "url": "https://example.test/fish"},
                        {"name": "Морепродукты", "url": "https://example.test/seafood"},
                    ],
                    "catalog_discovery": {"surface_type": "category_tree"},
                },
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, onboarding_runner=fake_onboarding_runner)
    controller.state.result.excel_path = "C:/tmp/reports/old.xlsx"
    controller.state.result.json_path = "C:/tmp/reports/old.json"
    controller.state.result.report_dir = "C:/tmp/reports"
    controller.state.result.launcher_view = {
        "report_summary": {"products_count": 105, "category_counts": {"Рыба": 105}},
        "available_filter_counts": {"suppliers": {"Море": 7}},
    }

    controller.run_onboarding_discovery(site_url="https://5ka.ru")

    assert controller.state.result.excel_path == ""
    assert controller.state.result.json_path == ""
    assert controller.state.result.report_dir == ""
    assert "report_summary" not in controller.state.result.launcher_view
    assert controller.state.result.launcher_view["category_tree"] == [
        {"name": "Рыба", "url": "https://example.test/fish"},
        {"name": "Морепродукты", "url": "https://example.test/seafood"},
    ]
    assert controller.state.task.message == (
        "Исследование магазина завершено. Найдено разделов: 2 Текущая фаза: Открытие сайта"
    )
def test_desktop_launcher_controller_clears_selected_products_when_categories_change(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)

    controller.set_selection(categories=["Рыба"], selected_product_ids=["fish-1", "fish-2"])
    controller.set_selection(categories=["Морепродукты"])

    assert controller.state.selection.categories == ["Морепродукты"]
    assert controller.state.selection.selected_product_ids == []

