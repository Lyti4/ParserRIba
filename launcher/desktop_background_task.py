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

    class _Callbacks(qtcore.QObject):
        def __init__(
            self,
            finished_callback: Callable[[object], None],
            failed_callback: Callable[[object], None],
            cleared_callback: Callable[[], None],
        ) -> None:
            super().__init__()
            self.finished_callback = finished_callback
            self.failed_callback = failed_callback
            self.cleared_callback = cleared_callback

        @qtcore.Slot(object)
        def handle_finished(self, result: object) -> None:
            self.finished_callback(result)

        @qtcore.Slot(object)
        def handle_failed(self, error: object) -> None:
            self.failed_callback(error)

        @qtcore.Slot()
        def handle_cleared(self) -> None:
            self.cleared_callback()

    thread = qtcore.QThread()
    worker = _Worker(action)
    callbacks = _Callbacks(on_finished, on_failed, on_cleared)
    thread._parserriba_callbacks = callbacks
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(callbacks.handle_finished)
    worker.failed.connect(callbacks.handle_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(callbacks.handle_cleared)
    thread.start()
    return thread, worker
