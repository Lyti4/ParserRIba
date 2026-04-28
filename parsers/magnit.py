"""
Парсер для Магнита
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from parsers.base_parser import BaseParser
from models.product import FishProduct


class MagnitParser(BaseParser):
    """Парсер для магазина Магнит"""
    
    def __init__(self):
        super().__init__(
            store_name="Магнит",
            base_url="https://magnit.ru"
        )
        self.categories = [
            "https://magnit.ru/catalog/ryba-moreprodukty/",
            "https://magnit.ru/catalog/ryba-kopchenaya-solenaya/",
            "https://magnit.ru/catalog/konservy-rybnye/",
        ]
    
    def get_category_urls(self) -> List[str]:
        return self.categories
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Магнита"""
        products = []
        
        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")
            
            html = await self.fetch_page(category_url)
            if html:
                page_products = self._parse_product_list(html, category_url)
                products.extend(page_products)
                logger.info(f"Найдено товаров: {len(page_products)}")
            
            await self.delay(2)
        
        logger.info(f"Всего найдено товаров в Магните: {len(products)}")
        return products
    
    def _parse_product_list(self, html: str, category_url: str) -> List[FishProduct]:
        """Парсинг списка товаров со страницы категории"""
        products = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Ищем карточки товаров
        product_cards = soup.select('.product-item, .catalog-product, .goods-card, [class*="product"]')
        
        for card in product_cards[:50]:
            try:
                product = self._extract_product(card, category_url)
                if product and product.price > 0:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Ошибка при парсинге карточки: {e}")
        
        return products
    
    def _extract_product(self, card, category_url: str) -> FishProduct:
        """Извлечение данных о товаре из карточки"""
        # Название
        name_elem = card.select_one('.name, .title, .product-title, h2, h3, [class*="name"], [class*="title"]')
        name = self.clean_text(name_elem.get_text()) if name_elem else ""
        
        # Цена
        price_elem = card.select_one(
            '.price, .cost, .product-price, [class*="price"], [class*="cost"], [class*="rub"]'
        )
        price_str = self.clean_text(price_elem.get_text()) if price_elem else "0"
        price = self.clean_price(price_str) or 0.0
        
        # Вес
        weight_elem = card.select_one(
            '.weight, .volume, .size, [class*="weight"], [class*="volume"], [class*="gram"], [class*="kg"]'
        )
        weight = self.clean_text(weight_elem.get_text()) if weight_elem else None
        
        # Ссылка
        link_elem = card.select_one('a[href]')
        url = ""
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            if href.startswith('/'):
                url = f"{self.base_url}{href}"
            elif href.startswith('http'):
                url = href
        
        # Изображение
        img_elem = card.select_one('img[src], img[data-src]')
        image_url = None
        if img_elem:
            src = img_elem.get('data-src') or img_elem.get('src')
            if src:
                image_url = src if src.startswith('http') else f"{self.base_url}{src}"
        
        # Категория
        category = "рыбные товары"
        if "копчен" in category_url.lower() or "солен" in category_url.lower():
            category = "рыба копченая и соленая"
        elif "консерв" in category_url.lower():
            category = "консервы рыбные"
        elif "морепродукт" in category_url.lower() or "рыб" in category_url.lower():
            category = "рыба и морепродукты"
        
        return FishProduct(
            name=name,
            price=price,
            store=self.store_name,
            category=category,
            url=url,
            weight=weight,
            image_url=image_url
        )
