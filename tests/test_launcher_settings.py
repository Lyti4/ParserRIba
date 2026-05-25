import json
from pathlib import Path

from models.launcher_state import LauncherAppState, LauncherSettingsState
from utils.launcher_settings import LauncherSettingsStore


def test_launcher_settings_store_saves_and_loads_settings(tmp_path: Path) -> None:
    store = LauncherSettingsStore(tmp_path / "launcher_settings.json")
    settings = LauncherSettingsState(
        output_dir="C:/reports",
        headless=False,
        manual_wait=True,
        attempts=2,
        listen_seconds=10,
    )

    path = store.save(settings)
    loaded = store.load()

    assert path.exists()
    assert loaded.output_dir == "C:/reports"
    assert loaded.headless is False
    assert loaded.manual_wait is True
    assert loaded.attempts == 2
    assert loaded.listen_seconds == 10


def test_launcher_settings_store_saves_and_loads_app_state(tmp_path: Path) -> None:
    store = LauncherSettingsStore(tmp_path / "launcher_state.json")
    state = LauncherAppState()
    state.selection.shop = "metro"
    state.selection.intent = "fish_catalog"
    state.selection.categories = ["Рыба"]
    state.selection.selected_catalog_nodes = [{"name": "Рыба", "url": "https://example.test/fish"}]
    state.selection.selected_product_ids = ["fish-1"]
    state.task.status = "running"
    state.task.message = "busy"
    state.result.excel_path = "C:/reports/fish.xlsx"

    store.save_app_state(state)
    loaded = store.load_app_state()

    assert loaded.selection.shop == "metro"
    assert loaded.selection.categories == []
    assert loaded.selection.selected_catalog_nodes == []
    assert loaded.selection.selected_product_ids == []
    assert loaded.task.status == "idle"
    assert loaded.task.message == ""
    assert loaded.result.excel_path == "C:/reports/fish.xlsx"


def test_launcher_settings_store_loads_legacy_settings_only_json(tmp_path: Path) -> None:
    settings_path = tmp_path / "launcher_state.json"
    settings_path.write_text(
        json.dumps({"settings": {"headless": False, "listen_seconds": 12}}, ensure_ascii=False),
        encoding="utf-8",
    )
    store = LauncherSettingsStore(settings_path)

    loaded_settings = store.load()
    loaded_state = store.load_app_state()

    assert loaded_settings.headless is False
    assert loaded_settings.listen_seconds == 12
    assert loaded_state.settings.headless is False
    assert loaded_state.profile.profile_id == ""
    assert loaded_state.catalog.full_tree == []
    assert loaded_state.products.products_count == 0


def test_launcher_settings_store_preserves_profile_and_clears_transient_workspace(tmp_path: Path) -> None:
    store = LauncherSettingsStore(tmp_path / "launcher_state.json")
    state = LauncherAppState(
        profile={"profile_id": "profile-1", "domain": "5ka.ru", "display_name": "Пятёрочка"},
        catalog={
            "full_tree": [{"name": "Каталог"}],
            "selected_nodes": [{"name": "Рыба"}],
            "selected_node_urls": ["https://5ka.ru/catalog/ryba/"],
        },
        products={
            "products_count": 3,
            "source_categories": ["Рыба"],
            "selected_product_ids": ["fish-1"],
        },
        dynamic_filters={"available_filters": {"brand": {"kind": "multi_select"}}},
    )

    store.save_app_state(state)
    loaded = store.load_app_state()

    assert loaded.profile.profile_id == "profile-1"
    assert loaded.catalog.full_tree == [{"name": "Каталог"}]
    assert loaded.catalog.selected_nodes == []
    assert loaded.catalog.selected_node_urls == []
    assert loaded.products.products_count == 3
    assert loaded.products.source_categories == ["Рыба"]
    assert loaded.products.selected_product_ids == []
    assert loaded.dynamic_filters.available_filters == {"brand": {"kind": "multi_select"}}
