"""
Базовый класс для парсеров
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
from loguru import logger

from models.product import FishProduct


class BaseParser(ABC):
    """Базовый класс для всех парсеров магазинов"""
    
    def __init__(self, store_name: str, base_url: str):
        self.store_name = store_name
        self.base_url = base_url
        self.session = None
    
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
    
    async def fetch_page(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """
        Загрузка страницы с обработкой ошибок
        
        Args:
            url: URL страницы
            headers: HTTP заголовки
            
        Returns:
            HTML содержимое или None при ошибке
        """
        import aiohttp
        from fake_useragent import UserAgent
        
        if headers is None:
            ua = UserAgent()
            headers = {
                'User-Agent': ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"Ошибка загрузки {url}: статус {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None
    
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
            # Удаляем все кроме цифр, точки и запятой
            cleaned = ''.join(filter(lambda x: x.isdigit() or x in ',.', price_str.strip()))
            # Заменяем запятую на точку
            cleaned = cleaned.replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            logger.warning(f"Не удалось распарсить цену: {price_str}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Очистка текста от лишних пробелов и символов
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
        
        # Удаляем лишние пробелы, переносы строк, табуляции
        cleaned = ' '.join(text.split())
        return cleaned.strip()
    
    async def delay(self, seconds: int = 2):
        """Задержка между запросами"""
        await asyncio.sleep(seconds)
