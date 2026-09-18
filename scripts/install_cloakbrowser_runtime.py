"""Install CloakBrowser binary into ParserRIba's ignored local browser cache."""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLOAK_CACHE_DIR = PROJECT_ROOT / "profiles" / "browser_binaries" / "cloakbrowser"


def _effective_cache_dir() -> Path:
    value = os.environ.get("CLOAKBROWSER_CACHE_DIR")
    return Path(value) if value else CLOAK_CACHE_DIR


def _verified_binary_path(binary_path: Path, cache_dir: Path) -> bool:
    try:
        binary_path.resolve().relative_to(cache_dir.resolve())
    except ValueError:
        return False
    return binary_path.is_file()


def main() -> int:
    """Install the optional CloakBrowser binary into an ASCII-safe project cache."""
    try:
        from cloakbrowser import binary_info, ensure_binary
    except ModuleNotFoundError:
        logger.error("CloakBrowser package is not installed. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements-browser-alt.txt")
        return 1

    cache_dir = _effective_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CLOAKBROWSER_CACHE_DIR", str(cache_dir))
    os.environ["CLOAKBROWSER_AUTO_UPDATE"] = "false"

    before = binary_info()
    before_path = Path(str(before.get("binary_path") or ""))
    if before.get("installed") and _verified_binary_path(before_path, cache_dir):
        logger.info("CloakBrowser binary already verified in configured cache.")
        return 0

    binary_path = ensure_binary()
    after = binary_info()
    resolved_path = Path(str(binary_path))
    if not _verified_binary_path(resolved_path, cache_dir):
        logger.error("CloakBrowser provisioning did not produce a verified executable in the configured cache.")
        return 2

    logger.info("CloakBrowser binary provisioned and verified in the configured cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
