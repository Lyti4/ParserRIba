"""Generate and validate ParserRIba launcher visual review screenshots."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "launcher_visual_review"
REQUIRED_OBJECTS = (
    ("QFrame", "launcherNavigationRail"),
    ("QFrame", "launcherCommandStrip"),
    ("QFrame", "launcherRightInspector"),
    ("QTableWidget", "launcherProductResultTable"),
    ("QPlainTextEdit", "launcherDiagnosticsText"),
)


@dataclass(frozen=True)
class VisualReviewResult:
    mode: str
    path: str
    width: int
    height: int


def run_visual_review(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    width: int = 1440,
    height: int = 900,
    modes: tuple[str, ...] = ("light", "dark"),
    root: Path = ROOT,
) -> list[VisualReviewResult]:
    """Build launcher screenshots and validate stable shell regions."""
    from launcher.desktop_launcher import DesktopLauncherShell
    from launcher.desktop_theme import apply_launcher_theme

    output_dir.mkdir(parents=True, exist_ok=True)
    shell = DesktopLauncherShell(root_dir=root)
    window = shell.create_window()
    window.resize(width, height)
    app = shell._qtwidgets.QApplication.instance()
    _validate_required_objects(shell, window)
    results: list[VisualReviewResult] = []
    for mode in modes:
        shell.state.settings.theme_mode = mode
        apply_launcher_theme(window, mode)
        shell._refresh_ui()
        window.show()
        app.processEvents()
        pixmap = window.grab()
        target = output_dir / f"launcher_{mode}_{width}x{height}.png"
        if not pixmap.save(str(target)):
            raise RuntimeError(f"Failed to save screenshot: {target}")
        results.append(VisualReviewResult(mode=mode, path=str(target), width=pixmap.width(), height=pixmap.height()))
    close_window = getattr(window, "close")
    close_window()
    return results


def render_results(results: list[VisualReviewResult]) -> str:
    """Render visual review results as compact JSON."""
    return json.dumps([item.__dict__ for item in results], ensure_ascii=True, indent=2)


def _validate_required_objects(shell: Any, window: Any) -> None:
    missing: list[str] = []
    for class_name, object_name in REQUIRED_OBJECTS:
        widget_class = getattr(shell._qtwidgets, class_name)
        if window.findChild(widget_class, object_name) is None:
            missing.append(f"{class_name}:{object_name}")
    if missing:
        raise RuntimeError("Missing launcher visual review objects: " + ", ".join(missing))


def main(argv: list[str] | None = None) -> int:
    """Run launcher visual review CLI."""
    parser = argparse.ArgumentParser(description="Generate ParserRIba launcher light/dark visual review screenshots")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args(argv)
    results = run_visual_review(output_dir=args.output_dir, width=args.width, height=args.height)
    sys.stdout.write(render_results(results) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
