from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from launcher.desktop_launcher import DesktopLauncherShell


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_prepare_cloak_button_dispatches_before_store_selection(monkeypatch, tmp_path) -> None:
    app = _app()
    shell = DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()
    calls = []
    monkeypatch.setattr(shell.controller, "run_cloak_runtime_install", lambda: calls.append("install"))

    button = next(button for button in window.findChildren(QPushButton) if button.text() == "Подготовить CloakBrowser")
    assert button.isEnabled()
    QTest.mouseClick(button, Qt.LeftButton)
    for _ in range(40):
        app.processEvents()
        QTest.qWait(10)
        if shell._active_task_thread is None:
            break
    assert calls == ["install"]
    assert shell._active_task_thread is None
