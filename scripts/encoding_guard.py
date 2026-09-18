"""Diff-aware encoding guard for ParserRIba text surfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "scripts" / "encoding_guard_baseline.json"
COMPATIBILITY_PATH = ROOT / "scripts" / "encoding_guard_compatibility.json"
SCAN_PREFIXES = ("launcher/", "tests/", "docs/", "specs/", "utils/")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml"}
BOM = b"\xef\xbb\xbf"
MOJIBAKE_MARKERS = (
    "\u0420\u040e",
    "\u0420\u045f",
    "\u0420\u045a",
    "\u0420\u0459",
    "\u0420\u2019",
    "\u0420\u045b",
    "\u0420\u2014",
    "\u0420\u045c",
    "\u0420\xa0",
    "\u0420\u0491",
    "\u0420\xb5",
    "\u0420\u0451",
    "\u0420\u2116",
    "\u0421\u0403",
    "\u0421\u201a",
    "\u0421\u2021",
    "\u0421\u2039",
    "\u0421\u040a",
    "\u0421\u040b",
    "\u0421\u040f",
    "\u0421\u2026",
    "\u0421\u0402",
    "\xd0",
    "\xd1",
    "\u00e2\u201d",
    "\u00e2\u2022",
    "\u00e2\u20ac",
    "\u00e2\u20ac\u201c",
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u00a6",
    "\u00ef\u00bb\u00bf",
)
REPLACEMENT_CHAR = "\ufffd"
C1_CONTROL_CHARS = frozenset(chr(value) for value in range(0x80, 0xA0))


@dataclass(frozen=True)
class EncodingFinding:
    """One encoding integrity finding."""

    code: str
    path: str
    line: int
    marker: str
    text: str

    @property
    def fingerprint(self) -> str:
        payload = f"{self.code}|{self.marker}|{self.text.strip()}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CompatibilityMarker:
    """Intentional mojibake-like marker used for legacy input compatibility."""

    path: str
    fingerprint: str
    marker: str
    reason: str


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, set[str]]:
    """Load allowed legacy finding fingerprints by repo path."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_allowed = payload.get("allowed", {}) if isinstance(payload, dict) else {}
    return {
        str(file_path).replace("\\", "/"): {str(item) for item in fingerprints}
        for file_path, fingerprints in raw_allowed.items()
        if isinstance(fingerprints, list)
    }


def load_compatibility_markers(path: Path = COMPATIBILITY_PATH) -> dict[str, dict[str, CompatibilityMarker]]:
    """Load intentional compatibility markers by repo path and fingerprint."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_allowed = payload.get("allowed", []) if isinstance(payload, dict) else []
    markers: dict[str, dict[str, CompatibilityMarker]] = {}
    for item in raw_allowed:
        if not isinstance(item, dict):
            continue
        marker = CompatibilityMarker(
            path=str(item.get("path", "")).replace("\\", "/"),
            fingerprint=str(item.get("fingerprint", "")),
            marker=str(item.get("marker", "")),
            reason=str(item.get("reason", "")),
        )
        if marker.path and marker.fingerprint and marker.reason:
            markers.setdefault(marker.path, {})[marker.fingerprint] = marker
    return markers


def write_baseline(findings: Iterable[EncodingFinding], path: Path = BASELINE_PATH) -> None:
    """Write the current non-BOM legacy findings as an explicit baseline."""
    allowed: dict[str, list[str]] = {}
    for finding in findings:
        if finding.code == "encoding-bom":
            continue
        allowed.setdefault(finding.path, []).append(finding.fingerprint)
    payload = {
        "version": 1,
        "note": "Legacy ParserRIba mojibake baseline. Do not add entries without review.",
        "allowed": {key: sorted(set(values)) for key, values in sorted(allowed.items())},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def scan_file(
    path: Path,
    *,
    root: Path = ROOT,
    baseline: dict[str, set[str]] | None = None,
    compatibility: dict[str, dict[str, CompatibilityMarker]] | None = None,
) -> list[EncodingFinding]:
    """Scan one text file and return non-baselined encoding findings."""
    rel = path.relative_to(root).as_posix()
    data = path.read_bytes()
    findings: list[EncodingFinding] = []
    if data.startswith(BOM):
        findings.append(EncodingFinding("encoding-bom", rel, 1, "utf8-bom", "UTF-8 BOM"))
    text = data.decode("utf-8", errors="replace")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if REPLACEMENT_CHAR in line:
            findings.append(EncodingFinding("encoding-replacement-char", rel, line_number, REPLACEMENT_CHAR, line))
        c1_marker = _first_c1_control_marker(line)
        if c1_marker:
            findings.append(EncodingFinding("encoding-c1-control", rel, line_number, c1_marker, line))
        marker = _first_mojibake_marker(line)
        if marker:
            findings.append(EncodingFinding("encoding-mojibake", rel, line_number, marker, line))
    return _without_accepted_findings(findings, baseline or {}, compatibility or {})


def scan_paths(
    paths: Iterable[Path],
    *,
    root: Path = ROOT,
    baseline: dict[str, set[str]] | None = None,
    compatibility: dict[str, dict[str, CompatibilityMarker]] | None = None,
) -> list[EncodingFinding]:
    """Scan many paths."""
    findings: list[EncodingFinding] = []
    for path in sorted(set(paths)):
        if _is_scannable_path(path, root=root) and path.exists():
            findings.extend(scan_file(path, root=root, baseline=baseline, compatibility=compatibility))
    return sorted(findings, key=lambda item: (item.path, item.line, item.code, item.marker))


def tracked_scan_paths(root: Path = ROOT) -> list[Path]:
    """Return tracked files covered by the encoding guard."""
    lines = _git_lines(["git", "ls-files"], root)
    if lines:
        return [_path_from_git_line(root, item) for item in lines]
    return [path for path in root.rglob("*") if path.is_file()]


def changed_scan_paths(root: Path = ROOT) -> list[Path]:
    """Return tracked files changed against HEAD."""
    return [_path_from_git_line(root, item) for item in _git_lines(["git", "diff", "--name-only", "HEAD"], root)]


def staged_scan_paths(root: Path = ROOT) -> list[Path]:
    """Return staged files."""
    return [_path_from_git_line(root, item) for item in _git_lines(["git", "diff", "--cached", "--name-only"], root)]


def render_findings(findings: Iterable[EncodingFinding]) -> str:
    """Render findings for CLI and architecture reports."""
    items = list(findings)
    if not items:
        return "Encoding guard passed: no findings."
    lines = ["# ParserRIba Encoding Guard", ""]
    for finding in items:
        location = finding.path if finding.line == 0 else f"{finding.path}:{finding.line}"
        lines.append(f"- `{finding.code}` `{location}` marker={finding.marker!r}")
    return "\n".join(lines)


def render_baseline_report(baseline: dict[str, set[str]]) -> str:
    """Render legacy encoding debt by file."""
    total = sum(len(items) for items in baseline.values())
    lines = ["# ParserRIba Encoding Baseline", "", f"- files: {len(baseline)}", f"- findings: {total}"]
    for path, fingerprints in sorted(baseline.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.append(f"- {len(fingerprints):3} {path}")
    return "\n".join(lines)


def render_compatibility_report(compatibility: dict[str, dict[str, CompatibilityMarker]]) -> str:
    """Render intentional compatibility marker summary."""
    total = sum(len(items) for items in compatibility.values())
    lines = ["# ParserRIba Encoding Compatibility Markers", "", f"- files: {len(compatibility)}", f"- markers: {total}"]
    for path, markers in sorted(compatibility.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.append(f"- {len(markers):3} {path}")
    return "\n".join(lines)


def collect_encoding_findings(root: Path = ROOT, *, mode: str = "all") -> list[EncodingFinding]:
    """Collect encoding findings for one scan mode."""
    baseline = load_baseline(root / "scripts" / "encoding_guard_baseline.json")
    compatibility = load_compatibility_markers(root / "scripts" / "encoding_guard_compatibility.json")
    if mode == "changed":
        paths = changed_scan_paths(root)
    elif mode == "staged":
        paths = staged_scan_paths(root)
    else:
        paths = tracked_scan_paths(root)
    return scan_paths(paths, root=root, baseline=baseline, compatibility=compatibility)


def main() -> int:
    """Run the encoding guard CLI."""
    parser = argparse.ArgumentParser(description="Check ParserRIba text encoding integrity")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="scan all tracked text surfaces")
    mode.add_argument("--changed", action="store_true", help="scan files changed against HEAD")
    mode.add_argument("--staged", action="store_true", help="scan staged files")
    parser.add_argument("--update-baseline", action="store_true", help="rewrite legacy mojibake baseline from all files")
    parser.add_argument("--baseline-report", action="store_true", help="print legacy mojibake baseline summary")
    parser.add_argument("--compatibility-report", action="store_true", help="print intentional compatibility marker summary")
    args = parser.parse_args()

    if args.baseline_report:
        sys.stdout.write(render_baseline_report(load_baseline(BASELINE_PATH)) + "\n")
        return 0
    if args.compatibility_report:
        sys.stdout.write(render_compatibility_report(load_compatibility_markers(COMPATIBILITY_PATH)) + "\n")
        return 0
    if args.update_baseline:
        findings = scan_paths(
            tracked_scan_paths(ROOT),
            root=ROOT,
            baseline={},
            compatibility=load_compatibility_markers(COMPATIBILITY_PATH),
        )
        write_baseline(findings, BASELINE_PATH)
        sys.stdout.write(f"Updated {BASELINE_PATH.relative_to(ROOT).as_posix()}\n")
        return 0
    scan_mode = "changed" if args.changed else "staged" if args.staged else "all"
    findings = collect_encoding_findings(ROOT, mode=scan_mode)
    sys.stdout.write(render_findings(findings) + "\n")
    return 1 if findings else 0


def _without_accepted_findings(
    findings: list[EncodingFinding],
    baseline: dict[str, set[str]],
    compatibility: dict[str, dict[str, CompatibilityMarker]],
) -> list[EncodingFinding]:
    result: list[EncodingFinding] = []
    for finding in findings:
        if finding.fingerprint in baseline.get(finding.path, set()):
            continue
        if finding.fingerprint in compatibility.get(finding.path, {}):
            continue
        result.append(finding)
    return result


def _first_mojibake_marker(line: str) -> str:
    for marker in MOJIBAKE_MARKERS:
        if marker in line:
            return marker
    return ""


def _first_c1_control_marker(line: str) -> str:
    for char in line:
        if char in C1_CONTROL_CHARS:
            return f"U+{ord(char):04X}"
    return ""


def _is_scannable_path(path: Path, *, root: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return rel.startswith(SCAN_PREFIXES) and path.suffix.lower() in TEXT_SUFFIXES


def _git_lines(command: list[str], root: Path) -> list[str]:
    result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _path_from_git_line(root: Path, value: str) -> Path:
    return root / value.replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
