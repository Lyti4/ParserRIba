from __future__ import annotations

from importlib import import_module

from launcher.desktop_background_task import start_background_action
from launcher.desktop_shell_helpers import load_pyside6


def test_background_action_callbacks_run_on_gui_thread() -> None:
    QApplication, _qtwidgets, _qt = load_pyside6()
    qtcore = import_module("PySide6.QtCore")
    app = QApplication.instance() or QApplication([])
    gui_thread = app.thread()
    seen: dict[str, object] = {}

    def action() -> str:
        seen["action_thread"] = qtcore.QThread.currentThread()
        return "done"

    def on_finished(result: object) -> None:
        seen["result"] = result
        seen["finished_thread"] = qtcore.QThread.currentThread()

    def on_failed(error: object) -> None:
        seen["error"] = error

    def on_cleared() -> None:
        seen["cleared_thread"] = qtcore.QThread.currentThread()

    thread, worker = start_background_action(
        action=action,
        on_finished=on_finished,
        on_failed=on_failed,
        on_cleared=on_cleared,
    )

    for _ in range(500):
        if "cleared_thread" in seen:
            break
        app.processEvents(qtcore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

    assert seen["result"] == "done"
    assert seen["action_thread"] != gui_thread
    assert seen["finished_thread"] == gui_thread
    assert seen["cleared_thread"] == gui_thread
    assert "error" not in seen
    assert worker is not None
    assert thread is not None
