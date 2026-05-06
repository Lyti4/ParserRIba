"""
Парсер для магазина "Пятерочка" (5ka.ru)
Использует Camoufox (Firefox с улучшенной маскировкой) для обхода антибот-систем.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger

from models.schemas import ParseResult, Product, ProductPrice, CategoryInfo
from parsers.camoufox_parser import CamoufoxParser


class PyaterochkaParser(CamoufoxParser):
    """
    Специфичный парсер для Пятерочки на базе Camoufox.
    
    Особенности Пятерочки:
    - Использует data-атрибуты (data-testid="product-card" и др.)
    - Требует скроллинга для подгрузки товаров (lazy loading)
    - Региональность через X-Region-Id (настраивается в KB)
    - Умеренная защита, возможны 403 при частых запросах
    """

    def __init__(self, config: Optional[dict] = None, shop_name: str = "pyaterochka", region: str = "77", headless: bool = True):
        # Инициализируем базовый парсер Camoufox
        super().__init__(
            store_name=shop_name,
            base_url="https://5ka.ru",
            headless=headless,
            region=region
        )
        
        self.config_dict = config or {}
        self.region = region
        
        logger.info(f"🦊 PyaterochkaParser (Camoufox) инициализирован для региона {region}")

    async def parse_category(self, category_url: str) -> ParseResult:
        """
        Парсинг категории Пятерочки с поддержкой пагинации.
        
        Args:
            category_url: URL категории для парсинга
            
        Returns:
            ParseResult с товарами
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        all_products = []
        
        logger.info(f"🛒 Парсинг категории: {category_url}")
        
        try:
            # Загружаем первую страницу через Camoufox
            html = await self.fetch_page_camoufox(
                url=category_url,
                wait_for_selector='div[data-testid="product-card"]',
                scroll_down=True  # Включаем скроллинг для lazy loading
            )
            
            if not html:
                errors.append(f"Не удалось загрузить страницу {category_url}")
                return self._create_empty_result(category_url, errors, warnings, start_time)
            
            # Парсим товары с первой страницы
            products = await self._parse_products_from_html(html, category_url)
            all_products.extend(products)
            logger.info(f"✅ Найдено {len(products)} товаров на странице 1")
            
            # Определяем количество страниц
            total_pages = self._extract_total_pages(html)
            logger.info(f"📊 Всего страниц: {total_pages}")
            
            # Парсим остальные страницы (ограничиваем 10 для безопасности)
            for page_num in range(2, min(total_pages + 1, 11)):
                page_url = f"{category_url}?page={page_num}"
                logger.info(f"📖 Загрузка страницы {page_num}: {page_url}")
                
                html = await self.fetch_page_camoufox(
                    url=page_url,
                    wait_for_selector='div[data-testid="product-card"]',
                    scroll_down=True
                )
                
                if not html:
                    warnings.append(f"Не удалось загрузить страницу {page_num}")
                    continue
                
                page_products = await self._parse_products_from_html(html, category_url)
                all_products.extend(page_products)
                logger.info(f"✅ Добавлено {len(page_products)} товаров со страницы {page_num}")
                
                # Задержка между запросами
                await asyncio.sleep(2.0)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(name=self._extract_category_name(html), url=category_url),
                products=all_products,
                total_products=len(all_products),
                errors=errors,
                warnings=warnings,
                parse_duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга категории: {e}")
            errors.append(str(e))
            return self._create_empty_result(category_url, errors, warnings, start_time)

    async def _parse_products_from_html(self, html: str, category_url: str) -> List[Product]:
        """Парсинг товаров из HTML с использованием селекторов из KB."""
        soup = BeautifulSoup(html, 'lxml')
        products = []
        
        # Получаем селектор карточки товара из KB или используем дефолтный
        card_selector = self.get_selector("product_card") or 'div[data-testid="product-card"]'
        cards = soup.select(card_selector)
        
        logger.info(f"🔍 Найдено {len(cards)} карточек товаров")
        
        for i, card in enumerate(cards):
            try:
                product = self._parse_product_card(card, category_url, i)
                if product and product.name:
                    products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга карточки {i}: {e}")
                continue
        
        return products

    def _parse_product_card(self, card: Any, category_url: str, index: int) -> Optional[Product]:
        """Парсинг одной карточки товара."""
        try:
            # Название товара
            name_selector = self.get_selector("product_name") or 'div[data-testid="product-name"]'
            name_elem = card.select_one(name_selector)
            name = name_elem.get_text(strip=True) if name_elem else None
            
            if not name:
                return None
            
            # Цена (текущая)
            price_selector = self.get_selector("price_current") or 'span[data-testid="price-current"]'
            price_elem = card.select_one(price_selector)
            price_value = 0.0
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'(\d+[.,]?\d*)', price_text.replace(' ', ''))
                if price_match:
                    price_value = float(price_match.group(1).replace(',', '.'))
            
            # Старая цена (если есть скидка)
            old_price = None
            old_price_selector = self.get_selector("price_old") or 'span[data-testid="price-old"]'
            old_price_elem = card.select_one(old_price_selector)
            if old_price_elem:
                old_price_text = old_price_elem.get_text(strip=True)
                old_price_match = re.search(r'(\d+[.,]?\d*)', old_price_text.replace(' ', ''))
                if old_price_match:
                    old_price = float(old_price_match.group(1).replace(',', '.'))
            
            # Вес/объем
            weight_selector = self.get_selector("weight_volume") or 'span[data-testid="product-weight"]'
            weight_elem = card.select_one(weight_selector)
            weight = weight_elem.get_text(strip=True) if weight_elem else None
            
            # Ссылка на товар
            link_selector = self.get_selector("product_link") or 'div[data-testid="product-card"] a'
            link_elem = card.select_one(link_selector)
            product_url = None
            if link_elem and link_elem.has_attr('href'):
                product_url = link_elem['href']
                if not product_url.startswith('http'):
                    product_url = f"https://5ka.ru{product_url}"
            
            # Изображение
            image_selector = self.get_selector("product_image") or 'img[data-testid="product-image"]'
            image_elem = card.select_one(image_selector)
            image_url = None
            if image_elem:
                image_url = image_elem.get('src') or image_elem.get('data-src')
                if image_url and image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url and not image_url.startswith('http'):
                    image_url = f"https://5ka.ru{image_url}"
            
            # Бренд
            brand_selector = self.get_selector("brand") or 'span[data-testid="product-brand"]'
            brand_elem = card.select_one(brand_selector)
            brand = brand_elem.get_text(strip=True) if brand_elem else None
            
            # Создаём продукт
            product = Product(
                id=f"pyaterochka_{index}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                name=name,
                description=f"{brand} {name}" if brand else name,
                price=ProductPrice(current=price_value, old=old_price),
                category=self._extract_category_name(str(card.parent)),
                product_url=product_url or category_url,
                image_url=image_url,
                attributes={"weight": weight, "brand": brand} if weight or brand else {},
                shop=self.shop_name,
                in_stock=True,
                created_at=datetime.now()
            )
            
            return product
            
        except Exception as e:
            logger.error(f"Ошибка парсинга карточки: {e}")
            return None

    def _extract_total_pages(self, html: str) -> int:
        """Извлечение количества страниц из HTML."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Ищем пагинацию
        pagination_selectors = [
            '.pagination__pages',
            '.paginator',
            '.pager',
            'nav[aria-label="Pagination"]'
        ]
        
        for selector in pagination_selectors:
            elem = soup.select_one(selector)
            if elem:
                page_links = elem.select('a[href*="?page="]')
                if page_links:
                    max_page = 1
                    for link in page_links:
                        match = re.search(r'page=(\d+)', link.get('href', ''))
                        if match:
                            page_num = int(match.group(1))
                            max_page = max(max_page, page_num)
                    return max_page
        
        return 1

    def _extract_category_name(self, html_or_text: str) -> str:
        """Извлечение названия категории."""
        try:
            if '<' in html_or_text:
                soup = BeautifulSoup(html_or_text, 'lxml')
                # Ищем заголовок H1
                h1 = soup.select_one('h1')
                if h1:
                    return h1.get_text(strip=True)
            return "Категория Пятерочки"
        except:
            return "Категория Пятерочки"

    def _create_empty_result(self, category_url: str, errors: list, warnings: list, start_time: datetime) -> ParseResult:
        """Создание пустого результата парсинга."""
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return ParseResult(
            shop=self.shop_name,
            category=CategoryInfo(name="Unknown", url=category_url),
            products=[],
            total_products=0,
            errors=errors,
            warnings=warnings,
            parse_duration_ms=duration_ms
        )
