"""Install CloakBrowser binary into ParserRIba's ignored local browser cache."""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLOAK_CACHE_DIR = PROJECT_ROOT / "profiles" / "browser_binaries" / "cloakbrowser"


def main() -> int:
    """Install the optional CloakBrowser binary into an ASCII-safe project cache."""
    try:
        from cloakbrowser import binary_info, ensure_binary
    except ModuleNotFoundError:
        logger.error("CloakBrowser package is not installed. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements-browser-alt.txt")
        return 1

    CLOAK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["CLOAKBROWSER_CACHE_DIR"] = str(CLOAK_CACHE_DIR)
    os.environ["CLOAKBROWSER_AUTO_UPDATE"] = "false"

    before = binary_info()
    if before.get("installed"):
        logger.info("CloakBrowser already installed: {}", before.get("binary_path"))
        return 0

    binary_path = ensure_binary()
    after = binary_info()
    if not after.get("installed"):
        logger.error("CloakBrowser install finished but binary is still unavailable: {}", after)
        return 2

    logger.info("CloakBrowser installed: {}", binary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
