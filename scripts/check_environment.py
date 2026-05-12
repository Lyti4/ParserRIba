"""Check local ParserRIba runtime, Camoufox, GeoIP and proxy setup."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.camoufox_launcher import configure_windows_console, resolve_camoufox_executable
from utils.env import load_dotenv_file
from utils.geoip import app_root, geoip_database_path, geoip_extra_installed
from utils.proxy import load_proxy_urls, mask_proxy_url, parse_proxy_url

CHECK_IP_URL = "http://api.ipify.org?format=json"


def _check_import(module_name: str) -> bool:
    """Return True when a module can be imported."""
    try:
        __import__(module_name)
        logger.info("{}: ok", module_name)
        return True
    except Exception as exc:
        logger.error("{}: {}", module_name, exc)
        return False


def _check_proxy(proxy_url: str) -> bool:
    """Check proxy syntax and external IP without logging credentials."""
    parsed = parse_proxy_url(proxy_url)
    logger.info("Proxy config: {}", mask_proxy_url(proxy_url))
    logger.info("Proxy server: {}", parsed.server)

    opener = build_opener(
        ProxyHandler(
            {
                "http": proxy_url,
                "https": proxy_url,
            }
        )
    )
    try:
        with opener.open(CHECK_IP_URL, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        logger.info("Proxy external IP: {}", payload.get("ip", "unknown"))
        return True
    except (OSError, URLError, json.JSONDecodeError) as exc:
        logger.error("Proxy check failed: {}", exc)
        return False


def main() -> int:
    """Run environment checks and return a shell exit code."""
    configure_windows_console()
    load_dotenv_file(app_root() / ".env")

    ok = True
    logger.info("Python: {}", sys.version.split()[0])
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ is required")
        ok = False

    for module_name in ("camoufox", "playwright", "pydantic", "loguru"):
        ok = _check_import(module_name) and ok

    browser_path = resolve_camoufox_executable()
    if browser_path:
        logger.info("Camoufox executable: {}", browser_path)
    else:
        logger.warning("Camoufox executable was not found; package fetch may be required")

    if geoip_extra_installed():
        logger.info("camoufox[geoip]: ok")
    else:
        logger.warning("camoufox[geoip] extra is not installed")

    database_path = geoip_database_path()
    if database_path:
        logger.info("GeoIP database: {}", database_path)
    else:
        logger.warning("GeoIP database not found; run `python download_geoip.py`")

    proxy_urls = load_proxy_urls(
        primary=os.environ.get("PARSER_PROXY", ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    if proxy_urls:
        logger.info("Proxy entries configured: {}", len(proxy_urls))
        for index, proxy_url in enumerate(proxy_urls, start=1):
            logger.info("Checking proxy {}/{}", index, len(proxy_urls))
            ok = _check_proxy(proxy_url) and ok
    else:
        logger.info("PARSER_PROXY/PARSER_PROXIES: not set")

    if ok:
        logger.info("Environment check passed")
        return 0
    logger.error("Environment check failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
