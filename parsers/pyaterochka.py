"""
Парсер Пятерочки
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class PyaterochkaParser(BaseParser):
    """Парсер для Пятерочки"""
    
    def __init__(self):
        super().__init__("Пятерочка", "https://5ka.ru")
        self.categories = [
            "https://5ka.ru/cat/ryba_i_moreprodukty",
            "https://5ka.ru/cat/ryba_kopchenaya_i_solenaya",
            "https://5ka.ru/cat/ikra_i_rybnye_delikatesy",
            "https://5ka.ru/cat/konservy_rybnye",
        ]
    
    def get_category_urls(self) -> List[str]:
        return self.categories
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Пятерочки"""
        products = []
        
        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")
            
            html = await self.fetch_page(category_url)
            if not html:
                await self.delay(2)
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Ищем карточки товаров - селекторы могут меняться
            product_cards = soup.select('div[data-testid="product-card"], div.catalog-item, article.product-card, [class*="product"], [class*="card"]')
            
            for card in product_cards[:50]:  # Ограничим количество
                try:
                    name_elem = card.select_one('h3, [class*="name"], [class*="title"], a[href*="/prod/"]')
                    price_elem = card.select_one('[class*="price"], [class*="cost"], span[data-testid*="price"]')
                    link_elem = card.select_one('a[href*="/prod/"], a[href*="/product/"]')
                    
                    if not name_elem or not price_elem:
                        continue
                    
                    name = self.clean_text(name_elem.get_text())
                    price = self.clean_price(price_elem.get_text())
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    if not url.startswith('http'):
                        url = f"https://5ka.ru{url}" if url else category_url
                    
                    if name and price:
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
            
            logger.info(f"Найдено товаров: {len(products)}")
            await self.delay(2)
        
        await self.close()
        logger.info(f"Всего найдено товаров в Пятерочке: {len(products)}")
        return products
