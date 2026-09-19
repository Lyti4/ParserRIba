"""Run the ParserRIba desktop launcher shell."""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.desktop_launcher import DesktopLauncherShell
from scripts.smoke_desktop_launcher import main as smoke_main
from scripts.cloak_runtime_probe import run_cloak_probe


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the desktop launcher entrypoint."""
    parser = argparse.ArgumentParser(description="Run the ParserRIba desktop launcher.")
    parser.add_argument("--smoke", action="store_true", help="Run a quick desktop smoke instead of the full event loop.")
    parser.add_argument("--cloak-probe-result", type=Path, help="Run the bounded selected-Cloak startup/DOM/close probe and write its result JSON.")
    parser.add_argument("--local-task", nargs=argparse.REMAINDER, help="Run the registered local-task worker inside the frozen executable.")
    args = parser.parse_args()
    if args.local_task == []:
        parser.error("--local-task requires worker arguments")
    return args


def main() -> int:
    """Run the desktop launcher shell and return the process exit code."""
    args = parse_args()
    if args.local_task is not None:
        sys.argv = [sys.argv[0], *args.local_task]
        runpy.run_module("scripts.run_local_task", run_name="__main__")
        return 0
    if args.smoke:
        return smoke_main()
    if args.cloak_probe_result:
        return run_cloak_probe(args.cloak_probe_result)
    shell = DesktopLauncherShell(root_dir=ROOT_DIR)
    return shell.run()


if __name__ == "__main__":
    raise SystemExit(main())
