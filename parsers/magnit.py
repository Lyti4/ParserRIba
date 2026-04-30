"""
Парсер Магнита
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class MagnitParser(BaseParser):
    """Парсер для Магнита"""
    
    def __init__(self, headless: bool = True):
        --- parsers/magnit.py (原始)
"""
Парсер Магнита
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class MagnitParser(BaseParser):
    """Парсер для Магнита"""

    def __init__(self, headless: bool = True):
        super().__init__("Магнит", "https://magnit.ru", headless=headless)
        self.categories = [
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/",
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-svezhaya/",
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-kopchenaya/",
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/konservy/",
        ]

    def get_category_urls(self) -> List[str]:
        return self.categories

    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Магнита"""
        products = []

        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")

            html = await self.fetch_page(category_url)
            if not html:
                await self.delay(2)
                continue

            soup = BeautifulSoup(html, 'lxml')

            # Ищем карточки товаров
            product_cards = soup.select('div[class*="product"], div[class*="card"], article[class*="product"]')

            for card in product_cards[:50]:
                try:
                    name_elem = card.select_one('h3, [class*="name"], [class*="title"], a[href*="/product/"]')
                    price_elem = card.select_one('[class*="price"], [class*="cost"]')
                    link_elem = card.select_one('a[href*="/product/"]')

                    if not name_elem or not price_elem:
                        continue

                    name = self.clean_text(name_elem.get_text())
                    price = self.clean_price(price_elem.get_text())
                    url = link_elem.get('href', '') if link_elem else ''

                    if not url.startswith('http'):
                        url = f"https://magnit.ru{url}" if url else category_url

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

            logger.info(f"Найдено товаров в категории: {len([p for p in products if category_url in p.url])}")
            await self.delay(2)

        await self.close()
        logger.info(f"Всего найдено товаров в Магните: {len(products)}")
        return products

+++ parsers/magnit.py (修改后)
"""
Парсер Магнита
"""
from typing import List
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class MagnitParser(BaseParser):
    """Парсер для Магнита"""

    def __init__(self, headless: bool = True):
        super().__init__("Магнит", "https://magnit.ru", headless=headless)
        self.categories = [
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/",
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/ryba-kopchenaya/",
            "https://magnit.ru/catalog/produkty/ryba-i-moreprodukty/konservy-rybnye/",
        ]

    def get_category_urls(self) -> List[str]:
        return self.categories

    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Магнита"""
        products = []

        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")

            html = await self.fetch_page(category_url)
            if not html:
                await self.delay(2)
                continue

            soup = BeautifulSoup(html, 'lxml')

            # Ищем карточки товаров
            product_cards = soup.select('div[class*="product"], div[class*="card"], article[class*="product"]')

            for card in product_cards[:50]:
                try:
                    name_elem = card.select_one('h3, [class*="name"], [class*="title"], a[href*="/product/"]')
                    price_elem = card.select_one('[class*="price"], [class*="cost"]')
                    link_elem = card.select_one('a[href*="/product/"]')

                    if not name_elem or not price_elem:
                        continue

                    name = self.clean_text(name_elem.get_text())
                    price = self.clean_price(price_elem.get_text())
                    url = link_elem.get('href', '') if link_elem else ''

                    if not url.startswith('http'):
                        url = f"https://magnit.ru{url}" if url else category_url

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

            logger.info(f"Найдено товаров в категории: {len([p for p in products if category_url in p.url])}")
            await self.delay(2)

        await self.close()
        logger.info(f"Всего найдено товаров в Магните: {len(products)}")
        return products
        return self.categories
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Магнита"""
        products = []
        
        for category_url in self.categories:
            logger.info(f"Парсинг категории: {category_url}")
            
            html = await self.fetch_page(category_url)
            if not html:
                await self.delay(2)
                continue
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Ищем карточки товаров
            product_cards = soup.select('div[class*="product"], div[class*="card"], article[class*="product"]')
            
            for card in product_cards[:50]:
                try:
                    name_elem = card.select_one('h3, [class*="name"], [class*="title"], a[href*="/product/"]')
                    price_elem = card.select_one('[class*="price"], [class*="cost"]')
                    link_elem = card.select_one('a[href*="/product/"]')
                    
                    if not name_elem or not price_elem:
                        continue
                    
                    name = self.clean_text(name_elem.get_text())
                    price = self.clean_price(price_elem.get_text())
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    if not url.startswith('http'):
                        url = f"https://magnit.ru{url}" if url else category_url
                    
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
            
            logger.info(f"Найдено товаров в категории: {len([p for p in products if category_url in p.url])}")
            await self.delay(2)
        
        await self.close()
        logger.info(f"Всего найдено товаров в Магните: {len(products)}")
        return products
