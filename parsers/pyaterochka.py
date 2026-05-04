"""
Парсер для магазина "Пятерочка" (5post.ru / x5.ru)
Использует BaseParser, Knowledge Base и Strategies.
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page, BrowserContext
from pydantic import BaseModel
from loguru import logger

from .base import BaseParser
from models.schemas import ParseResult, Product, ProductPrice, CategoryInfo


class PyaterochkaProduct(BaseModel):
    """Модель продукта для Пятерочки (расширенная)"""
    name: str
    price: float
    old_price: Optional[float] = None
    unit_price: Optional[str] = None  # Цена за кг/л
    weight: Optional[str] = None
    image_url: Optional[str] = None
    link: str
    discount: Optional[int] = None  # Процент скидки
    stock_status: str = "in_stock"  # in_stock, out_of_stock, low_stock


class PyaterochkaParser(BaseParser):
    """
    Специфичный парсер для Пятерочки.
    
    Особенности:
    - Использует data-атрибуты (data-naive-props и др.)
    - Требует скроллинга для подгрузки товаров
    - Региональность через X-Region-Id (настраивается в KB)
    """

    def __init__(self, config: Optional[dict] = None, shop_name: str = "pyaterochka", region: Optional[str] = None, **kwargs):
        super().__init__(shop_name, region)
        
        # Сохраняем конфиг для дальнейшего использования
        self.config_dict = config or {}
        
        # Playwright атрибуты
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        
        logger.info(f"PyaterochkaParser инициализирован для региона {region or 'default'}")

    async def start_browser(self):
        """Запуск браузера Playwright"""
        try:
            from playwright.async_api import async_playwright
            
            logger.info("🌐 Запуск браузера для Пятерочки...")
            
            self._playwright = await async_playwright().start()
            
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
            ]
            
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=args
            )
            
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="ru-RU",
                timezone_id="Europe/Moscow"
            )
            
            self._page = await self._context.new_page()
            
            # Применение stealth с использованием нового API
            try:
                from playwright_stealth import stealth
                await stealth(self._page)
            except ImportError:
                logger.warning("⚠️ playwright_stealth не установлен, применяем базовую маскировку")
            
            # Маскировка webdriver - расширенная версия
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
                
                // Маскировка плагинов
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Маскировка языков
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
            """)
            
            # Установка дополнительных заголовков
            await self._context.set_extra_http_headers({
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            })
            
            logger.info("✅ Браузер запущен успешно")
            
        except ImportError as e:
            logger.warning(f"⚠️ Playwright не установлен: {e}")
            raise
        except Exception as e:
            error_msg = str(e)
            if "Executable doesn't exist" in error_msg or "ENOSPC" in error_msg:
                logger.error("❌ Не удалось запустить браузер: недостаточно места на диске или браузер не установлен.")
                logger.error("💡 Попробуйте освободить место или используйте curl-cffi вместо Playwright.")
            else:
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

    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None, timeout: int = 30000) -> str:
        """Загрузка через Playwright (для JS сайтов)"""
        import random
        
        try:
            if not self._page:
                await self.start_browser()
            
            logger.info(f"🔗 Запрос к {url} через Playwright...")
            
            # Случайная задержка перед запросом
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Ждем появления карточек товаров перед продолжением
            try:
                await self._page.wait_for_selector('div[data-testid="product-card"]', timeout=10000)
            except:
                pass  # Игнорируем если не найдено, продолжаем
            
            # Дополнительная задержка для полной загрузки контента
            await asyncio.sleep(3)
            
            if wait_selector:
                await self._page.wait_for_selector(wait_selector, timeout=timeout)
            
            # Скроллинг для загрузки lazy-load контента
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            await self._page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            content = await self._page.content()
            logger.info(f"✅ Страница загружена успешно")
            return content
            
        except Exception as e:
            error_msg = str(e)
            if "Executable doesn't exist" in error_msg or "ENOSPC" in error_msg:
                logger.error("❌ Ошибка Playwright: недостаточно места на диске или браузер не установлен.")
                logger.error("💡 Попробуйте освободить место или использовать curl-cffi вместо Playwright.")
            else:
                logger.error(f"❌ Ошибка Playwright запроса: {e}")
            raise

    async def _init_strategies(self):
        """Инициализация стратегий после создания страницы"""
        # Стратегии больше не используются, скроллинг выполняется в fetch_page_playwright
        pass

    async def _fetch_page(self, url: str, page: int) -> str:
        """
        Получение HTML страницы.
        Реализация абстрактного метода из BaseParser.
        """
        if not hasattr(self, 'config') or not self.config:
            html = await self.fetch_page_playwright(url)
        elif getattr(self.config, 'use_playwright', True):
            html = await self.fetch_page_playwright(url)
        else:
            html = await self.fetch_page(url)
        
        if not html:
            raise Exception(f"Не удалось загрузить страницу {url}")
        
        return html

    async def _parse_products(self, html: str, category_url: str) -> List[Product]:
        """
        Парсинг товаров из HTML.
        Использует селекторы из Knowledge Base.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'lxml')
        products = []
        
        # Получаем селекторы из KB
        card_selector = self._extract_selector("product_card")
        if not card_selector:
            logger.warning("Селектор product_card не найден в KB")
            return products
        
        cards = soup.select(card_selector)
        logger.info(f"Найдено {len(cards)} карточек товаров")
        
        for card in cards:
            try:
                # Извлечение данных с использованием селекторов из KB
                name_sel = self._extract_selector("product_name")
                price_sel = self._extract_selector("price_current")
                old_price_sel = self._extract_selector("price_old")
                weight_sel = self._extract_selector("weight_volume")
                link_sel = self._extract_selector("product_link")
                image_sel = self._extract_selector("image_url")
                
                name = card.select_one(name_sel).get_text(strip=True) if name_sel and card.select_one(name_sel) else None
                price_text = card.select_one(price_sel).get_text(strip=True) if price_sel and card.select_one(price_sel) else "0"
                
                # Очистка цены
                price_value = float(''.join(c for c in price_text.replace(',', '.') if c.isdigit() or c == '.')) if price_text else 0.0
                
                old_price = None
                if old_price_sel:
                    old_price_el = card.select_one(old_price_sel)
                    if old_price_el:
                        old_price_text = old_price_el.get_text(strip=True)
                        old_price = float(''.join(c for c in old_price_text.replace(',', '.') if c.isdigit() or c == '.'))
                
                weight = card.select_one(weight_sel).get_text(strip=True) if weight_sel and card.select_one(weight_sel) else None
                
                # Ссылка
                link = None
                if link_sel:
                    link_el = card.select_one(link_sel)
                    if link_el and link_el.has_attr('href'):
                        link = link_el['href']
                        if not link.startswith('http'):
                            link = self.kb.base_url + link
                
                # Картинка
                image_url = None
                if image_sel:
                    img_el = card.select_one(image_sel)
                    if img_el:
                        image_url = img_el.get('src') or img_el.get('data-src')
                        if image_url and image_url.startswith('//'):
                            image_url = 'https:' + image_url
                
                if name and price_value > 0:
                    product = Product(
                        name=name,
                        price=ProductPrice(current=price_value, old=old_price),
                        dimensions=None,
                        image_url=image_url,
                        product_link=link or category_url,
                        category="Рыба и морепродукты",
                        in_stock=True,
                        raw_data={"weight": weight}
                    )
                    products.append(product)
                    
            except Exception as e:
                logger.warning(f"Ошибка при парсинге карточки: {e}")
                continue
        
        return products

    async def _has_next_page(self, html: str, page: int) -> bool:
        """Проверка наличия следующей страницы."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        next_selector = self._extract_selector("pagination_next")
        if next_selector:
            return soup.select_one(next_selector) is not None
        
        return False

    async def _get_next_page_url(self, html: str, category_url: str, page: int) -> Optional[str]:
        """Получение URL следующей страницы."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        next_selector = self._extract_selector("pagination_next")
        if next_selector:
            next_el = soup.select_one(next_selector)
            if next_el and next_el.has_attr('href'):
                next_url = next_el['href']
                if not next_url.startswith('http'):
                    next_url = self.kb.base_url + next_url
                return next_url
        
        return None
