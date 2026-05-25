"""Check ParserRIba file-size budget before editing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.file_budget import file_budget_snapshot


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Check ParserRIba file-size budget.")
    parser.add_argument("paths", nargs="+", help="One or more repo-relative file paths.")
    return parser.parse_args()


def main() -> int:
    """Print JSON budget snapshots for one or more file paths."""
    args = parse_args()
    snapshots = [file_budget_snapshot(ROOT_DIR, path) for path in args.paths]
    sys.stdout.write(f"{json.dumps(snapshots, ensure_ascii=False, indent=2)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
