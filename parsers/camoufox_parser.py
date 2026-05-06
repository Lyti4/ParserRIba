import asyncio
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_short_path_windows(path: str) -> str:
    """Converts long path to short 8.3 format on Windows."""
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

class CamoufoxParser(BaseParser):
    def __init__(self, store_name: str, config: Dict[str, Any] = None, **kwargs):
        # Передаем store_name как shop_name, т.к. BaseParser ожидает shop_name
        super().__init__(shop_name=store_name, region=kwargs.get('region', '77'), headless=kwargs.get('headless', True))
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
        
        logger.info(f"Starting Camoufox (geoip={geoip}, headless={headless})...")
        
        # Формируем аргументы для запуска браузера
        browser_args = {
            "humanize": True,
            "block_images": True,
            "block_webgl": False,
        }
        
        # Обработка headless режима
        if headless:
            browser_args["headless"] = "virtual"
        else:
            browser_args["headless"] = False

        if geoip:
            geoip_file = Path(__file__).parent.parent / "GeoLite2-City.mmdb"
            if geoip_file.exists():
                short_path = get_short_path_windows(str(geoip_file))
                os.environ["GEOIP_PATH"] = short_path
                logger.info(f"GeoIP DB found: {short_path}")
                browser_args["geoip"] = True
            else:
                browser_args["geoip"] = False
        else:
            browser_args["geoip"] = False

        try:
            # Используем контекстный менеджер для правильного запуска браузера
            # AsyncCamoufox принимает параметры в __init__, а браузер запускается в __aenter__
            self._camoufox_context = AsyncCamoufox(**browser_args)
            self._camoufox_browser = await self._camoufox_context.__aenter__()
            logger.info("Camoufox started successfully")
            return self._camoufox_browser
        except OSError as e:
            if "No space left on device" in str(e) or e.errno == 28:
                logger.error("❌ Недостаточно места на диске для загрузки Camoufox (~713MB требуется)")
                logger.error("   Освободите место или используйте Playwright вместо Camoufox")
                raise RuntimeError("Insufficient disk space for Camoufox") from e
            raise
        except Exception as e:
            logger.error(f"Error starting Camoufox: {e}")
            raise

    async def close_browser(self):
        if self._camoufox_browser:
            await self._camoufox_browser.close()
            self._camoufox_browser = None
        # Также закрываем контекст, если он существует
        if hasattr(self, '_camoufox_context') and self._camoufox_context:
            try:
                await self._camoufox_context.__aexit__(None, None, None)
            except Exception:
                pass  # Игнорируем ошибки при закрытии контекста
            self._camoufox_context = None

    async def parse_category(self, category_url: str, category_name: str, **kwargs) -> List[Dict]:
        page = await self.start_browser(headless=kwargs.get('headless', True), geoip=True)
        try:
            await page.goto(category_url, wait_until="domcontentloaded")
            logger.info(f"Parsing category: {category_name}")
            return []
        finally:
            await self.close_browser()
