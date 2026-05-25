"""Create and close the desktop launcher window for a quick local smoke check."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.desktop_launcher import DesktopLauncherShell, load_pyside6


def main() -> int:
    """Build one launcher window and exit with a non-zero code on failure."""
    app, _, _ = load_pyside6()
    shell = DesktopLauncherShell(root_dir=ROOT_DIR)
    window = shell.create_window()
    if window is None:
        raise RuntimeError("Desktop launcher window was not created.")
    title = window.windowTitle()
    central_widget = window.centralWidget()
    window.show()
    instance = app.instance()
    if instance is not None:
        instance.processEvents()
    if title != "ParserRIba Лаунчер":
        raise RuntimeError(f"Unexpected launcher window title: {title}")
    if central_widget is None:
        raise RuntimeError("Launcher central widget is missing.")
    window.hide()
    window.deleteLater()
    if instance is not None:
        instance.processEvents()
    sys.stdout.write("Desktop launcher smoke passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
