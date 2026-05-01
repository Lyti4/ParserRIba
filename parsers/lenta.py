"""
Парсер для магазина "Лента".
Использует Playwright для обхода Cloudflare Turnstile.
Критично: Header X-Region обязателен.
"""
import asyncio
import json
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, BrowserContext
from pydantic import BaseModel, Field

from .base_parser import BaseParser
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy
from utils.kb_loader import KBLoader


class LentaProduct(BaseModel):
    """Модель продукта для Ленты."""
    name: str
    price_current: float
    price_old: Optional[float] = None
    unit_price: Optional[float] = None
    weight_volume: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    product_link: Optional[str] = None
    discount: Optional[int] = None
    source: str = "lenta"
    raw_data: Optional[Dict[str, Any]] = None


class LentaParser(BaseParser):
    def __init__(self, context: BrowserContext, kb_path: str = "knowledge_base/lenta.md"):
        super().__init__(context, kb_path)
        self.kb = KBLoader().load_shop("lenta")
        
        # Стратегии
        self.strategies = [
            ScrollStrategy(self.page, delay=1.0, steps=5),
            LazyLoadStrategy(self.page, timeout=5000)
        ]
        
        # Критичные заголовки из KB
        self.required_headers = self.kb.headers.custom or {}
        if "X-Region" not in self.required_headers:
            raise ValueError("LentaParser: Header X-Region обязателен!")

    async def navigate_to_category(self, url: str) -> bool:
        """Переход с применением специфичных хедеров."""
        try:
            await self.page.set_extra_http_headers(self.required_headers)
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Ожидание появления товаров или обработки Cloudflare
            await asyncio.sleep(2)  # Пауза для JS
            
            if await self.is_blocked():
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Ошибка навигации: {e}")
            return False

    async def is_blocked(self) -> bool:
        """Проверка на Cloudflare Turnstile или капчу."""
        indicators = [
            "iframe[src*='challenges.cloudflare.com']",
            "title:has-text('Just a moment')",
            "div[class*='cf-turnstile']"
        ]
        for selector in indicators:
            if await self.page.query_selector(selector):
                self.logger.warning("Обнаружена защита Cloudflare/CAPTCHA")
                return True
        return False

    async def parse_category(self, url: str, max_pages: int = 1) -> List[LentaProduct]:
        """Основной метод парсинга категории."""
        products = []
        
        if not await self.navigate_to_category(url):
            self.logger.error("Не удалось загрузить страницу (блокировка)")
            return products

        # Применение стратегий
        for strategy in self.strategies:
            await strategy.execute()

        # Парсинг товаров через JS
        js_code = """
        () => {
            const cards = document.querySelectorAll('article[data-testid="product-card"], div[class*="ProductCard"]');
            return Array.from(cards).map(card => {
                const nameEl = card.querySelector('[data-testid="product-name"], h3, .product-name');
                const priceEl = card.querySelector('[data-testid="price-current"], .price-current, span[class*="price"]');
                const oldPriceEl = card.querySelector('[data-testid="price-old"], .price-old, s');
                const unitPriceEl = card.querySelector('.price-per-unit, .unit-price');
                const weightEl = card.querySelector('.weight, .volume, .size');
                const brandEl = card.querySelector('.brand, .manufacturer');
                const imgEl = card.querySelector('img');
                const linkEl = card.querySelector('a[href*="/product/"]');
                
                // Расчет скидки
                let discount = null;
                if (priceEl && oldPriceEl) {
                    const p = parseFloat(priceEl.innerText.replace(/[^0-9.]/g, ''));
                    const op = parseFloat(oldPriceEl.innerText.replace(/[^0-9.]/g, ''));
                    if (p && op && op > p) discount = Math.round(((op - p) / op) * 100);
                }

                return {
                    name: nameEl ? nameEl.innerText.trim() : '',
                    price_current: priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, '')) : null,
                    price_old: oldPriceEl ? parseFloat(oldPriceEl.innerText.replace(/[^0-9.]/g, '')) : null,
                    unit_price: unitPriceEl ? parseFloat(unitPriceEl.innerText.replace(/[^0-9.]/g, '')) : null,
                    weight_volume: weightEl ? weightEl.innerText.trim() : null,
                    brand: brandEl ? brandEl.innerText.trim() : null,
                    image_url: imgEl ? (imgEl.src || imgEl.dataset.src) : null,
                    product_link: linkEl ? linkEl.href : null,
                    discount: discount
                };
            }).filter(p => p.name && p.price_current);
        }
        """
        
        try:
            raw_data = await self.page.evaluate(js_code)
            for item in raw_data:
                try:
                    product = LentaProduct(**item, raw_data=item)
                    products.append(product)
                except Exception as e:
                    self.logger.warning(f"Ошибка валидации продукта: {e}, данные: {item}")
        except Exception as e:
            self.logger.error(f"Ошибка выполнения JS: {e}")

        # Пагинация (если есть)
        # Лента часто использует бесконечный скролл, но проверим кнопки
        if max_pages > 1:
            next_btn_selectors = self.kb.selectors.get("pagination_next", [])
            for sel in next_btn_selectors:
                btn = await self.page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(2)
                    products.extend(await self.parse_category(self.page.url, max_pages - 1))
                    break

        return products

    async def handle_captcha(self) -> bool:
        """Обработка Cloudflare Turnstile (автоматически через Playwright)."""
        self.logger.info("Попытка обхода Cloudflare...")
        await asyncio.sleep(5)  # Ждем автоматического решения
        return not await self.is_blocked()
