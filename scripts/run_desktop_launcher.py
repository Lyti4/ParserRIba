"""Run the ParserRIba desktop launcher shell."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.desktop_launcher import DesktopLauncherShell
from scripts.smoke_desktop_launcher import main as smoke_main


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the desktop launcher entrypoint."""
    parser = argparse.ArgumentParser(description="Run the ParserRIba desktop launcher.")
    parser.add_argument("--smoke", action="store_true", help="Run a quick desktop smoke instead of the full event loop.")
    return parser.parse_args()


def main() -> int:
    """Run the desktop launcher shell and return the process exit code."""
    args = parse_args()
    if args.smoke:
        return smoke_main()
    shell = DesktopLauncherShell(root_dir=ROOT_DIR)
    return shell.run()


if __name__ == "__main__":
    raise SystemExit(main())
