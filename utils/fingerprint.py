"""Camoufox fingerprint profile helpers.

Camoufox already generates BrowserForge fingerprints internally. This module
keeps ParserRIba's fingerprint settings explicit, configurable and reportable
without building an inconsistent custom user agent by hand.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from browserforge.fingerprints import Screen


DEFAULT_WINDOWS_SCREEN = {
    "min_width": 1366,
    "max_width": 1920,
    "min_height": 768,
    "max_height": 1080,
}


@dataclass(frozen=True)
class CamoufoxFingerprintProfile:
    """Serializable constraints passed to Camoufox fingerprint generation."""

    os: str | list[str] = "windows"
    locale: str | list[str] = "ru-RU"
    humanize: bool | float = 1.5
    block_images: bool = True
    block_webrtc: bool = True
    block_webgl: bool = False
    screen_min_width: int | None = DEFAULT_WINDOWS_SCREEN["min_width"]
    screen_max_width: int | None = DEFAULT_WINDOWS_SCREEN["max_width"]
    screen_min_height: int | None = DEFAULT_WINDOWS_SCREEN["min_height"]
    screen_max_height: int | None = DEFAULT_WINDOWS_SCREEN["max_height"]
    window_width: int | None = None
    window_height: int | None = None
    fingerprint_preset: bool | None = None
    webgl_vendor: str | None = None
    webgl_renderer: str | None = None

    def screen(self) -> Screen | None:
        """Return BrowserForge screen constraints for Camoufox."""
        values = (
            self.screen_min_width,
            self.screen_max_width,
            self.screen_min_height,
            self.screen_max_height,
        )
        if all(value is None for value in values):
            return None
        return Screen(
            min_width=self.screen_min_width,
            max_width=self.screen_max_width,
            min_height=self.screen_min_height,
            max_height=self.screen_max_height,
        )

    def window(self) -> tuple[int, int] | None:
        """Return fixed browser window size, if configured."""
        if self.window_width and self.window_height:
            return (self.window_width, self.window_height)
        return None

    def webgl_config(self) -> tuple[str, str] | None:
        """Return fixed WebGL vendor/renderer pair, if configured."""
        if self.webgl_vendor and self.webgl_renderer:
            return (self.webgl_vendor, self.webgl_renderer)
        return None

    def launch_options(self) -> dict[str, Any]:
        """Return Camoufox launch options controlled by this profile."""
        options: dict[str, Any] = {
            "os": self.os,
            "locale": self.locale,
            "humanize": self.humanize,
            "block_images": self.block_images,
            "block_webrtc": self.block_webrtc,
            "block_webgl": self.block_webgl,
        }
        screen = self.screen()
        if screen:
            options["screen"] = screen
        window = self.window()
        if window:
            options["window"] = window
        webgl_config = self.webgl_config()
        if webgl_config:
            options["webgl_config"] = webgl_config
        if self.fingerprint_preset is not None:
            options["fingerprint_preset"] = self.fingerprint_preset
        return options

    def summary(self) -> dict[str, Any]:
        """Return a report-safe summary of the fingerprint settings."""
        data = asdict(self)
        data["engine"] = (
            "camoufox-preset" if self.fingerprint_preset else "camoufox-browserforge"
        )
        return data


def build_fingerprint_profile(
    *,
    os_value: str | list[str] | None = None,
    locale: str | list[str] | None = None,
    humanize: bool | float | None = None,
    block_images: bool | None = None,
    block_webrtc: bool | None = None,
    block_webgl: bool | None = None,
) -> CamoufoxFingerprintProfile:
    """Build a fingerprint profile from defaults, environment and overrides."""
    return CamoufoxFingerprintProfile(
        os=_coalesce(os_value, _env_list_or_string("CAMOUFOX_FINGERPRINT_OS"), "windows"),
        locale=_coalesce(locale, _env_list_or_string("CAMOUFOX_LOCALE"), "ru-RU"),
        humanize=_coalesce(humanize, _env_bool_float("CAMOUFOX_HUMANIZE"), 1.5),
        block_images=_coalesce(block_images, _env_bool("CAMOUFOX_BLOCK_IMAGES"), True),
        block_webrtc=_coalesce(block_webrtc, _env_bool("CAMOUFOX_BLOCK_WEBRTC"), True),
        block_webgl=_coalesce(block_webgl, _env_bool("CAMOUFOX_BLOCK_WEBGL"), False),
        screen_min_width=_env_int("CAMOUFOX_SCREEN_MIN_WIDTH", DEFAULT_WINDOWS_SCREEN["min_width"]),
        screen_max_width=_env_int("CAMOUFOX_SCREEN_MAX_WIDTH", DEFAULT_WINDOWS_SCREEN["max_width"]),
        screen_min_height=_env_int("CAMOUFOX_SCREEN_MIN_HEIGHT", DEFAULT_WINDOWS_SCREEN["min_height"]),
        screen_max_height=_env_int("CAMOUFOX_SCREEN_MAX_HEIGHT", DEFAULT_WINDOWS_SCREEN["max_height"]),
        window_width=_env_int("CAMOUFOX_WINDOW_WIDTH"),
        window_height=_env_int("CAMOUFOX_WINDOW_HEIGHT"),
        fingerprint_preset=_env_bool("CAMOUFOX_FINGERPRINT_PRESET"),
        webgl_vendor=_env_str("CAMOUFOX_WEBGL_VENDOR"),
        webgl_renderer=_env_str("CAMOUFOX_WEBGL_RENDERER"),
    )


def fingerprint_summary_from_options(options: dict[str, Any]) -> dict[str, Any]:
    """Build a compact report summary from Camoufox launch options."""
    screen = options.get("screen")
    screen_summary = {}
    if screen:
        screen_summary = {
            "min_width": getattr(screen, "min_width", None),
            "max_width": getattr(screen, "max_width", None),
            "min_height": getattr(screen, "min_height", None),
            "max_height": getattr(screen, "max_height", None),
        }
    return {
        "engine": "camoufox-preset" if options.get("fingerprint_preset") else "camoufox-browserforge",
        "os": options.get("os", ""),
        "locale": options.get("locale", ""),
        "humanize": options.get("humanize", False),
        "block_images": options.get("block_images", False),
        "block_webrtc": options.get("block_webrtc", False),
        "block_webgl": options.get("block_webgl", False),
        "screen": screen_summary,
        "window": options.get("window", ""),
        "webgl_configured": bool(options.get("webgl_config")),
    }


def get_camoufox_config(fingerprint: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible helper returning Camoufox profile launch options."""
    _ = fingerprint
    profile = build_fingerprint_profile(
        os_value=kwargs.get("os") or kwargs.get("fingerprint_os"),
        locale=kwargs.get("locale"),
        humanize=kwargs.get("humanize"),
        block_images=kwargs.get("block_images"),
        block_webrtc=kwargs.get("block_webrtc"),
        block_webgl=kwargs.get("block_webgl"),
    )
    return profile.launch_options()


def create_fingerprint_for_region(region: str = "RU", timezone: str = "Europe/Moscow") -> dict[str, Any]:
    """Return a reportable regional fingerprint intent without custom spoof data."""
    return {
        "region": region,
        "timezone": timezone,
        "profile": build_fingerprint_profile().summary(),
    }


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _env_str(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _env_int(name: str, default: int | None = None) -> int | None:
    value = _env_str(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str) -> bool | None:
    value = _env_str(name)
    if value is None:
        return None
    return value.lower() in {"1", "true", "yes", "on"}


def _env_bool_float(name: str) -> bool | float | None:
    value = _env_str(name)
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    try:
        return float(value)
    except ValueError:
        return None


def _env_list_or_string(name: str) -> str | list[str] | None:
    value = _env_str(name)
    if value is None:
        return None
    parts = [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
    if len(parts) > 1:
        return parts
    return parts[0] if parts else None
