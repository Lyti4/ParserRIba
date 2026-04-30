import asyncio
import random
import logging
from typing import Optional, List, Dict, Any
from curl_cffi import requests as curl_requests
from loguru import logger
from functools import wraps

# Декоратор для повторных попыток
def retry_on_failure(max_attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Попытка {attempt+1}/{max_attempts} не удалась: {e}. Ждём {delay}с...")
                    await asyncio.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

class BaseParser:
    def __init__(self, store_name: str):
        self.store_name = store_name
        self.session = curl_requests.Session()
        self.headers = self._get_headers()

    def _get_headers(self) -> dict:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }

    @retry_on_failure(max_attempts=3, delay=2)
    async def fetch_page(self, url: str, use_impersonate: str = 'chrome124') -> Optional[str]:
        """Загрузка страницы с улучшенной маскировкой"""
        try:
            headers = self._get_headers()
            # Динамический выбор профиля
            if '5ka.ru' in url:
                use_impersonate = 'chrome124'
            elif 'magnit.ru' in url:
                use_impersonate = 'chrome120'
            
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=45,
                impersonate=use_impersonate,
                allow_redirects=True, 
                verify=False # Игнорируем SSL ошибки для тестов
            )
            
            if response.status_code == 403:
                logger.warning(f"⚠️ Защита (403) на {url}")
                return None
            if response.status_code == 401:
                headers['X-Region'] = '77'
                response = self.session.get(url, headers=headers, timeout=30, impersonate=use_impersonate, verify=False)
                
            return response.text if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None

    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """Загрузка через Playwright (для JS сайтов)"""
        # Заглушка, если playwright не установлен
        logger.warning(f"Playwright не доступен для {url}, пробуем обычный запрос.")
        return await self.fetch_page(url)

    def parse_product(self, html: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("Метод parse_product должен быть реализован в наследнике")
