from pathlib import Path

from utils.file_budget import (
    DEFAULT_LONG_FILE_LIMIT,
    EXTENDED_LONG_FILE_LIMIT,
    file_budget_snapshot,
    long_file_limit_for_path,
)


def test_long_file_limit_for_path_matches_repo_policy() -> None:
    assert long_file_limit_for_path("utils/example.py") == DEFAULT_LONG_FILE_LIMIT
    assert long_file_limit_for_path("tests/test_example.py") == EXTENDED_LONG_FILE_LIMIT
    assert long_file_limit_for_path("scripts/tool.py") == EXTENDED_LONG_FILE_LIMIT
    assert long_file_limit_for_path("main.py") == EXTENDED_LONG_FILE_LIMIT


def test_file_budget_snapshot_reports_headroom(tmp_path: Path) -> None:
    target = tmp_path / "feature.py"
    target.write_text("line1\nline2\n", encoding="utf-8")

    snapshot = file_budget_snapshot(tmp_path, target)

    assert snapshot["path"] == "feature.py"
    assert snapshot["line_count"] == 2
    assert snapshot["limit"] == DEFAULT_LONG_FILE_LIMIT
    assert snapshot["headroom"] == DEFAULT_LONG_FILE_LIMIT - 2
    assert snapshot["near_limit"] is False
    assert snapshot["over_limit"] is False


def test_file_budget_snapshot_marks_near_limit(tmp_path: Path) -> None:
    target = tmp_path / "feature.py"
    target.write_text("\n".join(["x"] * 280), encoding="utf-8")

    snapshot = file_budget_snapshot(tmp_path, target)

    assert snapshot["near_limit"] is True
    assert snapshot["over_limit"] is False
