"""Run the focused ParserRIba agent workflow guard set."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
HANDOFF_REQUIRED_MARKERS = (
    "Workspace:",
    "Branch:",
    "Active plan:",
    "Validation:",
    "Open risks:",
)


@dataclass(frozen=True)
class CheckCommand:
    """One command in the agent workflow guard set."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    """Result of one guard command."""

    name: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def build_commands(*, scope: str, include_tests: bool) -> list[CheckCommand]:
    """Build the command list for a selected validation scope."""
    python = sys.executable
    commands = [
        CheckCommand("encoding-changed", (python, "scripts/encoding_guard.py", "--changed")),
        CheckCommand("architecture", (python, "scripts/architecture_check.py")),
    ]
    if scope == "staged":
        commands[0] = CheckCommand("encoding-staged", (python, "scripts/encoding_guard.py", "--staged"))
    elif scope == "all":
        commands[0] = CheckCommand("encoding-all", (python, "scripts/encoding_guard.py", "--all"))
    if include_tests:
        commands.append(
            CheckCommand(
                "agent-ops-focused-tests",
                (
                    python,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_encoding_guard.py",
                    "tests/test_architecture_check.py",
                    "tests/test_agent_ops_check.py",
                ),
            )
        )
    return commands


def run_checks(
    commands: Iterable[CheckCommand],
    *,
    root: Path = ROOT,
    runner: CommandRunner | None = None,
) -> list[CheckResult]:
    """Run checks and return their raw results."""
    command_runner = runner or _run_command
    results: list[CheckResult] = []
    for item in commands:
        completed = command_runner(item.command, root)
        results.append(
            CheckResult(
                name=item.name,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        )
    return results


def check_handoff_note(path: Path, *, root: Path = ROOT) -> CheckResult:
    """Validate a paste-ready handoff note for stale-context transitions."""
    target = path if path.is_absolute() else root / path
    if not target.exists():
        return CheckResult("handoff-note", 1, "", f"Missing handoff note: {target}")
    text = target.read_text(encoding="utf-8", errors="replace")
    sections = _handoff_sections(text)
    missing = [marker for marker in HANDOFF_REQUIRED_MARKERS if marker not in sections]
    if missing:
        return CheckResult("handoff-note", 1, "", "Missing handoff markers: " + ", ".join(missing))
    empty = [marker for marker in HANDOFF_REQUIRED_MARKERS if not sections[marker].strip()]
    if empty:
        return CheckResult("handoff-note", 1, "", "Empty handoff markers: " + ", ".join(empty))
    return CheckResult("handoff-note", 0, "handoff note passed", "")


def collect_results(
    *,
    scope: str,
    include_tests: bool,
    handoff_note: Path | None = None,
    root: Path = ROOT,
    runner: CommandRunner | None = None,
) -> list[CheckResult]:
    """Collect command and optional handoff-note results."""
    results = run_checks(build_commands(scope=scope, include_tests=include_tests), root=root, runner=runner)
    if handoff_note:
        results.append(check_handoff_note(handoff_note, root=root))
    return results


def render_results(results: Iterable[CheckResult]) -> str:
    """Render a compact report for humans and automation logs."""
    items = list(results)
    if not items:
        return "Agent ops check: no commands selected."
    lines = ["# ParserRIba Agent Ops Check", ""]
    for item in items:
        status = "passed" if item.passed else "failed"
        lines.append(f"- {item.name}: {status} ({item.returncode})")
        if not item.passed:
            detail = (item.stderr or item.stdout).strip()
            if detail:
                lines.append(detail)
    return "\n".join(lines)


def render_encoding_workflow() -> str:
    """Render the standard encoding safety commands."""
    python = sys.executable
    lines = [
        "# ParserRIba Encoding Workflow",
        "",
        f"- changed: `{python} scripts/encoding_guard.py --changed`",
        f"- staged: `{python} scripts/encoding_guard.py --staged`",
        f"- all: `{python} scripts/encoding_guard.py --all`",
        f"- dry-run: `{python} scripts/encoding_normalization_dry_run.py --changed`",
        f"- utf8-capture: `{python} scripts/utf8_command.py -- <command>`",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the agent workflow guard CLI."""
    parser = argparse.ArgumentParser(description="Run ParserRIba agent workflow guards")
    parser.add_argument("--scope", choices=("changed", "staged", "all"), default="changed")
    parser.add_argument("--with-tests", action="store_true", help="run focused guard tests too")
    parser.add_argument("--handoff-note", type=Path, help="validate a paste-ready handoff note")
    parser.add_argument("--encoding-workflow", action="store_true", help="print encoding safety commands and exit")
    args = parser.parse_args(argv)

    if args.encoding_workflow:
        sys.stdout.write(render_encoding_workflow() + "\n")
        return 0

    results = collect_results(scope=args.scope, include_tests=args.with_tests, handoff_note=args.handoff_note)
    sys.stdout.write(render_results(results) + "\n")
    return 0 if all(item.passed for item in results) else 1


def _run_command(command: Sequence[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, check=False, capture_output=True, text=True, encoding="utf-8")


def _handoff_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in HANDOFF_REQUIRED_MARKERS:
            current = stripped
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {marker: "\n".join(lines) for marker, lines in sections.items()}


if __name__ == "__main__":
    raise SystemExit(main())
