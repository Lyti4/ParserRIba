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
