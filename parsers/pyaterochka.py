import asyncio
import logging
from typing import List, Dict, Any
from curl_cffi import requests as curl_requests
from loguru import logger

from parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class PyaterochkaParser(BaseParser):
    """Парсер Пятерочки на основе curl-cffi + Knowledge Base"""
    
    def __init__(self, store_name: str = "pyaterochka", region: str = "77", **kwargs):
        # Инициализируем базовый парсер с загрузкой KB
        super().__init__(shop_name=store_name, region=region, headless=kwargs.get('headless', True))
        self.region = region
        self.base_url = "https://5ka.ru"
        logger.info(f"PyaterochkaParser initialized for region {region}")

    async def parse_category(self, category_url: str, category_name: str, **kwargs):
        """Парсинг категории товаров через браузер (Camoufox/Playwright)"""
        from models.schemas import ParseResult, CategoryInfo
        
        logger.info(f"Parsing category: {category_url}")
        
        # Определяем режим headless из kwargs или используем значение по умолчанию
        headless_mode = kwargs.get('headless', 'virtual')
        if kwargs.get('no_headless', False):
            headless_mode = False
        
        try:
            # Запускаем браузер с видимым окном если нужно
            await self.start_browser(
                use_camoufox=True,
                geoip=False,
                block_images=False,  # Не блокируем изображения для правильного рендеринга
                block_webgl=False,
                addons=None,
                headless=headless_mode,
                humanize=True
            )
            
            # Переходим на страницу категории
            logger.info(f"🌐 Переход на страницу: {category_url}")
            await self._page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
            
            # Применяем стратегии (скроллинг, lazy load) если они включены в KB
            if self._strategies_config.get('scrolling', False):
                logger.info("📜 Выполняем скроллинг страницы...")
                await self._apply_scrolling()
            
            if self._strategies_config.get('lazy_load', False):
                logger.info("⏳ Ожидание загрузки lazy-элементов...")
                await self._page.wait_for_timeout(3000)
            
            # Получаем HTML после выполнения JS
            html = await self._page.content()
            logger.info(f"✅ Страница загружена ({len(html)} bytes)")
            
            # Парсим товары из HTML
            products = await self._parse_products_from_html(html)
            
            # Закрываем браузер
            await self.close_browser()
            
            return ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(name=category_name, url=category_url),
                products=products,
                total_products=len(products),
                errors=[],
                warnings=[]
            )
                
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге категории: {e}")
            # Закрываем браузер в случае ошибки
            await self.close_browser()
            raise
    
    async def _apply_scrolling(self):
        """Применение стратегии скроллинга"""
        # Простой скроллинг вниз и вверх
        await self._page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    let scrollHeight = document.body.scrollHeight;
                    let currentScroll = 0;
                    let distance = 500;
                    let timer = setInterval(() => {
                        currentScroll += distance;
                        window.scrollTo(0, currentScroll);
                        if (currentScroll > scrollHeight - window.innerHeight) {
                            clearInterval(timer);
                            // Скроллим обратно вверх
                            window.scrollTo(0, 0);
                            resolve();
                        }
                    }, 500);
                });
            }
        """)
        await self._page.wait_for_timeout(2000)
    
    async def _parse_products_from_html(self, html: str):
        """Парсинг товаров из HTML с использованием селекторов из KB"""
        from playwright.async_api import Page
        from models.schemas import Product, ProductPrice
        
        products = []
        
        # Получаем селекторы из KB
        product_card_selector = self.get_selector('product_card')
        name_selector = self.get_selector('product_name')
        price_selector = self.get_selector('price_current')
        old_price_selector = self.get_selector('price_old')
        weight_selector = self.get_selector('product_weight')
        brand_selector = self.get_selector('product_brand')
        image_selector = self.get_selector('product_image')
        link_selector = self.get_selector('product_link')
        
        if not product_card_selector:
            logger.warning("⚠️ Селектор product_card не найден в KB")
            return products
        
        # Находим все карточки товаров
        try:
            card_elements = await self._page.query_selector_all(product_card_selector)
            logger.info(f"📦 Найдено {len(card_elements)} карточек товаров")
            
            for idx, card in enumerate(card_elements):
                try:
                    # Извлекаем данные из карточки
                    name_el = await card.query_selector(name_selector) if name_selector else None
                    price_el = await card.query_selector(price_selector) if price_selector else None
                    old_price_el = await card.query_selector(old_price_selector) if old_price_selector else None
                    weight_el = await card.query_selector(weight_selector) if weight_selector else None
                    brand_el = await card.query_selector(brand_selector) if brand_selector else None
                    image_el = await card.query_selector(image_selector) if image_selector else None
                    link_el = await card.query_selector(link_selector) if link_selector else None
                    
                    name = await name_el.inner_text() if name_el else ""
                    price_text = await price_el.inner_text() if price_el else "0"
                    old_price_text = await old_price_el.inner_text() if old_price_el else None
                    weight = await weight_el.inner_text() if weight_el else ""
                    brand = await brand_el.inner_text() if brand_el else ""
                    
                    # Очищаем цену от лишних символов
                    price_value = int(''.join(filter(str.isdigit, price_text)) or 0)
                    old_price_value = None
                    if old_price_text:
                        old_price_value = int(''.join(filter(str.isdigit, old_price_text)) or 0)
                    
                    # Получаем ссылку
                    product_url = ""
                    if link_el:
                        href = await link_el.get_attribute('href')
                        if href:
                            product_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                    # Получаем изображение
                    image_url = ""
                    if image_el:
                        image_url = await image_el.get_attribute('src') or ""
                    
                    product = Product(
                        name=name.strip(),
                        price=ProductPrice(current=price_value, old=old_price_value),
                        weight=weight.strip() if weight else None,
                        brand=brand.strip() if brand else None,
                        url=product_url,
                        image_url=image_url
                    )
                    
                    if name.strip():  # Добавляем только если есть название
                        products.append(product)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при парсинге карточки {idx}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске карточек: {e}")
        
        return products
