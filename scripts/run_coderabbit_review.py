"""Run CodeRabbit review safely from Windows through WSL."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.coderabbit_review import (
    build_wsl_review_command,
    evaluate_review_preflight,
    parse_git_status_lines,
)


def _configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CodeRabbit review through WSL")
    parser.add_argument("--scope", choices=("committed", "uncommitted"), default="committed")
    parser.add_argument("--base", default="main")
    parser.add_argument("--config", action="append", default=["AGENTS.md"])
    parser.add_argument("--dir", default="")
    parser.add_argument("--distro", default="Ubuntu")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser.parse_args(argv)


def _git_status_lines() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _commits_ahead_of_base(base: str) -> int:
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base}..HEAD"],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return int(result.stdout.strip() or "0")


def _check_coderabbit_auth(distro: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "wsl.exe",
            "-d",
            distro,
            "--",
            "bash",
            "-lc",
            "source /home/lyti4/.bashrc && coderabbit auth status --agent",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


if __name__ == "__main__":
    _configure_stdio()
    args = _parse_args()
    snapshot = parse_git_status_lines(_git_status_lines())
    commits_ahead = _commits_ahead_of_base(args.base) if args.scope == "committed" else None
    preflight = evaluate_review_preflight(
        snapshot,
        scope=args.scope,
        commits_ahead_of_base=commits_ahead,
    )
    if not preflight.ok:
        sys.stdout.write(
            json.dumps(
                {
                    "status": "blocked",
                    "scope": args.scope,
                    "warnings": preflight.warnings,
                    "errors": preflight.errors,
                    "changed_paths": snapshot.changed_paths,
                    "commits_ahead_of_base": commits_ahead,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(2)

    auth_result = _check_coderabbit_auth(args.distro)
    if auth_result.returncode != 0:
        sys.stdout.write(
            json.dumps(
                {
                    "status": "blocked",
                    "scope": args.scope,
                    "warnings": preflight.warnings,
                    "errors": ["CodeRabbit auth check failed."],
                    "auth_stdout": auth_result.stdout,
                    "auth_stderr": auth_result.stderr,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(2)

    command = build_wsl_review_command(
        root_dir=ROOT_DIR,
        scope=args.scope,
        base=args.base,
        config_files=args.config,
        review_dir=args.dir,
        distro=args.distro,
    )
    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=args.timeout_seconds,
    )
    sys.stdout.write(
        json.dumps(
            {
                "status": "completed" if result.returncode == 0 else "failed",
                "scope": args.scope,
                "warnings": preflight.warnings,
                "returncode": result.returncode,
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(result.returncode)
