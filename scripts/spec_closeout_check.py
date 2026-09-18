"""Validate spec-kit closeout state for ParserRIba features."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "specs"
DEFAULT_DOCS = (
    "docs/PROJECT_STATE.md",
    "docs/NEXT_STEPS.md",
    "docs/DECISIONS.md",
    "docs/TARGET_ARCHITECTURE.md",
    "docs/PROJECT_STRUCTURE.md",
)


@dataclass(frozen=True)
class CloseoutFinding:
    code: str
    path: str
    message: str


def collect_findings(
    *,
    feature: str | None = None,
    include_deferred: bool = False,
    require_clean_git: bool = False,
    require_graphify: bool = False,
    required_docs: Iterable[str] = DEFAULT_DOCS,
    root: Path = ROOT,
) -> list[CloseoutFinding]:
    """Collect closeout findings for one feature or every spec with tasks."""
    findings: list[CloseoutFinding] = []
    specs = _spec_dirs(feature=feature, root=root)
    if feature and not specs:
        findings.append(CloseoutFinding("missing-feature", f"specs/{feature}", "Feature directory was not found."))
    for spec_dir in specs:
        findings.extend(_check_tasks(spec_dir, root=root, include_deferred=include_deferred))
    for rel_path in required_docs:
        if not (root / rel_path).exists():
            findings.append(CloseoutFinding("missing-doc", rel_path, "Required project document is missing."))
    if require_graphify and not (root / "graphify-out" / "graph.json").exists():
        findings.append(CloseoutFinding("missing-graphify", "graphify-out/graph.json", "Graphify output is missing."))
    if require_clean_git and _git_status(root):
        findings.append(CloseoutFinding("dirty-git", ".", "Working tree has uncommitted changes."))
    return findings


def render_findings(findings: Iterable[CloseoutFinding]) -> str:
    """Render a compact closeout report."""
    items = list(findings)
    if not items:
        return "Spec closeout check passed: no findings."
    lines = ["# ParserRIba Spec Closeout Check", ""]
    for item in items:
        lines.append(f"- `{item.code}` `{item.path}` - {item.message}")
    return "\n".join(lines)


def _spec_dirs(*, feature: str | None, root: Path) -> list[Path]:
    if feature:
        return [root / "specs" / feature] if (root / "specs" / feature).exists() else []
    if not (root / "specs").exists():
        return []
    return sorted(path for path in (root / "specs").iterdir() if (path / "tasks.md").exists())


def _check_tasks(spec_dir: Path, *, root: Path, include_deferred: bool = False) -> list[CloseoutFinding]:
    rel = spec_dir.relative_to(root).as_posix()
    tasks_path = spec_dir / "tasks.md"
    if not tasks_path.exists():
        return [CloseoutFinding("missing-tasks", f"{rel}/tasks.md", "Feature has no tasks.md.")]
    findings: list[CloseoutFinding] = []
    open_lines: list[str] = []
    for line_number, line in enumerate(tasks_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if line.startswith("- [ ]") and (include_deferred or not line.startswith("- [ ] Deferred:")):
            open_lines.append(f"{line_number}: {line}")
    if open_lines:
        findings.append(
            CloseoutFinding(
                "open-tasks",
                f"{rel}/tasks.md",
                f"Open tasks remain: {json.dumps(open_lines, ensure_ascii=True)}",
            )
        )
    return findings


def _git_status(root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    """Run the spec closeout guard."""
    parser = argparse.ArgumentParser(description="Validate ParserRIba spec-kit closeout state")
    parser.add_argument("--feature", help="specific specs/<feature> directory name")
    parser.add_argument("--include-deferred", action="store_true", help="treat Deferred tasks as open tasks")
    parser.add_argument("--require-clean-git", action="store_true", help="fail when git status is not clean")
    parser.add_argument("--require-graphify", action="store_true", help="fail when graphify-out/graph.json is missing")
    args = parser.parse_args(argv)

    findings = collect_findings(
        feature=args.feature,
        include_deferred=args.include_deferred,
        require_clean_git=args.require_clean_git,
        require_graphify=args.require_graphify,
    )
    sys.stdout.write(render_findings(findings) + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
