"""
Базовый класс для парсеров с использованием Playwright и curl-cffi
С поддержкой stealth-режима для обхода блокировок
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
import random
from loguru import logger
from curl_cffi import requests as curl_requests
from fake_useragent import UserAgent

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright_stealth import stealth_async
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright или playwright-stealth не установлены. Установите: pip install playwright playwright-stealth")

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
        """Запуск браузера Playwright в stealth-режиме"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright не доступен. Установите: pip install playwright && playwright install chromium")
            return False
            
        if self.browser is None:
            try:
                pw = await async_playwright().start()
                
                # Запускаем браузер с дополнительными аргументами для маскировки
                args = [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
                
                self.browser = await pw.chromium.launch(
                    headless=self.headless,
                    args=args
                )
                
                # Создаем контекст с реалистичными параметрами
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    permissions=["geolocation"],
                    geolocation={"latitude": 55.7558, "longitude": 37.6173},  # Москва
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                    color_scheme="light",
                    extra_http_headers={
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
                    }
                )
                
                self.page = await self.context.new_page()
                
                # Применяем stealth-режим для скрытия признаков автоматизации
                await stealth_async(self.page)
                
                # Дополнительная защита от обнаружения
                await self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Маскировка плагинов
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // Маскировка языка
                    Object.defineProperty(navigator, 'language', {
                        get: () => 'ru-RU'
                    });
                    
                    // Маскировка количества ядер процессора
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8
                    });
                    
                    // Маскировка памяти
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8
                    });
                """)
                
                logger.info(f"🌐 Браузер запущен (режим: {'скрытый' if self.headless else 'ВИДИМЫЙ'})")
                logger.info("🛡️ Stealth-режим активирован")
                return True
            except Exception as e:
                logger.error(f"Ошибка запуска браузера: {e}")
                return False
        return True
    
    async def save_cookies(self, filename: str) -> bool:
        """Сохранение cookies в JSON файл"""
        if not self.context:
            logger.warning("Контекст браузера не создан, нельзя сохранить cookies")
            return False
        
        try:
            cookies = await self.context.cookies()
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"🍪 Cookies сохранены в файл: {filename}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения cookies: {e}")
            return False
    
    async def load_cookies(self, filename: str) -> bool:
        """Загрузка cookies из JSON файла"""
        if not self.context:
            logger.warning("Контекст браузера не создан, нельзя загрузить cookies")
            return False
        
        import os
        import json
        
        if not os.path.exists(filename):
            logger.info(f"📁 Файл cookies не найден: {filename}")
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            await self.context.add_cookies(cookies)
            logger.info(f"🍪 Cookies загружены из файла: {filename}")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки cookies: {e}")
            return False
    
    async def human_scroll(self, min_delay: float = 0.5, max_delay: float = 1.5):
        """Имитация человеческой прокрутки страницы"""
        if not self.page:
            return
        
        try:
            # Прокрутка вниз небольшими порциями
            scroll_height = await self.page.evaluate("document.documentElement.scrollHeight")
            current_scroll = 0
            step = random.randint(100, 300)
            
            while current_scroll < scroll_height:
                await self.page.evaluate(f"window.scrollBy(0, {step})")
                current_scroll += step
                await asyncio.sleep(random.uniform(min_delay, max_delay))
                
                # Проверяем, не достигли ли конца
                new_scroll_height = await self.page.evaluate("document.documentElement.scrollHeight")
                if new_scroll_height == scroll_height and current_scroll >= scroll_height - 100:
                    break
                scroll_height = new_scroll_height
                step = random.randint(100, 300)
            
            # Прокрутка обратно вверх
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
        except Exception as e:
            logger.warning(f"Ошибка при прокрутке: {e}")
    
    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        Загрузка страницы через Playwright с полным рендерингом JS и stealth-режимом
        
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
            
            # Случайная задержка перед переходом (имитация раздумий человека)
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Переход на страницу с ожиданием полной загрузки
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Дополнительная пауза для рендеринга и скриптов сайта
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Ожидание конкретного элемента если указан
            if wait_selector:
                try:
                    await self.page.wait_for_selector(wait_selector, timeout=10000)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception:
                    logger.warning(f"Элемент {wait_selector} не найден, продолжаем без него")
            
            # Имитация человеческой прокрутки для подгрузки контента
            await self.human_scroll()
            
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
