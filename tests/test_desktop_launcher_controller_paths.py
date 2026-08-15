from pathlib import Path

import pytest

from launcher.desktop_controller import DesktopLauncherController, open_path_with_system_handler
from launcher.desktop_user_messages import (
    no_output_path_message,
    opened_path_message,
    settings_saved_message,
)


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
