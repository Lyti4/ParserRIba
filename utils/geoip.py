"""GeoIP helpers for Camoufox."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GEOIP_PATH = ROOT_DIR / "GeoLite2-City.mmdb"


def geoip_extra_installed() -> bool:
    """Return True when camoufox[geoip] dependencies are available."""
    return importlib.util.find_spec("geoip2") is not None


def geoip_database_path() -> Path | None:
    """Return the configured GeoIP database path if it exists."""
    env_path = os.environ.get("GEOIP_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    if DEFAULT_GEOIP_PATH.exists():
        return DEFAULT_GEOIP_PATH
    return None


def prepare_geoip() -> bool:
    """Prepare GeoIP environment variables for Camoufox."""
    if not geoip_extra_installed():
        logger.warning("camoufox[geoip] is not installed; disabling geoip")
        return False

    database_path = geoip_database_path()
    if not database_path:
        logger.warning("GeoIP database not found; run download_geoip.py")
        return False

    # ИЗМЕНЕНО: Camoufox читает GEOIP_PATH из окружения.
    os.environ["GEOIP_PATH"] = str(database_path)
    logger.info("GeoIP database enabled: {}", database_path)
    return True
