"""
Парсер для Перекрестка - использует API напрямую
"""
import json
from typing import List, Optional
from loguru import logger

from parsers.base_parser import BaseParser
from models.product import FishProduct


class PerekrestokParser(BaseParser):
    """Парсер для магазина Перекресток"""
    
    def __init__(self):
        super().__init__(
            store_name="Перекресток",
            base_url="https://perekrestok.ru"
        )
        self.api_base = "https://api.perekrestok.ru/v1"
        self.categories = [
            {"id": "ryba-moreprodukty", "name": "рыба и морепродукты"},
            {"id": "ryba-kopchenaya-solenaya", "name": "рыба копченая и соленая"},
            {"id": "ikra-delikatesy", "name": "икра и деликатесы"},
            {"id": "konservy-rybnye", "name": "консервы рыбные"},
            {"id": "moreprodukty", "name": "морепродукты"},
        ]
    
    def get_category_urls(self) -> List[str]:
        return [f"{self.base_url}/catalog/{cat['id']}" for cat in self.categories]
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Парсинг рыбных товаров из Перекрестка через API"""
        from curl_cffi import requests as curl_requests
        
        products = []
        
        # Получаем cookies с главной страницы
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        session = curl_requests.Session()
        
        # Сначала заходим на главную для получения cookies
        try:
            session.get(f"{self.base_url}/", headers=headers, impersonate='chrome120', timeout=15)
        except Exception as e:
            logger.warning(f"Не удалось получить cookies: {e}")
        
        for category in self.categories:
            logger.info(f"Парсинг категории: {category['name']}")
            
            # Пробуем разные варианты API endpoints
            api_urls = [
                f"{self.api_base}/products?category={category['id']}",
                f"{self.api_base}/catalog/products?category_id={category['id']}",
                f"{self.base_url}/api/catalog/{category['id']}",
            ]
            
            for api_url in api_urls:
                try:
                    response = session.get(
                        api_url,
                        headers=headers,
                        impersonate='chrome120',
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            page_products = self._parse_api_response(data, category['name'])
                            if page_products:
                                products.extend(page_products)
                                logger.info(f"Найдено товаров: {len(page_products)}")
                                break
                        except json.JSONDecodeError:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Ошибка API {api_url}: {e}")
                    continue
            
            await self.delay(2)
        
        logger.info(f"Всего найдено товаров в Перекрестке: {len(products)}")
        return products
    
    def _parse_api_response(self, data: dict, category_name: str) -> List[FishProduct]:
        """Парсинг JSON ответа API"""
        products = []
        
        # Пытаемся найти товары в разных форматах ответа
        items = []
        if isinstance(data, dict):
            items = data.get('products', data.get('items', data.get('data', [])))
        elif isinstance(data, list):
            items = data
        
        for item in items[:50]:
            try:
                product = self._extract_product_from_json(item, category_name)
                if product and product.price > 0:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Ошибка при парсинге товара: {e}")
        
        return products
    
    def _extract_product_from_json(self, item: dict, category_name: str) -> Optional[FishProduct]:
        """Извлечение данных о товаре из JSON"""
        if not isinstance(item, dict):
            return None
        
        # Название
        name = item.get('name', item.get('title', ''))
        
        # Цена
        price_data = item.get('price', item.get('prices', {}))
        if isinstance(price_data, dict):
            price = float(price_data.get('current', price_data.get('value', 0)))
        elif isinstance(price_data, (int, float)):
            price = float(price_data)
        else:
            price = 0.0
        
        # Вес
        weight = item.get('weight', item.get('volume', item.get('size', None)))
        
        # Ссылка
        slug = item.get('slug', item.get('url', ''))
        url = f"{self.base_url}/product/{slug}" if slug else ""
        
        # Изображение
        image_url = item.get('image', item.get('imageUrl', item.get('picture', None)))
        
        return FishProduct(
            name=name,
            price=price,
            store=self.store_name,
            category=category_name,
            url=url,
            weight=str(weight) if weight else None,
            image_url=image_url
        )
