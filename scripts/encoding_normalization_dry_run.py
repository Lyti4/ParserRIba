"""Dry-run mojibake normalization candidates before changing fixtures."""

from __future__ import annotations

import argparse
import ast
import io
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from ftfy import fix_and_explain
except ImportError:  # pragma: no cover - exercised by fallback tests through monkeypatching.
    fix_and_explain = None


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.encoding_guard import load_compatibility_markers, scan_file

PYTHON_SUFFIX = ".py"
REPLACEMENT_CHAR = "\ufffd"
MOJIBAKE_STARTS = ("\u0420", "\u0421")
RISK_KEYWORDS = {
    "category": "category/filter matching",
    "categories": "category/filter matching",
    "subcategory": "subcategory/filter matching",
    "subcategories": "subcategory/filter matching",
    "wine_styles": "subcategory/filter matching",
    "alcohol_type": "wine facet parsing",
    "alcohol_types": "wine facet parsing",
    "name": "product parsing",
    "selected_categories": "selection persistence",
    "sheetnames": "Excel sheet naming",
    "report_summary": "report summary",
    "available_filters": "filter options",
    "available_filter_counts": "filter options",
    "products_count": "product count expectation",
}
INTENTIONAL_MARKER_PATHS = {"scripts/encoding_guard.py"}


@dataclass(frozen=True)
class NormalizationCandidate:
    """One reversible mojibake string literal candidate."""

    path: str
    line: int
    test_name: str
    old: str
    new: str
    risk: str
    method: str
    explanation: str
    action: str


def collect_candidates(paths: Iterable[Path], *, root: Path = ROOT) -> list[NormalizationCandidate]:
    """Collect reversible string literal repairs for Python files."""
    candidates: list[NormalizationCandidate] = []
    for path in sorted(set(paths)):
        if path.suffix != PYTHON_SUFFIX or not path.exists():
            continue
        candidates.extend(_scan_python_file(path, root=root))
    return sorted(candidates, key=lambda item: (item.path, item.line, item.old))


def render_candidates(candidates: Iterable[NormalizationCandidate]) -> str:
    """Render dry-run report."""
    items = list(candidates)
    if not items:
        return "Encoding normalization dry-run: no reversible candidates."
    lines = ["# ParserRIba Encoding Normalization Dry-Run", ""]
    for item in items:
        lines.append(f"- `{item.path}:{item.line}` `{item.test_name}` risk={item.risk}")
        lines.append(f"  action: {item.action}")
        lines.append(f"  method: {item.method}")
        if item.explanation:
            lines.append(f"  explanation: {item.explanation}")
        lines.append(f"  old: {_ascii_text(item.old)}")
        lines.append(f"  new: {_ascii_text(item.new)}")
    return "\n".join(lines)


def tracked_python_paths(root: Path = ROOT) -> list[Path]:
    """Return tracked Python files."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    return [root / line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def baseline_python_paths(root: Path = ROOT) -> list[Path]:
    """Return Python paths currently present in the encoding baseline."""
    baseline = root / "scripts" / "encoding_guard_baseline.json"
    if not baseline.exists():
        return []
    import json

    payload = json.loads(baseline.read_text(encoding="utf-8"))
    allowed = payload.get("allowed", {}) if isinstance(payload, dict) else {}
    return [root / path for path in allowed if str(path).endswith(PYTHON_SUFFIX)]


def changed_python_paths(root: Path = ROOT) -> list[Path]:
    """Return changed Python paths."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    return [root / line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip().endswith(PYTHON_SUFFIX)]


def main() -> int:
    """Run the dry-run CLI."""
    parser = argparse.ArgumentParser(
        description="Preview ParserRIba mojibake normalization candidates. Dry-run only; never writes files."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="scan all tracked Python files")
    mode.add_argument("--baseline", action="store_true", help="scan Python files still listed in encoding baseline")
    mode.add_argument("--changed", action="store_true", help="scan changed Python files")
    parser.add_argument("paths", nargs="*", help="specific Python files to scan")
    args = parser.parse_args()

    if args.paths:
        paths = [ROOT / value.replace("\\", "/") for value in args.paths]
    elif args.all:
        paths = tracked_python_paths(ROOT)
    elif args.changed:
        paths = changed_python_paths(ROOT)
    else:
        paths = baseline_python_paths(ROOT)
    sys.stdout.write(render_candidates(collect_candidates(paths, root=ROOT)) + "\n")
    return 0


def _scan_python_file(path: Path, *, root: Path) -> list[NormalizationCandidate]:
    rel = path.relative_to(root).as_posix()
    source = path.read_text(encoding="utf-8")
    compatibility_lines = _compatibility_lines(path, root=root)
    test_names = _test_names_by_line(source)
    candidates: list[NormalizationCandidate] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING or not any(marker in token.string for marker in MOJIBAKE_STARTS):
            continue
        value = _literal_string(token.string)
        if value is None or not any(marker in value for marker in MOJIBAKE_STARTS):
            continue
        repaired, method, explanation = _best_repair(value)
        if _is_useful_repair(value, repaired):
            line = source.splitlines()[token.start[0] - 1]
            risk = _risk_for_line(line)
            action = _action_for_candidate(risk, token.start[0] in compatibility_lines)
            candidates.append(
                NormalizationCandidate(
                    path=rel,
                    line=token.start[0],
                    test_name=_nearest_test_name(test_names, token.start[0]),
                    old=value,
                    new=repaired or "",
                    risk="intentional-compatibility" if action == "allowlist" else risk,
                    method=method,
                    explanation=explanation,
                    action=action,
                )
            )
    return candidates


def _literal_string(token_text: str) -> str | None:
    try:
        value = ast.literal_eval(token_text)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


def _repair_segment(value: str) -> str | None:
    try:
        raw = bytearray()
        for char in value:
            codepoint = ord(char)
            if codepoint < 256:
                raw.append(codepoint)
            else:
                raw.extend(char.encode("cp1251"))
        return bytes(raw).decode("utf-8")
    except UnicodeError:
        return None


def _best_repair(value: str) -> tuple[str | None, str, str]:
    ftfy_repaired, ftfy_explanation = _repair_with_ftfy(value)
    manual_repaired = _repair_segment(value)
    options = [
        ("ftfy", ftfy_repaired, ftfy_explanation),
        ("cp1251-repair", manual_repaired, "encode cp1251 -> decode utf-8"),
    ]
    useful = [(method, repaired, explanation) for method, repaired, explanation in options if _is_useful_repair(value, repaired)]
    if not useful:
        return None, "", ""
    method, repaired, explanation = max(useful, key=lambda item: _repair_score(value, item[1] or ""))
    return repaired, method, explanation


def _repair_with_ftfy(value: str) -> tuple[str | None, str]:
    if fix_and_explain is None:
        return None, ""
    try:
        repaired, plan = fix_and_explain(value)
    except Exception:
        return None, ""
    explanation = ", ".join(str(step) for step in plan)
    return repaired, explanation


def _is_useful_repair(old: str, new: str | None) -> bool:
    if not new or new == old or REPLACEMENT_CHAR in new:
        return False
    old_mojibake = sum(old.count(marker) for marker in MOJIBAKE_STARTS)
    new_mojibake = sum(new.count(marker) for marker in MOJIBAKE_STARTS)
    return new_mojibake < old_mojibake


def _repair_score(old: str, new: str) -> int:
    old_mojibake = sum(old.count(marker) for marker in MOJIBAKE_STARTS)
    new_mojibake = sum(new.count(marker) for marker in MOJIBAKE_STARTS)
    return old_mojibake - new_mojibake


def _test_names_by_line(source: str) -> list[tuple[int, str]]:
    names: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            names.append((node.lineno, node.name))
    return sorted(names)


def _nearest_test_name(names: list[tuple[int, str]], line: int) -> str:
    current = "<module>"
    for lineno, name in names:
        if lineno > line:
            break
        current = name
    return current


def _risk_for_line(line: str) -> str:
    lowered = line.lower()
    reasons = [reason for keyword, reason in RISK_KEYWORDS.items() if keyword.lower() in lowered]
    if reasons:
        return "behavior-affecting: " + ", ".join(sorted(set(reasons)))
    if "assert" in lowered:
        return "assertion"
    return "text-only"


def _action_for_candidate(risk: str, is_compatibility: bool) -> str:
    if is_compatibility:
        return "allowlist"
    if risk.startswith("behavior-affecting"):
        return "manual-review"
    return "repair"


def _compatibility_lines(path: Path, *, root: Path) -> set[int]:
    rel_path = path.relative_to(root).as_posix()
    if rel_path in INTENTIONAL_MARKER_PATHS:
        return {finding.line for finding in scan_file(path, root=root, baseline={}, compatibility={})}
    compatibility = load_compatibility_markers(root / "scripts" / "encoding_guard_compatibility.json")
    markers = compatibility.get(rel_path, {})
    if not markers:
        return set()
    return {
        finding.line
        for finding in scan_file(path, root=root, baseline={}, compatibility={})
        if finding.fingerprint in markers
    }


def _ascii_text(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


if __name__ == "__main__":
    raise SystemExit(main())
