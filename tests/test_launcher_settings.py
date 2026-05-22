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
    state.task.status = "running"
    state.result.excel_path = "C:/reports/fish.xlsx"

    store.save_app_state(state)
    loaded = store.load_app_state()

    assert loaded.selection.shop == "metro"
    assert loaded.selection.categories == ["Рыба"]
    assert loaded.task.status == "running"
    assert loaded.result.excel_path == "C:/reports/fish.xlsx"
