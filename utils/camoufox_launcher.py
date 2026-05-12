"""Single Camoufox launch configuration used by parsers and smoke tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from utils.geoip import prepare_geoip
from utils.proxy import mask_proxy_url, parse_proxy_url

DEFAULT_CAMOUFOX_PATH = Path(
    r"C:\CamoufoxBrowser\camoufox-135.0.1-beta.24-win.x86_64\camoufox.exe"
)
DEFAULT_FF_VERSION = 135


def configure_windows_console() -> None:
    """Use UTF-8 output in classic Windows terminals."""
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        return


def resolve_camoufox_executable() -> Path | None:
    """Return an existing local Camoufox executable, if configured."""
    env_path = os.environ.get("CAMOUFOX_BIN")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    if DEFAULT_CAMOUFOX_PATH.exists():
        os.environ["CAMOUFOX_BIN"] = str(DEFAULT_CAMOUFOX_PATH)
        os.environ["CAMOUFOX_SKIP_DOWNLOAD"] = "1"
        return DEFAULT_CAMOUFOX_PATH
    return None


def build_camoufox_options(
    *,
    headless: bool | str = True,
    proxy_url: str | None = None,
    geoip: bool = False,
    block_images: bool = True,
    block_webgl: bool = False,
    humanize: bool = True,
    locale: str = "ru-RU",
    timezone_id: str = "Europe/Moscow",
) -> dict[str, Any]:
    """Build AsyncCamoufox options in one place."""
    executable_path = resolve_camoufox_executable()
    geoip_enabled = prepare_geoip() if geoip else False
    options: dict[str, Any] = {
        "geoip": geoip_enabled,
        "humanize": humanize,
        "block_images": block_images,
        "block_webgl": block_webgl,
        "headless": normalize_headless(headless),
        "i_know_what_im_doing": True,
        "locale": locale,
        "timezone_id": timezone_id,
    }

    if executable_path:
        # ИЗМЕНЕНО: используем локальный Camoufox, чтобы не требовать `camoufox fetch`.
        options["executable_path"] = str(executable_path)
        options["ff_version"] = DEFAULT_FF_VERSION

    if proxy_url:
        parsed_proxy = parse_proxy_url(proxy_url)
        options["proxy"] = parsed_proxy.as_playwright()
        logger.info("Using proxy {}", mask_proxy_url(proxy_url))

    return options


def normalize_headless(headless: bool | str) -> bool | str:
    """Normalize headless mode for Windows and Linux."""
    if headless in (False, "false", "False", "0"):
        return False
    if headless in ("virtual",):
        return True if sys.platform == "win32" else "virtual"
    if headless in (True, "true", "True", "1", "auto"):
        return True if sys.platform == "win32" else "virtual"
    return headless
