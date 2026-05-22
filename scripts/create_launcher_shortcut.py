"""Create a Windows shortcut for the ParserRIba desktop launcher."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from launcher.desktop_shell_helpers import resolve_launcher_icon_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for launcher shortcut creation."""
    parser = argparse.ArgumentParser(description="Create a Windows shortcut for the ParserRIba desktop launcher.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "ParserRIba Launcher.lnk",
        help="Where to write the .lnk file.",
    )
    return parser.parse_args()


def build_shortcut_powershell(output_path: Path, target_path: Path, script_path: Path, icon_path: Path) -> str:
    """Build a PowerShell command that creates the launcher shortcut."""
    output = str(output_path)
    target = str(target_path)
    script = str(script_path)
    working_dir = str(ROOT_DIR)
    icon = str(icon_path)
    return (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{output}'); "
        f"$shortcut.TargetPath = '{target}'; "
        f"$shortcut.Arguments = '\"{script}\"'; "
        f"$shortcut.WorkingDirectory = '{working_dir}'; "
        f"$shortcut.IconLocation = '{icon}'; "
        "$shortcut.Save()"
    )


def main() -> int:
    """Create the launcher shortcut and return a process exit code."""
    args = parse_args()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_path = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    script_path = ROOT_DIR / "scripts" / "run_desktop_launcher.py"
    icon_path = resolve_launcher_icon_path(ROOT_DIR)
    if not target_path.exists():
        raise FileNotFoundError(f"Launcher Python executable not found: {target_path}")
    if not script_path.exists():
        raise FileNotFoundError(f"Launcher entry script not found: {script_path}")
    if not icon_path.exists():
        raise FileNotFoundError(f"Launcher icon not found: {icon_path}")
    command = build_shortcut_powershell(output_path, target_path, script_path, icon_path)
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
