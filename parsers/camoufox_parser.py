"""Camoufox-backed parser base class."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from loguru import logger

try:
    from camoufox.async_api import AsyncCamoufox

    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False

from parsers.base_parser import BaseParser
from utils.camoufox_launcher import build_camoufox_options


def get_short_path_windows(path: str) -> str:
    """Return a path usable by Camoufox on Windows."""
    return path


class CamoufoxParser(BaseParser):
    """Parser base that owns a Camoufox context manager."""

    def __init__(self, store_name: str, config: dict[str, Any] | None = None, **kwargs: Any):
        super().__init__(store_name=store_name, headless=kwargs.get("headless", True))
        self.shop_name = store_name
        self.config = config or {}
        self._camoufox_browser: Any | None = None
        self._camoufox_context: AsyncCamoufox | None = None
        logger.info("CamoufoxParser initialized for {}", store_name)

    async def start_browser(self, headless: bool | str = True, geoip: bool = False, **kwargs: Any) -> Any:
        """Start Camoufox and return the browser object."""
        if not CAMOUFOX_AVAILABLE:
            raise ImportError("Camoufox not installed.")

        if geoip:
            geoip_file = Path(__file__).parent.parent / "GeoLite2-City.mmdb"
            if geoip_file.exists():
                os.environ["GEOIP_PATH"] = get_short_path_windows(str(geoip_file))
                logger.info("GeoIP DB found: {}", os.environ["GEOIP_PATH"])
            else:
                logger.warning("GeoIP requested but GeoLite2-City.mmdb was not found")
                geoip = False

        browser_args = build_camoufox_options(
            headless=headless,
            proxy_url=kwargs.get("proxy_url"),
            geoip=geoip,
            block_images=kwargs.get("block_images", True),
            block_webgl=kwargs.get("block_webgl", False),
            humanize=kwargs.get("humanize", True),
            fingerprint_os=kwargs.get("fingerprint_os", "windows"),
        )

        try:
            self._camoufox_context = AsyncCamoufox(**browser_args)
            self._camoufox_browser = await self._camoufox_context.__aenter__()
            if not hasattr(self._camoufox_browser, "new_page"):
                raise RuntimeError("Invalid browser object returned from Camoufox")
            logger.info("Camoufox started successfully")
            return self._camoufox_browser
        except Exception:
            await self.close_browser()
            raise

    async def close_browser(self) -> None:
        """Close Camoufox via the owning context manager."""
        if self._camoufox_context:
            try:
                await self._camoufox_context.__aexit__(None, None, None)
            except Exception as exc:
                logger.warning("Error closing Camoufox context: {}", exc)
        self._camoufox_browser = None
        self._camoufox_context = None

    async def parse_category(self, category_url: str, category_name: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Open a category page through Camoufox.

        Concrete store parsers should override product extraction.
        """
        browser = await self.start_browser(
            headless=kwargs.get("headless", True),
            geoip=kwargs.get("geoip", False),
            proxy_url=kwargs.get("proxy_url"),
        )
        try:
            page = await browser.new_page()
            logger.info("Parsing category: {} at {}", category_name, category_url)
            await page.goto(category_url, wait_until="domcontentloaded")
            return []
        finally:
            await self.close_browser()
