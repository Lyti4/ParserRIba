"""
Парсер Перекрестка
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class PerekrestokParser(BaseParser):
    """Парсер для Перекрестка"""
    
    def __init__(self, headless: bool = True):
        super().__init__("Перекресток", "https://perekrestok.ru", headless=headless)
        self.categories = [
            "https://perekrestok.ru/catalog/ryba-moreprodukty",
            "https://perekrestok.ru/catalog/ryba-kopchenaya-solenaya",
            "https://perekrestok.ru/catalog/ikra-delikatesy",
            "https://perekrestok.ru/catalog/konservy-rybnye",
            "https://perekrestok.ru/catalog/moreprodukty",
        ]
    
    def get_category_urls(self) -> List[str]:
        return self.categories
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Перекрестка"""
        products = []
        
        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")
            
            # Используем requests-html с JavaScript
            html = await self.fetch_page_with_js(category_url)
            if not html:
                logger.warning(f"Не удалось загрузить страницу {category_url}")
                await self.delay(2)
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Ищем карточки товаров - различные селекторы
            product_cards = (
                soup.select('div[class*="product-card"]') or
                soup.select('div[class*="ProductCard"]') or
                soup.select('article[class*="product"]') or
                soup.select('div[data-product-id]') or
                soup.select('div[class*="catalog-item"]')
            )
            
            if not product_cards:
                # Пробуем найти все элементы с ценами
                product_cards = soup.select('div[class*="price"], span[class*="price"]')
            
            logger.debug(f"Найдено элементов на странице: {len(product_cards)}")
            
            for card in product_cards[:50]:
                try:
                    name_elem = (
                        card.select_one('h3') or
                        card.select_one('[class*="name"]') or
                        card.select_one('[class*="title"]') or
                        card.select_one('a[href*="/product/"]') or
                        card.select_one('[data-name]')
                    )
                    price_elem = (
                        card.select_one('[class*="price"]') or
                        card.select_one('[class*="cost"]') or
                        card.select_one('[data-price]')
                    )
                    link_elem = card.select_one('a[href*="/product/"]')
                    
                    if not name_elem or not price_elem:
                        continue
                    
                    name = self.clean_text(name_elem.get_text())
                    price = self.clean_price(price_elem.get_text())
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    if not url.startswith('http'):
                        url = f"https://perekrestok.ru{url}" if url else category_url
                    
                    if name and price and len(name) > 2:
                        product = FishProduct(
                            name=name,
                            price=price,
                            store=self.store_name,
                            url=url,
                            category="рыба/морепродукты"
                        )
                        products.append(product)
                        
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге карточки: {e}")
                    continue
            
            count_in_category = len([p for p in products if category_url in p.url or not p.url])
            logger.info(f"Найдено товаров в категории: {count_in_category}")
            await self.delay(3)
        
        await self.close()
        logger.info(f"Всего найдено товаров в Перекрестке: {len(products)}")
        return products
