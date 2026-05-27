import json

from models.launcher_state import LauncherAppState, LauncherSettingsState


def test_launcher_app_state_has_desktop_defaults() -> None:
    state = LauncherAppState()

    assert state.selection.shop == "pyaterochka"
    assert state.selection.intent == "fish_catalog"
    assert state.selection.selected_product_ids == []
    assert state.settings.headless is True
    assert state.settings.manual_wait is False
    assert state.task.status == "idle"
    assert state.research.mode == "live"
    assert state.research.current_phase == ""
    assert state.research.streamed_categories == []
    assert state.research.active_profile_id == ""
    assert state.profile.profile_id == ""
    assert state.catalog.full_tree == []
    assert state.products.products_count == 0
    assert state.products.items == []
    assert state.dynamic_filters.available_filters == {}
    assert state.task.progress_current == 0
    assert state.result.launcher_view == {}
    assert state.result.summary == {}


def test_launcher_settings_state_allows_desktop_overrides() -> None:
    settings = LauncherSettingsState(
        output_dir="C:/tmp/ParserRIba-clean/data/reports",
        headless=False,
        attempts=3,
        listen_seconds=15,
    )

    assert settings.output_dir.endswith("data/reports")
    assert settings.headless is False
    assert settings.attempts == 3
    assert settings.listen_seconds == 15


def test_launcher_app_state_supports_research_overrides() -> None:
    state = LauncherAppState(
        research={
            "mode": "quiet",
            "current_phase": "build_tree",
            "current_status": "running",
            "streamed_categories": ["Рыба", "Морепродукты"],
            "active_profile_id": "profile-1",
            "active_profile_version_id": "version-3",
        }
    )

    assert state.research.mode == "quiet"
    assert state.research.current_phase == "build_tree"
    assert state.research.current_status == "running"
    assert state.research.streamed_categories == ["Рыба", "Морепродукты"]
    assert state.research.active_profile_id == "profile-1"
    assert state.research.active_profile_version_id == "version-3"


def test_launcher_app_state_supports_selected_product_ids() -> None:
    state = LauncherAppState(selection={"selected_product_ids": ["fish-1", "fish-2"]})

    assert state.selection.selected_product_ids == ["fish-1", "fish-2"]


def test_launcher_app_state_accepts_legacy_payload_without_v2_sections() -> None:
    state = LauncherAppState(
        selection={
            "shop": "pyaterochka",
            "intent": "fish_catalog",
            "selected_catalog_nodes": [{"name": "Рыба", "url": "https://example.test/fish"}],
        },
        result={"launcher_view": {"products": [{"id": "fish-1"}]}},
    )

    assert state.selection.selected_catalog_nodes == [
        {"name": "Рыба", "url": "https://example.test/fish"}
    ]
    assert state.profile.profile_id == ""
    assert state.catalog.selected_nodes == []
    assert state.products.selected_product_ids == []
    assert state.result.launcher_view == {"products": [{"id": "fish-1"}]}


def test_launcher_app_state_round_trips_v2_workspace_sections() -> None:
    state = LauncherAppState(
        profile={
            "profile_id": "profile-1",
            "profile_version_id": "version-2",
            "site_url": "https://5ka.ru",
            "domain": "5ka.ru",
            "shop": "pyaterochka",
            "display_name": "Пятёрочка",
            "diagnostics": {"known_backend": True},
        },
        catalog={
            "full_tree": [{"name": "Каталог", "children": [{"name": "Рыба"}]}],
            "selected_nodes": [{"name": "Рыба", "url": "https://5ka.ru/catalog/ryba/"}],
            "selected_node_urls": ["https://5ka.ru/catalog/ryba/"],
            "catalog_type": "category_tree",
        },
        products={
            "products_count": 2,
            "items": [{"id": "fish-1", "name": "Cod"}],
            "source_categories": ["Рыба"],
            "selected_product_ids": ["fish-1"],
            "json_path": "C:/reports/products.json",
            "discovered_fields": {"brand": {"count": 2}},
        },
        dynamic_filters={
            "available_filters": {"brand": {"kind": "multi_select"}},
            "applied_values": {"brand": ["Nord"]},
            "counts": {"brand": {"Nord": 2}},
            "missing_fields": ["supplier"],
        },
        task={
            "status": "running",
            "task_name": "pyaterochka_fish_export",
            "task_kind": "product_export",
            "phase": "collect_products",
            "progress_current": 1,
            "progress_total": 2,
            "source_profile_id": "profile-1",
        },
        result={
            "summary": {"products_count": 2},
            "artifact_paths": {"json_path": "C:/reports/products.json"},
            "products_count": 2,
            "source_profile_id": "profile-1",
            "filter_snapshot": {"brand": ["Nord"]},
        },
    )

    loaded = LauncherAppState(**json.loads(state.model_dump_json()))

    assert loaded.profile.profile_id == "profile-1"
    assert loaded.catalog.selected_node_urls == ["https://5ka.ru/catalog/ryba/"]
    assert loaded.products.items == [{"id": "fish-1", "name": "Cod"}]
    assert loaded.products.selected_product_ids == ["fish-1"]
    assert loaded.dynamic_filters.counts == {"brand": {"Nord": 2}}
    assert loaded.task.phase == "collect_products"
    assert loaded.result.artifact_paths == {"json_path": "C:/reports/products.json"}
