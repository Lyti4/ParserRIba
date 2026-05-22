from __future__ import annotations

from pathlib import Path

from utils.coderabbit_review import (
    build_wsl_review_command,
    evaluate_review_preflight,
    parse_git_status_lines,
    windows_path_to_wsl,
)


def test_parse_git_status_lines_collects_staged_unstaged_and_untracked() -> None:
    snapshot = parse_git_status_lines(
        [
            " M utils/site_onboarding.py",
            "M  utils/store_export_runtime.py",
            "A  docs/TOOLS_POLICY.md",
            "?? data/report.xlsx",
            "?? generated_scaffolds/sample.json",
        ]
    )

    assert snapshot.staged_paths == ["utils/store_export_runtime.py", "docs/TOOLS_POLICY.md"]
    assert snapshot.unstaged_paths == ["utils/site_onboarding.py"]
    assert snapshot.untracked_paths == ["data/report.xlsx", "generated_scaffolds/sample.json"]


def test_uncommitted_review_preflight_blocks_local_artifact_paths() -> None:
    snapshot = parse_git_status_lines(
        [
            " M utils/site_onboarding.py",
            "?? data/report.xlsx",
        ]
    )

    result = evaluate_review_preflight(snapshot, scope="uncommitted")

    assert result.ok is False
    assert any("data/report.xlsx" in item for item in result.errors)


def test_committed_review_preflight_warns_about_dirty_worktree() -> None:
    snapshot = parse_git_status_lines(
        [
            " M utils/site_onboarding.py",
            "?? generated_scaffolds/sample.json",
        ]
    )

    result = evaluate_review_preflight(snapshot, scope="committed", commits_ahead_of_base=1)

    assert result.ok is True
    assert any("ignores current working tree changes" in item for item in result.warnings)


def test_committed_review_preflight_blocks_when_no_commits_ahead_of_base() -> None:
    snapshot = parse_git_status_lines([])

    result = evaluate_review_preflight(snapshot, scope="committed", commits_ahead_of_base=0)

    assert result.ok is False
    assert any("at least one commit ahead" in item for item in result.errors)


def test_windows_path_to_wsl_maps_repo_path() -> None:
    assert windows_path_to_wsl(Path(r"C:\tmp\ParserRIba-clean")) == "/mnt/c/tmp/ParserRIba-clean"


def test_build_wsl_review_command_uses_committed_scope_and_repo_dir() -> None:
    command = build_wsl_review_command(
        root_dir=Path(r"C:\tmp\ParserRIba-clean"),
        scope="committed",
        base="main",
        config_files=["AGENTS.md"],
        review_dir="utils",
        distro="Ubuntu",
    )

    joined = " ".join(command)
    assert command[:5] == ["wsl.exe", "-d", "Ubuntu", "--", "bash"]
    assert "cd /mnt/c/tmp/ParserRIba-clean" in joined
    assert "coderabbit review --agent -t committed --base main -c AGENTS.md --dir utils" in joined
