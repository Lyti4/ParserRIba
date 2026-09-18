"""Run a command and save exact decoded output outside PowerShell rendering."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / "logs" / "agent_utf8"
PREFERRED_ENCODINGS = ("utf-8", "cp866", "cp1251")


@dataclass(frozen=True)
class CapturedOutput:
    """Captured command output decoded with best effort."""

    returncode: int
    stdout: str
    stderr: str
    stdout_encoding: str
    stderr_encoding: str


def run_command(command: list[str], *, cwd: Path = ROOT) -> CapturedOutput:
    """Run a command and capture raw bytes before decoding."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True)
    stdout, stdout_encoding = _decode_bytes(result.stdout)
    stderr, stderr_encoding = _decode_bytes(result.stderr)
    return CapturedOutput(
        returncode=result.returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_encoding=stdout_encoding,
        stderr_encoding=stderr_encoding,
    )


def write_capture(capture: CapturedOutput, *, command: list[str], log_dir: Path = DEFAULT_LOG_DIR) -> Path:
    """Write command output to a UTF-8 diagnostic file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"{timestamp}-command-output.txt"
    payload = "\n".join(
        [
            "# ParserRIba UTF-8 Command Capture",
            "",
            f"command: {_quote_command(command)}",
            f"returncode: {capture.returncode}",
            f"stdout_encoding: {capture.stdout_encoding}",
            f"stderr_encoding: {capture.stderr_encoding}",
            "",
            "## STDOUT",
            capture.stdout,
            "",
            "## STDERR",
            capture.stderr,
            "",
        ]
    )
    path.write_text(payload, encoding="utf-8")
    return path


def render_preview(capture: CapturedOutput, *, log_path: Path, limit: int = 4000) -> str:
    """Render ASCII-safe preview for unreliable terminals."""
    stdout = _ascii_preview(capture.stdout, limit=limit)
    stderr = _ascii_preview(capture.stderr, limit=limit)
    lines = [
        "# ParserRIba UTF-8 Command",
        "",
        f"- returncode: {capture.returncode}",
        f"- stdout_encoding: {capture.stdout_encoding}",
        f"- stderr_encoding: {capture.stderr_encoding}",
        f"- utf8_log: {log_path}",
        "",
        "## STDOUT unicode_escape",
        stdout or "<empty>",
        "",
        "## STDERR unicode_escape",
        stderr or "<empty>",
    ]
    return "\n".join(lines)


def render_json(capture: CapturedOutput, *, log_path: Path) -> str:
    """Render a machine-readable command capture summary."""
    payload = {
        "returncode": capture.returncode,
        "stdout_encoding": capture.stdout_encoding,
        "stderr_encoding": capture.stderr_encoding,
        "utf8_log": str(log_path),
        "stdout_unicode_escape": _ascii_preview(capture.stdout, limit=10000),
        "stderr_unicode_escape": _ascii_preview(capture.stderr, limit=10000),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def main(argv: list[str] | None = None) -> int:
    """Run the wrapper CLI."""
    parser = argparse.ArgumentParser(description="Run a command with UTF-8 capture and ASCII-safe preview")
    parser.add_argument("--cwd", default=str(ROOT), help="working directory for the command")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="directory for UTF-8 output files")
    parser.add_argument("--preview-limit", type=int, default=4000, help="characters per stream in terminal preview")
    parser.add_argument("--json", action="store_true", help="print a machine-readable ASCII-safe summary")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command to run after --")
    args = parser.parse_args(argv)

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command is required; use: utf8_command.py -- <command> [args...]")

    capture = run_command(command, cwd=Path(args.cwd))
    log_path = write_capture(capture, command=command, log_dir=Path(args.log_dir))
    if args.json:
        sys.stdout.write(render_json(capture, log_path=log_path) + "\n")
    else:
        sys.stdout.write(render_preview(capture, log_path=log_path, limit=args.preview_limit) + "\n")
    return capture.returncode


def _decode_bytes(data: bytes) -> tuple[str, str]:
    for encoding in PREFERRED_ENCODINGS:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def _ascii_preview(value: str, *, limit: int) -> str:
    clipped = value[:limit]
    suffix = "\n<truncated>" if len(value) > limit else ""
    return clipped.encode("unicode_escape").decode("ascii") + suffix


def _quote_command(command: list[str]) -> str:
    return " ".join(_quote_part(part) for part in command)


def _quote_part(part: str) -> str:
    if not part or any(char.isspace() for char in part):
        return '"' + part.replace('"', '\\"') + '"'
    return part


if __name__ == "__main__":
    raise SystemExit(main())
