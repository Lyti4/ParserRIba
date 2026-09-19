from __future__ import annotations

import sys

from utils.local_task_adapter import build_local_task_command


def test_frozen_task_command_uses_same_executable_worker_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    command = build_local_task_command(task_name="cloak_runtime_install", root_dir=tmp_path)
    assert command[:4] == [sys.executable, "--local-task", "--task", "cloak_runtime_install"]
    assert str(tmp_path) in command


def test_explicit_python_override_keeps_source_task_script(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    command = build_local_task_command(task_name="cloak_runtime_install", root_dir=tmp_path, python_executable="python-test")
    assert command[0] == "python-test"
    assert command[1].endswith("scripts/run_local_task.py")

def test_empty_worker_mode_rejects_arguments_without_gui(monkeypatch):
    import sys
    import types
    import pytest

    def reject_gui(*args, **kwargs):
        pytest.fail("Empty worker invocation must not start the GUI or browser probe")

    probe = types.ModuleType("scripts.cloak_runtime_probe")
    probe.run_cloak_probe = reject_gui
    monkeypatch.setitem(sys.modules, "scripts.cloak_runtime_probe", probe)
    from scripts import run_desktop_launcher as entry

    monkeypatch.setattr(entry, "DesktopLauncherShell", reject_gui)
    monkeypatch.setattr(sys, "argv", [str(entry.__file__), "--local-task"])
    with pytest.raises(SystemExit) as error:
        entry.main()
    assert error.value.code not in (None, 0)
