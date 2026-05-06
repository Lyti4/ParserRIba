import os
import asyncio
from typing import Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False
    logger.warning("⚠️ Camoufox не установлен")

class CamoufoxParser:
    """Базовый парсер на основе Camoufox"""
    
    def __init__(self, headless: bool = True, geoip_path: Optional[str] = None):
        if not CAMOUFOX_AVAILABLE:
            raise ImportError("Camoufox not installed. Run: pip install camoufox")
        
        self.headless = headless
        self.geoip_path = geoip_path
        self.browser = None
        self.page = None

    async def start_browser(self) -> Any:
        """Запускает браузер и возвращает страницу"""
        try:
            logger.info("🦊 Запуск Camoufox...")
            
            is_windows = os.name == 'nt'
            
            # Настройка headless режима
            if self.headless:
                headless_mode = True if is_windows else "virtual"
                mode_name = "Windows Headless" if is_windows else "Linux Virtual"
            else:
                headless_mode = False
                mode_name = "Visible Window"
            
            logger.info(f"🖥️ Режим: {mode_name}")
            
            launch_args = {
                "headless": headless_mode,
                "block_images": True,
                "timeout": 30000,
            }
            
            if self.geoip_path and os.path.exists(self.geoip_path):
                launch_args["geoip"] = self.geoip_path
                logger.info(f"🌍 GeoIP подключен: {self.geoip_path}")
            
            # Запуск браузера
            self.browser = await AsyncCamoufox(**launch_args).__aenter__()
            
            # Создание страницы
            self.page = await self.browser.new_page()
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            
            logger.info("✅ Браузер готов к работе")
            return self.page
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Camoufox: {e}")
            raise

    async def close_browser(self):
        """Закрытие браузера"""
        if self.browser:
            try:
                await self.browser.__aexit__(None, None, None)
                logger.info("🔒 Браузер закрыт")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка закрытия: {e}")
