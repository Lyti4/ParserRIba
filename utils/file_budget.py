"""Helpers for proactive file-size budgeting in ParserRIba."""

from __future__ import annotations

from pathlib import Path

DEFAULT_LONG_FILE_LIMIT = 300
EXTENDED_LONG_FILE_LIMIT = 450
EXTENDED_LONG_FILE_PATH_PREFIXES = ("tests/", "scripts/")
EXTENDED_LONG_FILE_PATHS = {"main.py"}


def long_file_limit_for_path(rel_path: str) -> int:
    """Return the pragmatic file-length guideline for one repo path."""
    normalized = rel_path.replace("\\", "/")
    if normalized in EXTENDED_LONG_FILE_PATHS:
        return EXTENDED_LONG_FILE_LIMIT
    if any(normalized.startswith(prefix) for prefix in EXTENDED_LONG_FILE_PATH_PREFIXES):
        return EXTENDED_LONG_FILE_LIMIT
    return DEFAULT_LONG_FILE_LIMIT


def file_budget_snapshot(root_dir: Path | str, target_path: Path | str) -> dict[str, int | str | bool]:
    """Return a current file-size budget snapshot for one repo file."""
    root = Path(root_dir).resolve()
    target = Path(target_path)
    if not target.is_absolute():
        target = (root / target).resolve()
    rel_path = target.relative_to(root).as_posix()
    line_count = len(target.read_text(encoding="utf-8").splitlines())
    limit = long_file_limit_for_path(rel_path)
    return {
        "path": rel_path,
        "line_count": line_count,
        "limit": limit,
        "headroom": limit - line_count,
        "near_limit": line_count >= max(limit - 30, 0),
        "over_limit": line_count > limit,
    }
