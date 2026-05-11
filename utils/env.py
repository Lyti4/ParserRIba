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
