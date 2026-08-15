import json
from pathlib import Path

from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_user_messages import filters_refreshed_message
from models.task_actor import RunManifest
from utils.local_task_adapter import build_local_task_process_result


def test_desktop_launcher_controller_rebuilds_filters_from_collected_products(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.set_selection(intent="fish_catalog", categories=["Mayonnaise"])
    controller.state.products.items = [
        {
            "id": "mayo-1",
            "category": "Mayonnaise",
            "name": "Mayo 67",
            "brand": "Good Brand",
            "raw_data": {
                "supplier": "Factory One",
                "fat_percent": "67%",
                "package": "glass",
            },
        },
        {
            "id": "mayo-2",
            "category": "Mayonnaise",
            "name": "Mayo 50",
            "brand": "Good Brand",
            "raw_data": {
                "producer": "Factory Two",
                "fat_percent": "50%",
                "package": "doypack",
            },
        },
    ]

    result = controller.load_filter_options()

    assert result.manifest.task_name == "refresh_product_filters"
    assert controller.state.task.status == "succeeded"
    assert controller.state.task.message == filters_refreshed_message()
    assert controller.state.dynamic_filters.counts["suppliers"] == {
        "Factory One": 1,
        "Factory Two": 1,
    }
    assert controller.state.dynamic_filters.counts["brands"] == {"Good Brand": 2}
    assert controller.state.products.discovered_fields == {
        "fat_percent": {"50%": 1, "67%": 1},
        "package": {"doypack": 1, "glass": 1},
    }


def test_desktop_launcher_controller_refreshes_filters_from_exported_products_without_extra_task(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "products.json"

    def fake_export_runner(**kwargs):
        del kwargs
        json_path.write_text(
            json.dumps(
                {
                    "products_count": 1,
                    "products": [
                        {
                            "id": "mayo-1",
                            "category": "Mayonnaise",
                            "name": "Mayo 67",
                            "brand": "Good Brand",
                            "raw_data": {"supplier": "Factory One", "fat_percent": "67%"},
                            "in_stock": True,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="pyaterochka_fish_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={"json_path": str(json_path)},
                summary={"products_count": 1, "categories": ["Mayonnaise"]},
            )
        )

    def forbidden_filter_runner(**kwargs):
        del kwargs
        raise AssertionError("filters must be rebuilt from collected products")

    controller = DesktopLauncherController(
        root_dir=tmp_path,
        fish_export_runner=fake_export_runner,
        fish_filter_options_runner=forbidden_filter_runner,
    )
    controller.set_selection(intent="fish_catalog", categories=["Mayonnaise"])

    controller.run_selected_export()

    assert controller.state.products.products_count == 1
    assert controller.state.dynamic_filters.counts["categories"] == {"Mayonnaise": 1}
    assert controller.state.dynamic_filters.counts["suppliers"] == {"Factory One": 1}
    assert controller.state.products.discovered_fields == {"fat_percent": {"67%": 1}}
