"""Single Camoufox launch configuration used by parsers and smoke tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from utils.fingerprint import build_fingerprint_profile
from utils.geoip import prepare_geoip
from utils.proxy import mask_proxy_url, parse_proxy_url
from utils.catalog_tree_discovery.camoufox_runtime_profile import (
    CamoufoxResearchRuntimeProfile,
)

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
    block_images: bool | None = None,
    block_webrtc: bool | None = None,
    block_webgl: bool | None = None,
    humanize: bool | float | None = None,
    locale: str | None = None,
    fingerprint_os: str | list[str] | None = None,
    user_data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build AsyncCamoufox options in one place."""
    executable_path = resolve_camoufox_executable()
    geoip_enabled = prepare_geoip() if geoip else False
    profile = build_fingerprint_profile(
        os_value=fingerprint_os,
        locale=locale,
        humanize=humanize,
        block_images=block_images,
        block_webrtc=block_webrtc,
        block_webgl=block_webgl,
    )
    options: dict[str, Any] = {
        "geoip": geoip_enabled,
        "headless": normalize_headless(headless),
        "i_know_what_im_doing": True,
    }
    options.update(profile.launch_options())

    if executable_path:
        # ИЗМЕНЕНО: используем локальный Camoufox, чтобы не требовать `camoufox fetch`.
        options["executable_path"] = str(executable_path)
        options["ff_version"] = DEFAULT_FF_VERSION

    if proxy_url:
        parsed_proxy = parse_proxy_url(proxy_url)
        options["proxy"] = parsed_proxy.as_playwright()
        logger.info("Using proxy {}", mask_proxy_url(proxy_url))

    profile_dir = user_data_dir or os.environ.get("CAMOUFOX_USER_DATA_DIR", "")
    if profile_dir:
        path = Path(profile_dir)
        path.mkdir(parents=True, exist_ok=True)
        disable_session_restore_in_profile(path)
        if options.get("block_images") is False:
            allow_images_in_profile(path)
        options["persistent_context"] = True
        options["user_data_dir"] = str(path)
        logger.info("Using persistent Camoufox profile: {}", path)

    return options


def build_research_camoufox_options(
    *,
    headless: bool | str,
    proxy_url: str | None = None,
    geoip: bool = False,
    user_data_dir: str | Path | None = None,
    profile: CamoufoxResearchRuntimeProfile | None = None,
) -> dict[str, Any]:
    """Build one constrained Camoufox option set for serial research runs."""
    runtime = profile or CamoufoxResearchRuntimeProfile()
    return build_camoufox_options(
        headless=headless,
        proxy_url=proxy_url,
        geoip=geoip,
        block_images=runtime.block_images,
        block_webgl=runtime.block_webgl,
        humanize=runtime.humanize,
        locale=runtime.locale,
        fingerprint_os="windows",
        user_data_dir=user_data_dir if runtime.require_persistent_context else None,
    )


def allow_images_in_profile(profile_dir: Path) -> None:
    """Undo a persisted Firefox image block when visual captcha mode is used."""
    _upsert_profile_pref(profile_dir, "permissions.default.image", "1")
    logger.info("Persistent profile image loading enabled: {}", profile_dir / "prefs.js")


def disable_session_restore_in_profile(profile_dir: Path) -> None:
    """Keep a persistent profile from restoring stale windows in visual smoke mode."""
    prefs = {
        "browser.startup.page": "0",
        "browser.sessionstore.resume_from_crash": "false",
        "browser.sessionstore.max_resumed_crashes": "0",
    }
    for key, value in prefs.items():
        _upsert_profile_pref(profile_dir, key, value)


def _upsert_profile_pref(profile_dir: Path, key: str, value: str) -> None:
    """Set a Firefox preference in prefs.js without touching other profile data."""
    prefs_path = profile_dir / "prefs.js"
    new_line = f'user_pref("{key}", {value});'
    if not prefs_path.exists():
        prefs_path.write_text(new_line + "\n", encoding="utf-8")
        return
    content = prefs_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    pref_prefix = f'user_pref("{key}", '
    changed = False
    for index, line in enumerate(lines):
        if line.startswith(pref_prefix):
            if line != new_line:
                lines[index] = new_line
                changed = True
            break
    else:
        lines.append(new_line)
        changed = True
    if not changed:
        return
    prefs_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_headless(headless: bool | str) -> bool | str:
    """Normalize headless mode for Windows and Linux."""
    if headless in (False, "false", "False", "0"):
        return False
    if headless in ("virtual",):
        return True if sys.platform == "win32" else "virtual"
    if headless in (True, "true", "True", "1", "auto"):
        return True if sys.platform == "win32" else "virtual"
    return headless
