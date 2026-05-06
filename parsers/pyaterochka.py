import asyncio
from typing import Any, Dict, List, Optional
from parsers.base_parser import BaseParser, Product
from parsers.camoufox_parser import CamoufoxParser
from utils.logger import get_logger

logger = get_logger(__name__)

class PyaterochkaParser(BaseParser, CamoufoxParser):
    """Парсер для Пятерочки на базе Camoufox"""
    
    def __init__(self, shop_name: str = "pyaterochka", **kwargs):
        # Инициализация базовых классов
        BaseParser.__init__(self, shop_name=shop_name, store_name=shop_name, **kwargs)
        CamoufoxParser.__init__(self, headless=kwargs.get('headless', True), geoip_path=kwargs.get('geoip_path'))
        
    async def parse_category(self, category_url: str, category_name: str) -> List[Product]:
        """Парсинг конкретной категории"""
        products = []
        page = None
        
        try:
            # Запускаем браузер и получаем страницу
            page = await self.start_browser()
            
            logger.info(f"📂 Переход к категории: {category_name}")
            
            # Переход на страницу
            await page.goto(category_url, wait_until="domcontentloaded")
            
            # Применяем стратегию скроллинга если нужно
            if self.strategies.get('scrolling'):
                logger.info("🔄 Выполнение скроллинга страницы...")
                await self._scroll_page(page)
            
            # Ждем загрузки элементов
            selector = self.selectors.get('product_card')
            if selector:
                await page.wait_for_selector(selector, timeout=10000)
            
            # Получаем все карточки товаров
            product_cards = await page.query_selector_all(selector) if selector else []
            
            logger.info(f"📦 Найдено товаров: {len(product_cards)}")
            
            for idx, card in enumerate(product_cards):
                try:
                    product = await self._extract_product(card, idx)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка извлечения товара #{idx}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга категории {category_name}: {e}")
            raise
        finally:
            # Закрываем браузер
            await self.close_browser()
                    
        return products

    async def _extract_product(self, card_element, index: int) -> Optional[Product]:
        """Извлечение данных из карточки товара"""
        try:
            # Извлекаем данные используя селекторы из Knowledge Base
            name_sel = self.selectors.get('name')
            price_sel = self.selectors.get('price')
            weight_sel = self.selectors.get('weight')
            image_sel = self.selectors.get('image')
            
            name_el = await card_element.query_selector(name_sel) if name_sel else None
            price_el = await card_element.query_selector(price_sel) if price_sel else None
            weight_el = await card_element.query_selector(weight_sel) if weight_sel else None
            image_el = await card_element.query_selector(image_sel) if image_sel else None
            
            name = await name_el.inner_text() if name_el else "Неизвестно"
            price_text = await price_el.inner_text() if price_el else "0"
            weight = await weight_el.inner_text() if weight_el else ""
            image_src = await image_el.get_attribute('src') if image_el else ""
            
            # Очистка цены
            price_str = price_text.replace('₽', '').replace(' ', '').strip()
            price = float(price_str) if price_str else 0.0
            
            # Получаем ссылку на товар
            link_el = await card_element.query_selector('a')
            source_url = await link_el.get_attribute('href') if link_el else ""
            
            return Product(
                name=name.strip(),
                price=price,
                currency="RUB",
                weight=weight.strip(),
                image_url=image_src or "",
                source_url=source_url,
                shop=self.shop_name,
                category=self.current_category_name,
                scraped_at=asyncio.get_event_loop().time()
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось распарсить товар #{index}: {e}")
            return None

    async def _scroll_page(self, page):
        """Скроллинг страницы для подгрузки lazy-load элементов"""
        scroll_steps = 5
        scroll_delay = 0.5
        
        for i in range(scroll_steps):
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight / {scroll_steps} * {i+1})")
            await asyncio.sleep(scroll_delay)
            
        # Возврат в начало
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
