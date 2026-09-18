"""GeoIP helpers for Camoufox."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GEOIP_PATH = ROOT_DIR / "GeoLite2-City.mmdb"


def app_root() -> Path:
    """Return project root in source mode or executable folder in frozen mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT_DIR


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

    candidates = [
        app_root() / "GeoLite2-City.mmdb",
        DEFAULT_GEOIP_PATH,
        Path(getattr(sys, "_MEIPASS", app_root())) / "GeoLite2-City.mmdb",
    ]
    for path in candidates:
        if path.exists():
            return path
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


def lookup_ip_geoip(ip: str) -> dict[str, Any]:
    """Return a small report-safe GeoIP summary for an IP address."""
    if not ip or not geoip_extra_installed():
        return {}
    database_path = geoip_database_path()
    if not database_path:
        return {}
    try:
        import geoip2.database
        import geoip2.errors

        with geoip2.database.Reader(str(database_path)) as reader:
            response = reader.city(ip)
        return {
            "ip": ip,
            "country_iso": response.country.iso_code or "",
            "country_name": response.country.name or "",
            "city": response.city.name or "",
            "timezone": response.location.time_zone or "",
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
        }
    except Exception as exc:
        logger.debug("GeoIP lookup failed for {}: {}", ip, exc)
        return {}
