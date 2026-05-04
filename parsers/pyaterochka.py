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
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy


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

    def __init__(self, shop_name: str = "pyaterochka", region: Optional[str] = None):
        super().__init__(shop_name, region)
        
        # Инициализация стратегий, специфичных для Пятерочки
        self.strategies.append(ScrollStrategy(delay=1.0, steps=5))
        self.strategies.append(LazyLoadStrategy(timeout=5000))
        
        logger.info(f"PyaterochkaParser инициализирован для региона {region or 'default'}")

    async def _fetch_page(self, url: str, page: int) -> str:
        """
        Получение HTML страницы.
        Реализация абстрактного метода из BaseParser.
        """
        if self.config.use_playwright:
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
