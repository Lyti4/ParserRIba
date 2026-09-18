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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.encoding_guard import collect_encoding_findings
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    ".build-venv",
    "archive",
    "build",
    "dist",
    "data",
    "logs",
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
REMOVED_STARTUP_DOC_MARKERS = (
    "archive/legacy_code", "archive\\legacy_code",
    "docs/LEGACY_MIGRATION_BACKLOG.md", "docs\\LEGACY_MIGRATION_BACKLOG.md",
    "docs/PROJECT_REVISION_2026-05-31.md", "docs\\PROJECT_REVISION_2026-05-31.md",
)
REQUIRED_STARTUP_DOCS = (
    "AGENTS.md", "docs/PROJECT_STATE.md", "docs/NEXT_STEPS.md", "docs/DECISIONS.md",
    "docs/TARGET_ARCHITECTURE.md", "docs/PROJECT_STRUCTURE.md",
)
REQUIRED_GITIGNORE_PATTERNS = (
    ".venv/", "data/", "logs/", "profiles/", "build/", "dist/", "graphify-out/", ".serena/cache/",
)
DEFAULT_LONG_FILE_LIMIT = 300
EXTENDED_LONG_FILE_LIMIT = 450
EXTENDED_LONG_FILE_PATH_PREFIXES = ("tests/", "scripts/")
EXTENDED_LONG_FILE_PATHS: set[str] = set()
LEGACY_ARCHIVE_PATHS: set[str] = set()
RUNTIME_PATH_PREFIXES = ("launcher/", "utils/", "stores/", "models/")
STORE_SPECIFIC_IMPORT_ALLOWED_PATHS = {"utils/store_catalog_registry.py"}
STORE_SPECIFIC_IMPORT_ALLOWED_PREFIXES = ("stores/pyaterochka/", "utils/pyaterochka_")
STORE_SPECIFIC_IMPORT_PREFIXES = ("stores.pyaterochka", "utils.pyaterochka_")
RLM_IMPORT_PREFIXES = ("rlm", "rlms")


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
    if rel in LEGACY_ARCHIVE_PATHS:
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    findings: list[Finding] = []

    long_file_limit = _long_file_limit_for_path(rel)
    if len(lines) > long_file_limit:
        findings.append(
            Finding(
                severity="warning",
                code="long-file",
                path=rel,
                line=0,
                message=f"Python file has {len(lines)} lines; target is <= {long_file_limit} for this file class.",
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
        if _is_runtime_path(rel):
            imported_module = _script_import_module(node)
            if imported_module:
                findings.append(
                    Finding(
                        severity="error",
                        code="runtime-imports-script",
                        path=rel,
                        line=getattr(node, "lineno", 0),
                        message=f"Runtime code must not import script entrypoints ({imported_module}).",
                    )
                )
            archive_module = _archive_import_module(node)
            if archive_module:
                findings.append(
                    Finding(
                        severity="error",
                        code="runtime-imports-archive",
                        path=rel,
                        line=getattr(node, "lineno", 0),
                        message=f"Active runtime must not import archived legacy code ({archive_module}).",
                    )
                )
            store_module = _store_specific_import_module(node)
            if store_module and not _allows_store_specific_import(rel):
                findings.append(
                    Finding(
                        severity="error",
                        code="shared-root-store-specific-import",
                        path=rel,
                        line=getattr(node, "lineno", 0),
                        message=f"Shared runtime must not import store-specific code directly ({store_module}).",
                    )
                )
            rlm_module = _rlm_import_module(node)
            if rlm_module:
                findings.append(
                    Finding(
                        severity="error",
                        code="runtime-imports-rlm",
                        path=rel,
                        line=getattr(node, "lineno", 0),
                        message=(
                            "RLM packages are Codex sidecar tooling only and must not "
                            f"be imported by product runtime ({rlm_module})."
                        ),
                    )
                )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                findings.append(
                    Finding(
                        severity="error" if _is_runtime_path(rel) else "warning",
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
                if not rel.startswith("tests/"):
                    findings.append(
                        Finding(
                            severity="warning",
                            code="close-call",
                            path=rel,
                            line=node.lineno,
                            message="Review close() call; AsyncCamoufox must be closed via async with or __aexit__.",
                        )
                    )
    return findings


def _is_runtime_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in RUNTIME_PATH_PREFIXES)


def _script_import_module(node: ast.AST) -> str:
    return _matched_import_module(node, ("scripts",), exact_prefix=True)


def _archive_import_module(node: ast.AST) -> str:
    return _matched_import_module(node, ("archive",), exact_prefix=True)


def _store_specific_import_module(node: ast.AST) -> str:
    return _matched_import_module(node, STORE_SPECIFIC_IMPORT_PREFIXES)


def _rlm_import_module(node: ast.AST) -> str:
    return _matched_import_module(node, RLM_IMPORT_PREFIXES, exact_prefix=True)


def _matched_import_module(
    node: ast.AST,
    prefixes: tuple[str, ...],
    *,
    exact_prefix: bool = False,
) -> str:
    modules: list[str] = []
    if isinstance(node, ast.ImportFrom):
        modules.append(str(node.module or ""))
    elif isinstance(node, ast.Import):
        modules.extend(str(alias.name or "") for alias in node.names)
    for module in modules:
        for prefix in prefixes:
            if exact_prefix:
                if module == prefix or module.startswith(f"{prefix}."):
                    return module
            elif module.startswith(prefix):
                return module
    return ""


def _allows_store_specific_import(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    return normalized in STORE_SPECIFIC_IMPORT_ALLOWED_PATHS or normalized.startswith(STORE_SPECIFIC_IMPORT_ALLOWED_PREFIXES)


def _long_file_limit_for_path(rel_path: str) -> int:
    normalized = rel_path.replace("\\", "/")
    if normalized in EXTENDED_LONG_FILE_PATHS:
        return EXTENDED_LONG_FILE_LIMIT
    if any(normalized.startswith(prefix) for prefix in EXTENDED_LONG_FILE_PATH_PREFIXES):
        return EXTENDED_LONG_FILE_LIMIT
    return DEFAULT_LONG_FILE_LIMIT


def check_active_runtime_imports(root: Path = ROOT) -> list[Finding]:
    script = (
        "from utils.local_task_registry import list_local_tasks\n"
        "from utils.store_catalog_registry import get_store_export_backend\n"
        "tasks = set(list_local_tasks())\n"
        "required = {'site_onboarding_discovery', 'store_catalog_export', 'store_report_export'}\n"
        "missing = sorted(required - tasks)\n"
        "if missing:\n"
        "    raise RuntimeError(f'missing local tasks: {missing}')\n"
        "backend = get_store_export_backend('pyaterochka', 'fish_catalog')\n"
        "if backend.shop != 'pyaterochka' or backend.intent != 'fish_catalog':\n"
        "    raise RuntimeError('invalid Pyaterochka store export backend')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    findings: list[Finding] = []
    if result.returncode != 0:
        findings.append(
            Finding(
                severity="warning",
                code="active-runtime-import",
                path="utils/local_task_registry.py",
                line=0,
                message=result.stderr.strip() or "Active runtime import check failed.",
            )
        )
    return findings


def check_required_startup_docs(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for rel_path in REQUIRED_STARTUP_DOCS:
        path = root / rel_path
        if not path.exists():
            findings.append(Finding("error", "startup-doc-missing", rel_path, 0, "Required startup document is missing."))
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for marker in REMOVED_STARTUP_DOC_MARKERS:
                if marker in line:
                    findings.append(
                        Finding(
                            severity="error",
                            code="startup-doc-removed-reference",
                            path=rel_path,
                            line=line_number,
                            message=f"Required startup docs must not point to removed legacy context ({marker}).",
                        )
                    )
    return findings


def check_local_runtime_ignore_policy(root: Path = ROOT) -> list[Finding]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return [Finding("error", "gitignore-missing", ".gitignore", 0, "Local runtime and generated artifact ignore policy is missing.")]
    patterns = {
        line.strip()
        for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    findings: list[Finding] = []
    for pattern in REQUIRED_GITIGNORE_PATTERNS:
        if pattern not in patterns:
            findings.append(
                Finding("error", "runtime-ignore-policy", ".gitignore", 0, f"Local runtime/generated path must stay ignored: {pattern}")
            )
    return findings


def collect_findings(root: Path = ROOT) -> list[Finding]:
    findings = find_tracked_artifacts(tracked_files(root))
    findings.extend(check_required_startup_docs(root))
    findings.extend(check_local_runtime_ignore_policy(root))
    findings.extend(check_encoding_integrity(root))
    for file_path in iter_python_files(root):
        findings.extend(scan_python_file(file_path, root=root))
    findings.extend(check_active_runtime_imports(root))
    return sorted(findings, key=lambda item: (item.severity, item.code, item.path, item.line))


def check_encoding_integrity(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for item in collect_encoding_findings(root, mode="all"):
        findings.append(
            Finding(
                severity="error",
                code=item.code,
                path=item.path,
                line=item.line,
                message=f"Unexpected encoding artifact marker {item.marker!r}; update text or explicit baseline.",
            )
        )
    return findings


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
