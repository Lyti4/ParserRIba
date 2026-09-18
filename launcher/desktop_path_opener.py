"""Open launcher artifacts with local desktop applications."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def open_path_with_system_handler(path: str) -> None:
    """Open a local path with the platform default application."""
    if sys.platform == "win32":
        if Path(path).suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            _open_windows_spreadsheet(path)
            return
        os.startfile(path)  # type: ignore[attr-defined]
        return
    command = ["open", path] if sys.platform == "darwin" else ["xdg-open", path]
    subprocess.Popen(command)


def _open_windows_spreadsheet(path: str) -> None:
    spreadsheet_app = _find_windows_spreadsheet_app()
    if spreadsheet_app:
        subprocess.Popen([spreadsheet_app, path])
        return
    subprocess.Popen(["explorer.exe", f"/select,{path}"])


def _find_windows_spreadsheet_app() -> str:
    for executable in ("excel.exe", "soffice.exe", "libreoffice.exe"):
        found = shutil.which(executable)
        if found:
            return found
    for candidate in (
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE",
        Path(os.environ.get("ProgramFiles", "")) / "LibreOffice" / "program" / "soffice.exe",
    ):
        if candidate.exists():
            return str(candidate)
    return ""
