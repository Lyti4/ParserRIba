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
        self._camoufox_context = None
        # На Windows virtual display не поддерживается - используем обычный headless или оконный режим
        is_windows = os.name == 'nt'
        headless_mode = kwargs.get('headless', True)
        
        # Для Windows: True = обычный headless, False/None = оконный режим
        # Для Linux: True = virtual display, False/None = оконный режим
        if is_windows:
            session_headless = True if headless_mode else False
        else:
            session_headless = "virtual" if headless_mode else False
            
        self._session_manager = SessionManager(
            block_images=True,
            block_webgl=False,
            humanize=True,
            headless=session_headless
        )
        logger.info(f"CamoufoxParser initialized for {store_name} (Windows={is_windows}, headless={session_headless})")

    async def start_browser(self, headless: bool = True, geoip: bool = False, **kwargs):
        """Запускает браузер и возвращает страницу (page)."""
        if not CAMOUFOX_AVAILABLE:
            raise ImportError("Camoufox not installed.")
        
        logger.info(f"Starting Camoufox (geoip={geoip}, headless={headless})...")
        
        # Формируем аргументы для запуска браузера
        browser_args = {
            "humanize": True,
            "block_images": True,
            "block_webgl": False,
        }
        
        # Обработка headless режима - Windows не поддерживает virtual display
        is_windows = os.name == 'nt'
        if headless:
            if is_windows:
                browser_args["headless"] = True  # Обычный headless для Windows
            else:
                browser_args["headless"] = "virtual"  # Virtual display для Linux
        else:
            browser_args["headless"] = False  # Оконный режим

        if geoip:
            geoip_file = Path(__file__).parent.parent / "GeoLite2-City.mmdb"
            if geoip_file.exists():
                short_path = get_short_path_windows(str(geoip_file))
                os.environ["GEOIP_PATH"] = short_path
                logger.info(f"GeoIP DB found: {short_path}")
                browser_args["geoip"] = True
            else:
                logger.warning("GeoIP requested but file not found, disabling geoip")
                browser_args["geoip"] = False
        else:
            browser_args["geoip"] = False

        try:
            # Запускаем браузер через контекстный менеджер
            self._camoufox_context = AsyncCamoufox(**browser_args)
            self._camoufox_browser = await self._camoufox_context.__aenter__()
            
            # Сразу создаем страницу и возвращаем её
            page = await self._camoufox_browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            logger.info(f"Camoufox started successfully, page created (type: {type(page).__name__})")
            
            return page
            
        except OSError as e:
            if "No space left on device" in str(e) or e.errno == 28:
                logger.error("❌ Недостаточно места на диске для загрузки Camoufox (~713MB требуется)")
                logger.error("   Освободите место или используйте Playwright вместо Camoufox")
                raise RuntimeError("Insufficient disk space for Camoufox") from e
            raise
        except Exception as e:
            logger.error(f"Error starting Camoufox: {e}")
            # Очищаем контекст при ошибке
            await self.close_browser()
            raise

    async def close_browser(self):
        if self._camoufox_browser:
            try:
                await self._camoufox_browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            self._camoufox_browser = None
            
        # Закрываем контекст, если он существует
        if hasattr(self, '_camoufox_context') and self._camoufox_context:
            try:
                await self._camoufox_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
            self._camoufox_context = None

    async def parse_category(self, category_url: str, category_name: str, **kwargs) -> List[Dict]:
        # Отключаем geoip по умолчанию для избежания ошибок с путями к файлам
        # headless берется из kwargs или используется True по умолчанию
        page = await self.start_browser(headless=kwargs.get('headless', True), geoip=False)
        try:
            logger.info(f"Parsing category: {category_name} at {category_url}")
            await page.goto(category_url, wait_until="domcontentloaded")
            # Здесь будет логика парсинга
            return []
        finally:
            await self.close_browser()
