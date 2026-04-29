"""
Парсер с использованием Playwright для обхода сложных блокировок
Запускает реальный браузер Chromium и собирает данные как настоящий пользователь
"""
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from loguru import logger
import asyncio

from models.product import FishProduct
from parsers.base_parser import BaseParser


class PlaywrightParser(BaseParser):
    """Парсер на базе Playwright - запускает настоящий браузер"""
    
    def __init__(self, store_name: str, base_url: str):
        super().__init__(store_name, base_url)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def start_browser(self, headless: bool = None):
        """
        Запуск браузера Chromium
        
        Args:
            headless: Запускать ли в фоновом режиме (без видимого окна).
                     Если None, используется значение из main.py (VISUAL_MODE)
        """
        # Импортируем VISUAL_MODE из main при необходимости
        if headless is None:
            try:
                from main import VISUAL_MODE
                headless = not VISUAL_MODE
            except ImportError:
                headless = True  # По умолчанию скрытый режим
        
        try:
            playwright = await async_playwright().start()
            
            # Запускаем браузер с настройками для обхода детекции
            self.browser = await playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                ]
            )
            
            # Создаём контекст с эмуляцией реального пользователя
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                permissions=['geolocation'],
                geolocation={'latitude': 55.7558, 'longitude': 37.6173}  # Москва
            )
            
            # Добавляем скрипт для скрытия автоматизации
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
            """)
            
            self.page = await self.context.new_page()
            logger.info(f"Браузер запущен (headless={headless})")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске браузера: {e}")
            raise
    
    async def fetch_page_playwright(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """
        Загрузка страницы через Playwright с полным рендерингом JavaScript
        
        Args:
            url: URL страницы
            wait_for_selector: CSS селектор элемента, которого нужно дождаться
            timeout: Таймаут в миллисекундах
            
        Returns:
            HTML содержимое или None при ошибке
        """
        if not self.page:
            await self.start_browser()
        
        try:
            # Переходим на страницу
            await self.page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # Ждём появления нужного элемента если указан
            if wait_for_selector:
                await self.page.wait_for_selector(wait_for_selector, timeout=timeout)
            
            # Дополнительная задержка для полного рендеринга
            await asyncio.sleep(2)
            
            # Получаем HTML
            html = await self.page.content()
            return html
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url} через Playwright: {e}")
            return None
    
    async def extract_with_playwright(self, url: str, selector: str, attribute: Optional[str] = None) -> Optional[str]:
        """
        Извлечение данных со страницы с помощью Playwright
        
        Args:
            url: URL страницы
            selector: CSS селектор элемента
            attribute: Атрибут для извлечения (None для текста)
            
        Returns:
            Значение или None
        """
        if not self.page:
            await self.start_browser()
        
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            if attribute:
                value = await self.page.get_attribute(selector, attribute)
            else:
                value = await self.page.text_content(selector)
            
            return value.strip() if value else None
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных: {e}")
            return None
    
    async def screenshot(self, path: str):
        """
        Сделать скриншот страницы
        
        Args:
            path: Путь для сохранения скриншота
        """
        if self.page:
            await self.page.screenshot(path=path, full_page=True)
            logger.info(f"Скриншот сохранён: {path}")
    
    async def scroll_page(self):
        """Прокрутка страницы для загрузки ленивого контента"""
        if self.page:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
    
    async def close(self):
        """Закрытие браузера и очистка ресурсов"""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.page:
            self.page = None
        logger.info("Браузер закрыт")


# Пример использования
async def example_usage():
    """Пример использования Playwright парсера"""
    parser = PlaywrightParser("Test Store", "https://example.com")
    
    try:
        await parser.start_browser(headless=True)
        
        # Загружаем страницу
        html = await parser.fetch_page_playwright("https://example.com")
        if html:
            print(f"Страница загружена, длина HTML: {len(html)}")
        
        # Делаем скриншот
        await parser.screenshot("example_screenshot.png")
        
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
