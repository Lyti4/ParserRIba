"""Helpers for safe CodeRabbit review runs on Windows via WSL."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shlex

BLOCKED_UNCOMMITTED_PREFIXES = (
    "data/",
    "generated_scaffolds/",
    "logs/",
    "build/",
    "dist/",
)
MAX_SAFE_UNCOMMITTED_PATHS = 25


@dataclass(frozen=True)
class GitWorktreeSnapshot:
    """Normalized git worktree paths split by state."""

    staged_paths: list[str] = field(default_factory=list)
    unstaged_paths: list[str] = field(default_factory=list)
    untracked_paths: list[str] = field(default_factory=list)

    @property
    def changed_paths(self) -> list[str]:
        """Return unique changed paths across all tracked and untracked states."""
        ordered: list[str] = []
        for group in (self.staged_paths, self.unstaged_paths, self.untracked_paths):
            for item in group:
                if item not in ordered:
                    ordered.append(item)
        return ordered


@dataclass(frozen=True)
class ReviewPreflightResult:
    """Preflight result for one planned CodeRabbit review run."""

    ok: bool
    scope: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_git_status_lines(lines: list[str]) -> GitWorktreeSnapshot:
    """Parse `git status --porcelain=v1` lines into structured path groups."""
    staged_paths: list[str] = []
    unstaged_paths: list[str] = []
    untracked_paths: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue
        status = line[:2]
        path = line[3:].strip()
        if status == "??":
            untracked_paths.append(path)
            continue
        if status[0] != " ":
            staged_paths.append(path)
        if status[1] != " ":
            unstaged_paths.append(path)
    return GitWorktreeSnapshot(
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
    )


def evaluate_review_preflight(
    snapshot: GitWorktreeSnapshot,
    *,
    scope: str,
    commits_ahead_of_base: int | None = None,
) -> ReviewPreflightResult:
    """Validate whether a requested CodeRabbit review scope is safe to run."""
    normalized_scope = str(scope or "committed").strip().casefold()
    warnings: list[str] = []
    errors: list[str] = []
    if normalized_scope == "uncommitted":
        blocked = [
            path
            for path in snapshot.changed_paths
            if any(path.startswith(prefix) for prefix in BLOCKED_UNCOMMITTED_PREFIXES)
        ]
        if blocked:
            errors.append(
                "Uncommitted review includes local artifact paths: " + ", ".join(blocked)
            )
        if len(snapshot.changed_paths) > MAX_SAFE_UNCOMMITTED_PATHS:
            errors.append(
                f"Uncommitted review is too broad: {len(snapshot.changed_paths)} changed paths."
            )
    elif normalized_scope == "committed":
        if commits_ahead_of_base is not None and commits_ahead_of_base <= 0:
            errors.append("Committed review requires at least one commit ahead of the selected base.")
        if snapshot.changed_paths:
            warnings.append(
                "Committed review ignores current working tree changes; commit the intended scope first."
            )
    else:
        errors.append(f"Unsupported review scope: {scope}")
    return ReviewPreflightResult(
        ok=not errors,
        scope=normalized_scope,
        warnings=warnings,
        errors=errors,
    )


def windows_path_to_wsl(path: Path | str) -> str:
    """Convert a Windows absolute path into the matching WSL mount path."""
    value = str(Path(path))
    drive, tail = value[:1], value[2:]
    normalized_tail = tail.replace("\\", "/")
    return f"/mnt/{drive.casefold()}{normalized_tail}"


def build_wsl_review_command(
    *,
    root_dir: Path | str,
    scope: str,
    base: str,
    config_files: list[str],
    review_dir: str,
    distro: str,
) -> list[str]:
    """Build a `wsl.exe ... coderabbit review` command for one safe scope."""
    repo_dir = windows_path_to_wsl(Path(root_dir))
    parts = ["source /home/lyti4/.bashrc", f"cd {shlex.quote(repo_dir)}", "coderabbit review --agent"]
    parts.append(f"-t {shlex.quote(str(scope))}")
    if base:
        parts.append(f"--base {shlex.quote(base)}")
    for config_file in config_files:
        parts.append(f"-c {shlex.quote(config_file)}")
    if review_dir:
        parts.append(f"--dir {shlex.quote(review_dir)}")
    linux_command = " && ".join(parts[:2]) + " && " + " ".join(parts[2:])
    return ["wsl.exe", "-d", distro, "--", "bash", "-lc", linux_command]
