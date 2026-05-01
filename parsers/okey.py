"""
Парсер для магазина "О'Кей".
Критично: Header X-Store-Id обязателен.
"""
import asyncio
from typing import List, Optional, Dict, Any
from playwright.async_api import BrowserContext
from pydantic import BaseModel

from .base_parser import BaseParser
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy
from utils.kb_loader import KBLoader


class OkeyProduct(BaseModel):
    """Модель продукта для О'Кей."""
    name: str
    price_current: float
    price_old: Optional[float] = None
    unit_price: Optional[float] = None
    weight_volume: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    product_link: Optional[str] = None
    discount: Optional[int] = None
    source: str = "okey"
    raw_data: Optional[Dict[str, Any]] = None


class OkeyParser(BaseParser):
    def __init__(self, context: BrowserContext, kb_path: str = "knowledge_base/okey.md"):
        super().__init__(context, kb_path)
        self.kb = KBLoader().load_shop("okey")
        
        self.strategies = [
            ScrollStrategy(self.page, delay=1.0, steps=5),
            LazyLoadStrategy(self.page, timeout=5000)
        ]
        
        self.required_headers = self.kb.headers.custom or {}
        if "X-Store-Id" not in self.required_headers:
            raise ValueError("OkeyParser: Header X-Store-Id обязателен!")

    async def navigate_to_category(self, url: str) -> bool:
        try:
            await self.page.set_extra_http_headers(self.required_headers)
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            if await self.is_blocked():
                return False
            return True
        except Exception as e:
            self.logger.error(f"Ошибка навигации: {e}")
            return False

    async def is_blocked(self) -> bool:
        indicators = [
            "iframe[src*='challenges.cloudflare.com']",
            "div[class*='captcha']",
            "title:has-text('Access denied')"
        ]
        for selector in indicators:
            if await self.page.query_selector(selector):
                self.logger.warning("Обнаружена защита/капча")
                return True
        return False

    async def parse_category(self, url: str, max_pages: int = 1) -> List[OkeyProduct]:
        products = []
        
        if not await self.navigate_to_category(url):
            return products

        for strategy in self.strategies:
            await strategy.execute()

        js_code = """
        () => {
            const cards = document.querySelectorAll('div.product-card, article.product');
            return Array.from(cards).map(card => {
                const nameEl = card.querySelector('.product-name, h3, a.title');
                const priceEl = card.querySelector('.price-current, .price');
                const oldPriceEl = card.querySelector('.price-old, s');
                const unitPriceEl = card.querySelector('.price-per-unit');
                const weightEl = card.querySelector('.weight, .size');
                const brandEl = card.querySelector('.brand');
                const imgEl = card.querySelector('img');
                const linkEl = card.querySelector('a[href*="/product/"]');
                
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
                    product = OkeyProduct(**item, raw_data=item)
                    products.append(product)
                except Exception as e:
                    self.logger.warning(f"Ошибка валидации: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка JS: {e}")

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
        self.logger.info("Попытка обхода капчи...")
        await asyncio.sleep(5)
        return not await self.is_blocked()
