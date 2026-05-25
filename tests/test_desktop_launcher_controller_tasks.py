import json
from pathlib import Path

from launcher.desktop_controller import DesktopLauncherController
from models.task_actor import RunManifest
from utils.local_task_adapter import build_local_task_process_result


def test_desktop_launcher_controller_passes_selected_products_to_report_runner(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_fish_report_runner(**kwargs):
        captured.update(kwargs)
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={"excel_path": str(tmp_path / "data" / "reports" / "fish.xlsx")},
                summary={"products_count": 1, "categories": ["Рыба"]},
            ),
            stderr="Task: store_report_export\nProducts: 1\n",
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_report_runner=fake_fish_report_runner)
    controller.set_selection(
        intent="fish_catalog",
        categories=["Рыба"],
        selected_product_ids=["fish-2", "fish-5"],
    )

    controller.run_selected_report_export()

    assert captured["categories"] == ["Рыба"]
    assert captured["selected_product_ids"] == ["fish-2", "fish-5"]
    assert captured["timeout_seconds"] == 120


def test_desktop_launcher_controller_passes_selected_catalog_node_urls_to_export(tmp_path: Path) -> None:
    captured: list[tuple[str, str]] = []

    def fake_fish_export_runner(**kwargs):
        captured.append((kwargs["category"], kwargs["category_url"]))
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="pyaterochka_fish_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={},
                summary={
                    "products_count": 0,
                    "categories": [kwargs["category"]],
                    "selected_categories": [kwargs["category"]],
                    "export_summary": {"products_count": 0, "categories": [kwargs["category"]]},
                },
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_export_runner=fake_fish_export_runner)
    controller.set_selection(
        intent="fish_catalog",
        categories=["Завтраки"],
        selected_catalog_nodes=[{"name": "Завтраки", "url": "https://5ka.ru/catalog/zavtraki--251C12891/"}],
    )

    controller.run_selected_export()

    assert captured == [("Завтраки", "https://5ka.ru/catalog/zavtraki--251C12891/")]


def test_desktop_launcher_controller_passes_bounded_task_timeout(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_onboarding_runner(**kwargs):
        captured.update(kwargs)
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="pyaterochka",
                intent="fish_catalog",
                status="runtime_ready",
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, onboarding_runner=fake_onboarding_runner)
    controller.set_settings({"listen_seconds": 15})

    controller.run_onboarding_discovery(site_url="https://5ka.ru")

    assert captured["listen_seconds"] == 15
    assert captured["timeout_seconds"] == 180


def test_desktop_launcher_controller_syncs_result_summary_and_artifacts(tmp_path: Path) -> None:
    def fake_fish_report_runner(**kwargs):
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
                summary={"products_count": 2, "categories": ["Рыба"]},
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_report_runner=fake_fish_report_runner)
    controller.set_selection(intent="fish_catalog", categories=["Рыба"])

    controller.run_selected_report_export()

    assert controller.state.result.summary == {"products_count": 2, "categories": ["Рыба"]}
    assert controller.state.result.artifact_paths == {
        "excel_path": str(tmp_path / "data" / "reports" / "fish.xlsx"),
        "json_path": str(tmp_path / "data" / "reports" / "fish.json"),
    }
    assert controller.state.result.excel_path.endswith("fish.xlsx")
    assert controller.state.result.json_path.endswith("fish.json")


def test_desktop_launcher_controller_hydrates_workspace_state_from_launcher_view(tmp_path: Path) -> None:
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
                    "active_profile_id": "profile-1",
                    "active_profile_version_id": "version-2",
                    "site_url": "https://5ka.ru",
                    "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
                    "full_catalog_tree": [{"name": "Каталог", "children": [{"name": "Рыба"}]}],
                    "full_catalog_links": [{"name": "Рыба", "url": "https://example.test/fish"}],
                    "products_count": 4,
                    "selected_categories": ["Рыба"],
                    "diagnostics_summary": {"known_backend": True},
                    "catalog_type": "category_tree",
                    "available_filter_counts": {"brands": {"Nord": 2}},
                    "found_filters": {"Производитель": {"Море": 1}},
                },
            ),
        )

    controller = DesktopLauncherController(root_dir=tmp_path, onboarding_runner=fake_onboarding_runner)
    controller.run_onboarding_discovery(site_url="https://5ka.ru")

    assert controller.state.profile.profile_id == "profile-1"
    assert controller.state.profile.profile_version_id == "version-2"
    assert controller.state.profile.shop == "pyaterochka"
    assert controller.state.profile.diagnostics["known_backend"] is True
    assert controller.state.catalog.full_tree == [{"name": "Каталог", "children": [{"name": "Рыба"}]}]
    assert controller.state.catalog.full_links == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert controller.state.catalog.catalog_type == "category_tree"
    assert controller.state.products.products_count == 4
    assert controller.state.products.source_categories == ["Рыба"]
    assert controller.state.products.discovered_fields == {"Производитель": {"Море": 1}}
    assert controller.state.dynamic_filters.counts == {"brands": {"Nord": 2}}
    assert controller.state.dynamic_filters.available_filters["brands"]["source"] == "available_filter_counts"
    assert controller.state.dynamic_filters.available_filters["Производитель"]["source"] == "found_filters"
    snapshot_path = Path(controller.state.result.artifact_paths["launcher_profile_snapshot_path"])
    snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot_path.exists()
    assert snapshot_payload["profile"]["site_url"] == "https://5ka.ru"
    assert snapshot_payload["catalog"]["full_tree"] == [{"name": "Каталог", "children": [{"name": "Рыба"}]}]


def test_desktop_launcher_controller_workspace_sync_is_additive(tmp_path: Path) -> None:
    def fake_fish_report_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                summary={"products_count": 1},
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_report_runner=fake_fish_report_runner)
    controller.state.profile.display_name = "Пятёрочка"
    controller.state.catalog.selected_nodes = [{"name": "Рыба", "url": "https://example.test/fish"}]
    controller.state.catalog.selected_node_urls = ["https://example.test/fish"]
    controller.state.dynamic_filters.available_filters = {"old": {"source": "previous"}}
    controller.state.dynamic_filters.counts = {"old": {"value": 1}}
    controller.state.dynamic_filters.missing_fields = ["old"]
    controller.state.dynamic_filters.applied_values = {"brand": ["Nord"]}
    controller.set_selection(intent="fish_catalog", categories=["Рыба"], selected_product_ids=["fish-1"])
    controller.set_filters({"brands": ["Nord"]})

    controller.run_selected_report_export()

    assert controller.state.profile.display_name == "Пятёрочка"
    assert controller.state.catalog.selected_nodes == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert controller.state.catalog.selected_node_urls == ["https://example.test/fish"]
    assert controller.state.products.selected_product_ids == ["fish-1"]
    assert controller.state.dynamic_filters.applied_values == {"brand": ["Nord"]}
    assert controller.state.dynamic_filters.available_filters == {}
    assert controller.state.dynamic_filters.counts == {}
    assert controller.state.dynamic_filters.missing_fields == []
    assert controller.state.result.filter_snapshot["brands"] == ["Nord"]
