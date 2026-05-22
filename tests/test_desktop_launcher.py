from pathlib import Path

import pytest

import launcher.desktop_launcher as desktop_launcher
import launcher.desktop_shell_helpers as desktop_shell_helpers
from launcher.desktop_user_messages import no_output_path_message


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


def test_open_json_without_target_sets_friendly_message(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell._refresh_ui = lambda: None

    shell._on_open_json()

    assert shell.state.task.message == no_output_path_message()


def test_desktop_launcher_wraps_controls_in_scroll_area(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()

    scroll_areas = window.findChildren(shell._qtwidgets.QScrollArea)

    assert window is not None
    assert scroll_areas


def test_desktop_launcher_research_button_is_renamed(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.create_window()

    assert shell.action_buttons["onboarding"].text() == "Исследование"


def test_desktop_launcher_does_not_autoselect_discovered_categories(tmp_path: Path) -> None:
    shell = desktop_launcher.DesktopLauncherShell(root_dir=tmp_path)
    shell.state.result.launcher_view = {
        "shop": "pyaterochka",
        "intent": "fish_catalog",
        "category_tree": [
            {"name": "Рыба", "url": "https://example.test/fish"},
            {"name": "Морепродукты", "url": "https://example.test/seafood"},
        ],
    }

    shell.create_window()

    assert shell.category_list.count() == 2
    assert shell.category_list.selectedItems() == []


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
