"""Render the desktop launcher into a PNG preview without manual interaction."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.desktop_launcher import DesktopLauncherShell, load_pyside6


def main() -> int:
    """Capture the desktop launcher window to a PNG file."""
    QApplication, _, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = DesktopLauncherShell(root_dir=ROOT_DIR)
    window = shell.create_window()
    output_path = ROOT_DIR / "data" / "reports" / "launcher_preview.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    window.show()
    app.processEvents()
    pixmap = window.grab()
    saved = pixmap.save(str(output_path))
    window.hide()
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
