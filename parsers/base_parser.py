"""
Базовый класс для парсеров с использованием curl-cffi и requests-html
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
from loguru import logger
from curl_cffi import requests as curl_requests
from fake_useragent import UserAgent
from requests_html import HTMLSession

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
    
    async def fetch_page_js(self, url: str) -> Optional[str]:
        """
        Загрузка страницы с JavaScript рендерингом (использует requests-html)
        
        Args:
            url: URL страницы
            
        Returns:
            HTML содержимое или None при ошибке
        """
        try:
            if not self.session:
                self.session = HTMLSession()
            
            headers = self._get_headers()
            self.session.headers.update(headers)
            
            r = self.session.get(url, timeout=30)
            
            # Пытаемся выполнить JavaScript
            try:
                await r.html.arender(timeout=30, keep_page=True)
            except Exception:
                pass  # Если JS не выполнился, используем обычный HTML
            
            return r.html.html
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url} с JS: {e}")
            return None
    
    async def fetch_page_with_js(self, url: str) -> Optional[str]:
        """
        Загрузка страницы с JavaScript рендерингом (алиас для fetch_page_js)
        
        Args:
            url: URL страницы
            
        Returns:
            HTML содержимое или None при ошибке
        """
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
        """Закрытие сессии"""
        if self.session:
            self.session.close()
    
    async def delay(self, seconds: int = 2):
        """Задержка между запросами"""
        await asyncio.sleep(seconds)
