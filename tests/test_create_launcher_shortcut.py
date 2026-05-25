from pathlib import Path

from scripts.create_launcher_shortcut import build_shortcut_powershell


def test_build_shortcut_powershell_uses_launcher_paths(tmp_path: Path) -> None:
    shortcut_path = tmp_path / "ParserRIba Launcher.lnk"
    target_path = tmp_path / "python.exe"
    script_path = tmp_path / "run_desktop_launcher.py"
    icon_path = tmp_path / "parserriba_launcher.ico"

    command = build_shortcut_powershell(shortcut_path, target_path, script_path, icon_path)

    assert str(shortcut_path) in command
    assert str(target_path) in command
    assert f'"{script_path}"' in command
    assert str(icon_path) in command
