import asyncio
import random
import logging
from typing import Optional, List, Dict, Any
from curl_cffi import requests as curl_requests
from loguru import logger
from functools import wraps

# Декоратор для повторных попыток
def retry_on_failure(max_attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Попытка {attempt+1}/{max_attempts} не удалась: {e}. Ждём {delay}с...")
                    await asyncio.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

class BaseParser:
    def __init__(self, store_name: str, base_url: str = "", headless: bool = True):
        self.store_name = store_name
        self.base_url = base_url
        self.headless = headless
        self.session = curl_requests.Session()
        self.headers = self._get_headers()
        
        # Playwright атрибуты (ленивая инициализация)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _get_headers(self) -> dict:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }

    async def start_browser(self):
        """Запуск браузера Playwright"""
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import stealth_async
            
            logger.info(f"🌐 Запуск браузера ({'невидимый' if self.headless else 'видимый'})...")
            
            self._playwright = await async_playwright().start()
            
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
            
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=args
            )
            
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            self._page = await self._context.new_page()
            
            # Применение stealth
            await stealth_async(self._page)
            
            # Маскировка webdriver
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
            """)
            
            logger.info("✅ Браузер запущен успешно")
            
        except ImportError:
            logger.warning("⚠️ Playwright не установлен, используем curl-cffi")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска браузера: {e}")
            raise

    async def close_browser(self):
        """Закрытие браузера"""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("🛑 Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")

    async def close(self):
        """Алиас для close_browser"""
        await self.close_browser()

    @retry_on_failure(max_attempts=3, delay=2)
    async def fetch_page(self, url: str, use_impersonate: str = 'chrome124') -> Optional[str]:
        """Загрузка страницы с улучшенной маскировкой"""
        try:
            headers = self._get_headers()
            # Динамический выбор профиля
            if '5ka.ru' in url:
                use_impersonate = 'chrome124'
            elif 'magnit.ru' in url:
                use_impersonate = 'chrome120'
            
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=45,
                impersonate=use_impersonate,
                allow_redirects=True, 
                verify=False # Игнорируем SSL ошибки для тестов
            )
            
            if response.status_code == 403:
                logger.warning(f"⚠️ Защита (403) на {url}")
                return None
            if response.status_code == 401:
                headers['X-Region'] = '77'
                response = self.session.get(url, headers=headers, timeout=30, impersonate=use_impersonate, verify=False)
                
            return response.text if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None

    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """Загрузка через Playwright (для JS сайтов)"""
        try:
            if not self._page:
                await self.start_browser()
            
            logger.info(f"🔗 Запрос к {url} через Playwright...")
            
            # Случайная задержка перед запросом
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            if wait_selector:
                await self._page.wait_for_selector(wait_selector, timeout=timeout)
            
            # Дополнительная задержка после загрузки
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            content = await self._page.content()
            logger.info(f"✅ Страница загружена успешно")
            return content
            
        except Exception as e:
            logger.error(f"❌ Ошибка Playwright запроса: {e}")
            # Фоллбэк на curl-cffi
            return await self.fetch_page(url)

    def parse_product(self, html: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Метод parse_product должен быть реализован в наследнике")

    async def delay(self, seconds: float):
        """Асинхронная задержка"""
        await asyncio.sleep(seconds)

    def clean_text(self, text: str) -> str:
        """Очистка текста"""
        if not text:
            return ""
        return " ".join(text.split()).strip()

    def clean_price(self, price_str: str) -> int:
        """Очистка цены"""
        if not price_str:
            return 0
        import re
        numbers = re.findall(r'\d+', price_str.replace(' ', '').replace(',', '.'))
        if numbers:
            # Берем первое найденное число (основная цена)
            return int(numbers[0])
        return 0
