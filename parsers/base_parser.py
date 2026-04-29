"""
Базовый класс для парсеров с использованием Playwright и curl-cffi
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
from loguru import logger
from curl_cffi import requests as curl_requests
from fake_useragent import UserAgent

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright не установлен. Установите: pip install playwright")

from models.product import FishProduct


class BaseParser(ABC):
    """Базовый класс для всех парсеров магазинов"""
    
    def __init__(self, store_name: str, base_url: str, headless: bool = True):
        self.store_name = store_name
        self.base_url = base_url
        self.headless = headless  # Если False, браузер будет видимым
        self.session = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    @abstractmethod
    async def parse_fish_products(self) -> List[FishProduct]:
        """
        Парсинг рыбных товаров из магазина
        
        Returns:
            Список объектов FishProduct
        """
        pass
    
    @abstractmethod
    def get_category_urls(self) -> List[str]:
        """
        Получение URL категорий с рыбными товарами
        
        Returns:
            Список URL
        """
        pass
    
    def _get_headers(self) -> dict:
        """Получение заголовков браузера"""
        ua = UserAgent()
        return {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Загрузка страницы с использованием curl-cffi для обхода блокировок
        
        Args:
            url: URL страницы
            
        Returns:
            HTML содержимое или None при ошибке
        """
        try:
            headers = self._get_headers()
            
            # Используем impersonate для эмуляции реального браузера
            response = curl_requests.get(
                url,
                headers=headers,
                timeout=30,
                impersonate='chrome120',
                allow_redirects=True,
                verify=False
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Ошибка загрузки {url}: статус {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None
    
    async def start_browser(self):
        """Запуск браузера Playwright"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright не доступен. Установите: pip install playwright && playwright install chromium")
            return False
            
        if self.browser is None:
            try:
                pw = await async_playwright().start()
                self.browser = await pw.chromium.launch(headless=self.headless)
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                self.page = await self.context.new_page()
                logger.info(f"🌐 Браузер запущен (режим: {'скрытый' if self.headless else 'ВИДИМЫЙ'})")
                return True
            except Exception as e:
                logger.error(f"Ошибка запуска браузера: {e}")
                return False
        return True
    
    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        Загрузка страницы через Playwright с полным рендерингом JS
        
        Args:
            url: URL страницы
            wait_selector: CSS селектор для ожидания (опционально)
            
        Returns:
            HTML содержимое или None
        """
        if not await self.start_browser():
            return None
            
        try:
            assert self.page is not None
            logger.info(f"🔍 Переход на страницу: {url}")
            
            # Переход на страницу с ожиданием полной загрузки
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Дополнительная пауза для рендеринга
            await asyncio.sleep(2)
            
            # Ожидание конкретного элемента если указан
            if wait_selector:
                try:
                    await self.page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    logger.warning(f"Элемент {wait_selector} не найден, продолжаем без него")
            
            # Получаем HTML
            html = await self.page.content()
            return html
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url} через Playwright: {e}")
            return None
    
    async def screenshot(self, path: str):
        """Сделать скриншот текущей страницы"""
        if self.page:
            try:
                await self.page.screenshot(path=path)
                logger.info(f"📸 Скриншот сохранен: {path}")
            except Exception as e:
                logger.error(f"Ошибка создания скриншота: {e}")
    
    async def fetch_page_js(self, url: str) -> Optional[str]:
        """
        Загрузка страницы с JavaScript рендерингом (использует Playwright если доступен)
        
        Args:
            url: URL страницы
            
        Returns:
            HTML содержимое или None при ошибке
        """
        # Пробуем через Playwright
        if PLAYWRIGHT_AVAILABLE:
            return await self.fetch_page_playwright(url)
        else:
            # Фоллбэк на старый метод (если вдруг нужен)
            logger.warning("Playwright недоступен, используем fallback метод")
            return await self.fetch_page(url)
    
    async def fetch_page_with_js(self, url: str) -> Optional[str]:
        """Алиас для fetch_page_js"""
        return await self.fetch_page_js(url)
    
    def clean_price(self, price_str: str) -> Optional[float]:
        """
        Очистка строки цены и преобразование в float
        
        Args:
            price_str: Строка с ценой (например, "123 ₽", "1 234 руб.")
            
        Returns:
            Цена в виде float или None
        """
        if not price_str:
            return None
        
        try:
            cleaned = ''.join(filter(lambda x: x.isdigit() or x in ',.', price_str.strip()))
            cleaned = cleaned.replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            logger.warning(f"Не удалось распарсить цену: {price_str}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Очистка текста от лишних пробелов"""
        if not text:
            return ""
        return ' '.join(text.split()).strip()
    
    async def close(self):
        """Закрытие браузера и сессии"""
        if self.browser:
            try:
                await self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
                logger.info("🚫 Браузер закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия браузера: {e}")
        
        if self.session:
            self.session.close()
    
    async def delay(self, seconds: int = 2):
        """Задержка между запросами"""
        await asyncio.sleep(seconds)
