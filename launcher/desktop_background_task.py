"""Qt background task helper for long launcher actions."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable


def start_background_action(
    *,
    action: Callable[[], Any],
    on_finished: Callable[[object], None],
    on_failed: Callable[[object], None],
    on_cleared: Callable[[], None],
) -> tuple[Any, Any]:
    """Start one launcher action in a QThread and return retained objects."""
    qtcore = import_module("PySide6.QtCore")

    class _Worker(qtcore.QObject):
        finished = qtcore.Signal(object)
        failed = qtcore.Signal(object)

        def __init__(self, task_action: Callable[[], Any]) -> None:
            super().__init__()
            self.task_action = task_action

        def run(self) -> None:
            try:
                result = self.task_action()
            except Exception as error:
                self.failed.emit(error)
                return
            self.finished.emit(result)

    thread = qtcore.QThread()
    worker = _Worker(action)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(on_cleared)
    thread.start()
    return thread, worker
