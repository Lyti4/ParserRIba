import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, BrowserContext
import logging

logger = logging.getLogger(__name__)

def get_short_path_windows(path: str) -> str:
    """
    Converts long path to short 8.3 format on Windows.
    Solves encoding issues with Cyrillic characters in paths.
    """
    if os.name != 'nt':
        return path
    try:
        cmd = f'cmd /c for %I in ("{path}") do @echo %~sI'
        result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        return result if result else path
    except Exception:
        return path

try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False
    logger.warning("Camoufox not installed.")

from parsers.base_parser import BaseParser
from utils.session_manager import SessionManager
from utils.fingerprint import get_camoufox_config

class CamoufoxParser(BaseParser):
    def __init__(self, store_name: str, config: Dict[str, Any] = None, **kwargs):
        super().__init__(store_name, config, **kwargs)
        self._camoufox_browser = None
        self._session_manager = SessionManager(
            block_images=True,
            block_webgl=False,
            humanize=True,
            headless="virtual" if kwargs.get('headless', True) else None
        )
        logger.info(f"CamoufoxParser initialized for {store_name}")

    async def start_browser(self, headless: bool = True, geoip: bool = False, **kwargs):
        if not CAMOUFOX_AVAILABLE:
            raise ImportError("Camoufox not installed.")
        
        logger.info(f"Starting Camoufox (geoip={geoip})...")
        
        browser_args = {
            "headless": "virtual" if headless else False,
            "humanize": True,
            "block_images": True,
            "block_webgl": False,
        }

        if geoip:
            geoip_file = Path(__file__).parent.parent / "GeoLite2-City.mmdb"
            if geoip_file.exists():
                short_path = get_short_path_windows(str(geoip_file))
                os.environ["GEOIP_PATH"] = short_path
                logger.info(f"GeoIP DB found: {short_path}")
                browser_args["geoip"] = True
            else:
                logger.warning("GeoIP DB not found. Disabling geoip.")
                browser_args["geoip"] = False
        else:
            browser_args["geoip"] = False

        try:
            self._camoufox_browser = await AsyncCamoufox().new_page(**browser_args)
            logger.info("Camoufox started successfully")
            return self._camoufox_browser
        except Exception as e:
            logger.error(f"Error starting Camoufox: {e}")
            raise

    async def close_browser(self):
        if self._camoufox_browser:
            await self._camoufox_browser.close()
            self._camoufox_browser = None

    async def parse_category(self, category_url: str, category_name: str, **kwargs) -> List[Dict]:
        page = await self.start_browser(headless=kwargs.get('headless', True), geoip=True)
        try:
            await page.goto(category_url, wait_until="domcontentloaded")
            logger.info(f"Parsing category: {category_name}")
            return []
        finally:
            await self.close_browser()
