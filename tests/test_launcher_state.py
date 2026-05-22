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
    assert state.result.launcher_view == {}


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
