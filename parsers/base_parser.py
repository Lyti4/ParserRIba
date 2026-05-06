import asyncio
import json
import logging
import platform
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from camoufox.async_api import AsyncCamoufox
from loguru import logger

# ИСПРАВЛЕННЫЙ ИМПОРТ
from utils.kb_loader import SelectorConfig, HeadersConfig, StrategyConfig, CategoryConfig, ShopKnowledge, KnowledgeBase
from models.product import Product
from utils.geoip import GeoIPService # Убедись, что этот файл есть, иначе закомментируй

logger = logging.getLogger(__name__)

class BaseParser:
    def __init__(self, store_name: str, headless: bool = True, geoip: bool = False):
        self.store_name = store_name.lower()
        self.headless = headless
        self.use_geoip = geoip
        
        self.kb = KnowledgeBase(self.store_name)
        # self.geoip_service = GeoIPService() if self.use_geoip else None # Закомментируй если нет geoip.py
        
        # Заглушка для конфигурации, если KB не загружен реально
        self._load_knowledge_base_stub()
        self._init_strategies()
        
        self._camoufox_browser: Optional[AsyncCamoufox] = None
        self._page = None
        self._context = None
        
        logger.info(f"🚀 Парсер {self.store_name} инициализирован")

    def _load_knowledge_base_stub(self):
        """Заглушка для загрузки конфигурации, чтобы код работал"""
        # В реальном проекте тут парсинг markdown
        # Для теста хардкодим настройки Пятерочки
        if self.store_name == 'pyaterochka':
            self.kb.categories = {
                "Рыба": CategoryConfig(name="Рыба", url="https://5ka.ru/catalog/ryba--251C13077/"),
                "Морепродукты": CategoryConfig(name="Морепродукты", url="https://5ka.ru/catalog/moreprodukty--251C13078/"),
                "Котлеты и фарш": CategoryConfig(name="Котлеты и фарш", url="https://5ka.ru/catalog/kotlety-i-farsh--251C13081/"),
                "Икра и закуски": CategoryConfig(name="Икра и закуски", url="https://5ka.ru/catalog/ikra-i-zakuski--251C13082/")
            }
            self.kb.selectors = {
                "product_card": ["article[class*='Card'] div[class*='card-content']", "div[data-testid='product-card']"],
                "product_name": ".product-title__text",
                "price": ".price-for-one__value",
                "old_price": ".price-for-one__old-value",
                "image": "img[class*='product-image']"
            }
            self.kb.strategies = StrategyConfig(scrolling=True, pagination=False, lazy_load=False)
            self.kb.headers = HeadersConfig(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    def _init_strategies(self):
        self.strategies = {}
        if self.kb.strategies and self.kb.strategies.scrolling:
            # Простая реализация скролла без отдельного класса
            self.strategies['scrolling'] = True

    async def _start_camoufox(self):
        if self._camoufox_browser:
            return

        system_os = platform.system()
        effective_headless = False if system_os == "Windows" and not self.headless else self.headless

        logger.info(f"🦊 Запуск Camoufox (OS={system_os}, headless={effective_headless})...")

        try:
            self._camoufox_browser = AsyncCamoufox()
            
            await self._camoufox_browser.start(
                headless=effective_headless,
                humanize=True,
                fingerprint=True,
                disable_coop=True,
                block_images=False,
                block_webgl=False,
                i_know_what_im_doing=True
            )
            
            self._context = await self._camoufox_browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            self._page = await self._context.new_page()
            
            logger.info("✅ Camoufox запущен успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка запуска Camoufox: {e}")
            await self.close_browser()
            raise

    async def close_browser(self):
        try:
            if self._page: await self._page.close()
            if self._context: await self._context.close()
            if self._camoufox_browser:
                await self._camoufox_browser.__aexit__(None, None, None)
            self._page = None
            self._context = None
            self._camoufox_browser = None
            logger.info("🛑 Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии: {e}")

    async def parse_category(self, category_name: str) -> List[Product]:
        if category_name not in self.kb.categories:
            return []

        category_config = self.kb.categories[category_name]
        url = category_config.url
        products = []

        if not self._page:
            await self._start_camoufox()
            await asyncio.sleep(2)

        try:
            logger.info(f"Переход: {url}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5) # Ждем загрузки

            # Скролл
            if self.strategies.get('scrolling'):
                logger.info("Выполняю скроллинг...")
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

            products = await self._parse_products_from_page(category_name)
            logger.info(f"✅ Найдено товаров: {len(products)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {category_name}: {e}")
            
        return products

    async def _parse_products_from_page(self, category_name: str) -> List[Product]:
        products = []
        selectors = self.kb.selectors.get("product_card", [])
        if isinstance(selectors, str): selectors = [selectors]
        
        elements = None
        for sel in selectors:
            try:
                els = await self._page.query_selector_all(sel)
                if els:
                    elements = els
                    logger.debug(f"Найдено по селектору {sel}: {len(els)}")
                    break
            except: continue

        if not elements:
            logger.warning("Карточки не найдены")
            return []

        for idx, el in enumerate(elements):
            try:
                p = await self._extract_product(el, category_name, idx)
                if p: products.append(p)
            except: continue
            
        return products

    async def _extract_product(self, element, cat_name: str, idx: int) -> Optional[Product]:
        try:
            async def get_text(css):
                if not css: return ""
                el = await element.query_selector(css)
                return (await el.inner_text()).strip() if el else ""
            
            name = await get_text(self.kb.selectors.get("product_name"))
            price_str = await get_text(self.kb.selectors.get("price"))
            
            if not name: return None
            
            price = 0.0
            if price_str:
                clean = "".join(filter(lambda x: x.isdigit() or x == '.', price_str.replace(',', '.')))
                if clean: price = float(clean)

            return Product(
                id=f"{self.store_name}_{idx}",
                name=name,
                price=price,
                category=cat_name,
                shop=self.store_name,
                currency="RUB"
            )
        except: return None

    async def parse_all_categories(self) -> Dict[str, List[Product]]:
        results = {}
        for name in self.kb.categories:
            logger.info(f"📦 Категория: {name}")
            res = await self.parse_category(name)
            results[name] = res
            await asyncio.sleep(2)
        return results
