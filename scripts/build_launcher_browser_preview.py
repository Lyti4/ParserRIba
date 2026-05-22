"""Build an interactive browser preview for the current launcher state."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.browser_preview import build_browser_preview_html
from launcher.desktop_controller import DesktopLauncherController


def _apply_preview_demo_state(controller: DesktopLauncherController) -> None:
    """Seed a useful demo state when local task runners are unavailable."""
    categories = ["Fish", "Seafood", "Caviar & Snacks", "Cutlets & Mince"]
    controller.set_selection(categories=categories[:4])
    controller.state.task.status = "succeeded"
    controller.state.task.task_name = "browser_preview"
    controller.state.task.message = "Preview mode with local demo data"
    controller.state.result.launcher_view = {
        "report_summary": {
            "products_count": 218,
            "categories": categories[:4],
            "category_counts": {
                categories[0]: 96 if len(categories) > 0 else 96,
                categories[1]: 65 if len(categories) > 1 else 65,
                categories[2]: 51 if len(categories) > 2 else 51,
                categories[3]: 6 if len(categories) > 3 else 6,
            },
            "supplier_counts": {
                "Russian Sea": 27,
                "Baltic Coast": 18,
                "Vici": 14,
            },
            "brand_counts": {
                "Russian Sea": 27,
                "Baltic Coast": 18,
                "Vici": 14,
            },
        },
        "available_filter_counts": {
            "suppliers": {"Russian Sea": 27, "Baltic Coast": 18, "Vici": 14},
            "brands": {"Russian Sea": 27, "Baltic Coast": 18, "Vici": 14},
            "wine_styles": {},
            "alcohol_types": {},
            "sugar_classes": {},
            "colors": {},
        },
    }


def main() -> int:
    """Write one browser-preview HTML file for the current launcher state."""
    controller = DesktopLauncherController(root_dir=ROOT_DIR)
    controller.set_selection(intent="fish_catalog")
    try:
        controller.load_filter_options()
        controller.run_selected_report_export()
    except Exception:
        _apply_preview_demo_state(controller)
    if not controller.state.selection.categories:
        _apply_preview_demo_state(controller)
    output_path = ROOT_DIR / "data" / "reports" / "launcher_browser_preview.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_browser_preview_html(controller.state), encoding="utf-8")
    sys.stdout.write(f"{output_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
