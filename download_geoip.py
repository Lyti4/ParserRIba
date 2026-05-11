"""Download GeoLite2 City database for Camoufox GeoIP mode."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

GEOIP_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"
ROOT_DIR = Path(__file__).resolve().parent
GEOIP_PATH = ROOT_DIR / "GeoLite2-City.mmdb"


def download_geoip() -> Path | None:
    """Download GeoLite2-City.mmdb into the project root."""
    if GEOIP_PATH.exists() and GEOIP_PATH.stat().st_size > 1_000_000:
        logger.info("GeoIP database already exists: {}", GEOIP_PATH)
        return GEOIP_PATH

    logger.info("Downloading GeoIP database from {}", GEOIP_URL)
    try:
        with urlopen(GEOIP_URL, timeout=60) as response:
            total = int(response.headers.get("content-length", "0") or "0")
            downloaded = 0
            next_report = 10
            with GEOIP_PATH.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded / total * 100
                        if percent >= next_report:
                            logger.info("GeoIP download: {:.0f}%", percent)
                            next_report += 10

        if GEOIP_PATH.stat().st_size <= 1_000_000:
            GEOIP_PATH.unlink(missing_ok=True)
            raise RuntimeError("Downloaded GeoIP database is too small")

        logger.info("GeoIP database saved: {}", GEOIP_PATH)
        return GEOIP_PATH
    except (OSError, URLError, RuntimeError) as exc:
        logger.error("GeoIP download failed: {}", exc)
        GEOIP_PATH.unlink(missing_ok=True)
        return None


if __name__ == "__main__":
    path = download_geoip()
    if path:
        logger.info("Done. You can run the parser with PARSER_GEOIP=1")
    else:
        sys.exit(1)
