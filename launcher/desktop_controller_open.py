"""Path opening helpers for desktop launcher controller."""

from __future__ import annotations

from typing import Any, Callable

from launcher.desktop_user_messages import friendly_error_message, no_output_path_message, opened_path_message


def open_controller_path(controller: Any, opener: Callable[[str], None], path_value: str) -> bool:
    """Open one path and update launcher task message."""
    path = str(path_value or "").strip()
    if not path:
        controller.state.task.message = no_output_path_message()
        return False
    try:
        opener(path)
    except OSError as error:
        controller.state.task.message = friendly_error_message(error)
        controller.state.task.last_error = str(error)
        return False
    controller.state.task.message = opened_path_message(path)
    controller.state.task.last_error = ""
    return True
