from pathlib import Path

from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_user_messages import filters_refreshed_message


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
