"""Repository architecture checks for ParserRIba.

This script is intentionally conservative: it reports legacy drift as warnings
and only fails by default on repository hygiene problems that should never be
committed, such as tracked logs or bytecode.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from loguru import logger


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    ".build-venv",
    "build",
    "dist",
    "data",
    "profiles",
    "__pycache__",
}
TRACKED_ARTIFACT_MARKERS = (
    "__pycache__/",
    ".pyc",
    "logs/",
    "build/",
    "dist/",
    "GeoLite2",
)
LONG_FILE_LIMIT = 300


@dataclass(frozen=True)
class Finding:
    """One architecture check result."""

    severity: str
    code: str
    path: str
    line: int
    message: str


def iter_python_files(root: Path = ROOT) -> list[Path]:
    """Return tracked-source Python files, excluding generated folders."""
    files: list[Path] = []
    for path in root.rglob("*.py"):
        rel_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        files.append(path)
    return sorted(files)


def tracked_files(root: Path = ROOT) -> list[str]:
    """Return files tracked by Git."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def find_tracked_artifacts(files: Iterable[str]) -> list[Finding]:
    """Find generated or secret-prone files already tracked by Git."""
    findings: list[Finding] = []
    for file_path in files:
        normalized = file_path.replace("\\", "/")
        if normalized == ".env.example":
            continue
        if (
            normalized == ".env"
            or normalized.startswith(".env.")
            or any(marker in normalized for marker in TRACKED_ARTIFACT_MARKERS)
        ):
            findings.append(
                Finding(
                    severity="error",
                    code="tracked-artifact",
                    path=normalized,
                    line=0,
                    message="Generated, local, or secret-prone file is tracked by Git.",
                )
            )
    return findings


def scan_python_file(path: Path, root: Path = ROOT) -> list[Finding]:
    """Scan one Python file for architecture drift."""
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    findings: list[Finding] = []

    if len(lines) > LONG_FILE_LIMIT:
        findings.append(
            Finding(
                severity="warning",
                code="long-file",
                path=rel,
                line=0,
                message=f"Python file has {len(lines)} lines; target is <= {LONG_FILE_LIMIT}.",
            )
        )

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        findings.append(
            Finding(
                severity="error",
                code="syntax-error",
                path=rel,
                line=exc.lineno or 0,
                message=str(exc),
            )
        )
        return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                findings.append(
                    Finding(
                        severity="warning",
                        code="print-call",
                        path=rel,
                        line=node.lineno,
                        message="Use loguru logger or a deliberate CLI output wrapper instead of print().",
                    )
                )
            if isinstance(node.func, ast.Attribute) and node.func.attr == "sleep":
                owner = node.func.value
                if isinstance(owner, ast.Name) and owner.id == "time":
                    findings.append(
                        Finding(
                            severity="error",
                            code="time-sleep",
                            path=rel,
                            line=node.lineno,
                            message="Use asyncio.sleep() instead of time.sleep().",
                        )
                    )
            if isinstance(node.func, ast.Attribute) and node.func.attr == "close":
                findings.append(
                    Finding(
                        severity="warning",
                        code="close-call",
                        path=rel,
                        line=node.lineno,
                        message="Review close() call; AsyncCamoufox must be closed via async with or __aexit__.",
                    )
                )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if rel.startswith("parsers/") and ("http://" in node.value or "https://" in node.value):
                findings.append(
                    Finding(
                        severity="warning",
                        code="hardcoded-url",
                        path=rel,
                        line=getattr(node, "lineno", 0),
                        message="Store-specific URLs should live in knowledge_base/.",
                    )
                )
    return findings


def check_parser_factory(root: Path = ROOT) -> list[Finding]:
    """Check whether ParserFactory can be imported and parser modules inspected."""
    script = (
        "from main import ParserFactory\n"
        "for store in ParserFactory.PARSERS:\n"
        "    try:\n"
        "        ParserFactory._load_parser_class(store)\n"
        "    except Exception as exc:\n"
        "        print(f'{store}: {type(exc).__name__}: {exc}')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [
        line
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith(("✅", "🌍", "⚠", "ℹ"))
    ]
    findings: list[Finding] = []
    if result.returncode != 0:
        findings.append(
            Finding(
                severity="warning",
                code="parser-factory",
                path="main.py",
                line=0,
                message=result.stderr.strip() or "ParserFactory import check failed.",
            )
        )
    for line in lines:
        findings.append(
            Finding(
                severity="warning",
                code="parser-factory",
                path="main.py",
                line=0,
                message=f"Parser module check: {line}",
            )
        )
    return findings


def collect_findings(root: Path = ROOT) -> list[Finding]:
    """Run all architecture checks."""
    findings = find_tracked_artifacts(tracked_files(root))
    for file_path in iter_python_files(root):
        findings.extend(scan_python_file(file_path, root=root))
    findings.extend(check_parser_factory(root))
    return sorted(findings, key=lambda item: (item.severity, item.code, item.path, item.line))


def render_findings(findings: Iterable[Finding]) -> str:
    """Render findings as compact Markdown."""
    items = list(findings)
    if not items:
        return "Architecture check passed: no findings."
    lines = ["# ParserRIba Architecture Check", ""]
    for severity in ("error", "warning"):
        group = [item for item in items if item.severity == severity]
        if not group:
            continue
        lines.append(f"## {severity.title()}s")
        for item in group:
            location = item.path if item.line == 0 else f"{item.path}:{item.line}"
            lines.append(f"- `{item.code}` `{location}` - {item.message}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    """Run the architecture check CLI."""
    parser = argparse.ArgumentParser(description="Check ParserRIba architecture hygiene")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    args = parser.parse_args()

    findings = collect_findings(ROOT)
    report = render_findings(findings)
    if findings:
        logger.warning("\n{}", report)
    else:
        logger.info(report)

    has_errors = any(item.severity == "error" for item in findings)
    has_warnings = any(item.severity == "warning" for item in findings)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
