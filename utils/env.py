"""Small .env loader for local ParserRIba settings."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file.

    The project already depends on python-dotenv, but this tiny loader keeps
    bootstrap scripts usable even before optional tooling is initialized.
    """
    env_path = Path(path)
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


def read_dotenv_values(path: str | Path = ".env") -> dict[str, str]:
    """Read KEY=VALUE pairs from a .env file without mutating os.environ."""
    env_path = Path(path)
    if not env_path.exists():
        return {}
    return _parse_dotenv_lines(env_path.read_text(encoding="utf-8").splitlines())


def update_dotenv_values(path: str | Path, updates: dict[str, str]) -> Path:
    """Update or append KEY=VALUE pairs while preserving unrelated .env lines."""
    env_path = Path(path)
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen: set[str] = set()
    rewritten: list[str] = []
    for line in lines:
        key = _dotenv_line_key(line)
        if key and key in updates:
            rewritten.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            rewritten.append(line)
    for key, value in updates.items():
        if key not in seen:
            rewritten.append(f"{key}={value}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")
    return env_path


def _parse_dotenv_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def _dotenv_line_key(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return ""
    key = stripped.split("=", 1)[0].strip()
    return key if key else ""
