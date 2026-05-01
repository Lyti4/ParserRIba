"""
Парсер для магазина "Пятерочка" (5post.ru / x5.ru)
Использует BaseParser, Knowledge Base и Strategies.
"""

import asyncio
from typing import List, Optional
from playwright.async_api import Page, BrowserContext
from pydantic import BaseModel

from .base_parser import BaseParser, ParseResult
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy


class PyaterochkaProduct(BaseModel):
    """Модель продукта для Пятерочки (расширенная)"""
    name: str
    price: float
    old_price: Optional[float] = None
    unit_price: Optional[str] = None  # Цена за кг/л
    weight: Optional[str] = None
    image_url: Optional[str] = None
    link: str
    discount: Optional[int] = None  # Процент скидки
    stock_status: str = "in_stock"  # in_stock, out_of_stock, low_stock


class PyaterochkaParser(BaseParser):
    """
    Специфичный парсер для Пятерочки.
    
    Особенности:
    - Использует data-атрибуты (data-naive-props и др.)
    - Требует скроллинга для подгрузки товаров
    - Региональность через X-Region-Id (настраивается в KB)
    """

    def __init__(self, context: BrowserContext, shop_name: str = "pyaterochka"):
        super().__init__(context, shop_name)
        
        # Инициализация стратегий, специфичных для Пятерочки
        self.strategies.append(ScrollStrategy(delay=1.0, steps=5))
        self.strategies.append(LazyLoadStrategy(timeout=5000))

    async def parse_category(self, url: str, limit: int = 100) -> List[ParseResult]:
        """
        Парсинг категории товаров.
        """
        self.logger.info(f"Начало парсинга категории Пятерочка: {url}")
        
        try:
            # 1. Переход на страницу (с обработкой политик)
            await self.navigate(url)
            
            # 2. Применение стратегий (скролл, ожидание JS)
            await self.apply_strategies()
            
            # 3. Извлечение данных
            products = await self._extract_products(limit)
            
            self.logger.info(f"Извлечено {len(products)} товаров из {url}")
            return products
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге категории {url}: {e}")
            # Политика обработки ошибок сработает автоматически в navigate/execute
            raise

    async def _extract_products(self, limit: int) -> List[ParseResult]:
        """
        Внутренний метод извлечения товаров со страницы.
        Использует селекторы из Knowledge Base.
        """
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        
        # Получаем селекторы из KB (уже загружены в base_parser)
        selectors = self.kb_config.selectors
        
        # Ждем появления карточек товаров
        card_selector = selectors.get("product_card", {}).get("css")
        if not card_selector:
            raise ValueError("Селектор product_card не найден в KB для Пятерочки")
            
        try:
            await page.wait_for_selector(card_selector, timeout=10000)
        except Exception:
            self.logger.warning("Товары не найдены или страница не прогрузилась")
            return []

        # Скрипт извлечения данных внутри браузера
        extraction_script = """
        (selectors) => {
            const results = [];
            const cards = document.querySelectorAll(selectors.product_card);
            
            cards.forEach((card, index) => {
                if (results.length >= selectors.limit) return;

                // Хелпер для безопасного получения текста
                const getText = (selector) => {
                    const el = card.querySelector(selector);
                    return el ? el.innerText.trim() : null;
                };
                
                const getAttr = (selector, attr) => {
                    const el = card.querySelector(selector);
                    return el ? el.getAttribute(attr) : null;
                };

                // Название
                let name = getText(selectors.product_name);
                if (!name) name = getText(selectors.product_name_fallback);

                // Цена
                let priceStr = getText(selectors.price_current);
                if (!priceStr) priceStr = getText(selectors.price_current_fallback);
                const price = parseFloat(priceStr?.replace(/[^0-9.]/g, '') || '0');

                // Старая цена
                let oldPriceStr = getText(selectors.price_old);
                const old_price = oldPriceStr ? parseFloat(oldPriceStr.replace(/[^0-9.]/g, '')) : null;

                // Вес/Объем
                let weight = getText(selectors.weight_volume);
                if (!weight) weight = getText(selectors.weight_volume_fallback);

                // Ссылка
                let link = getAttr(selectors.product_link, 'href');
                if (link && !link.startsWith('http')) {
                    link = window.location.origin + link;
                }

                // Картинка
                let image = getAttr(selectors.image_url, 'src') || getAttr(selectors.image_url, 'data-src');

                // Скидка (бейдж)
                let discountBadge = getText(selectors.discount_badge);
                const discount = discountBadge ? parseInt(discountBadge.replace(/[^0-9]/g, '')) : null;

                if (name && price > 0) {
                    results.push({
                        name: name,
                        price: price,
                        old_price: old_price,
                        weight: weight,
                        link: link,
                        image_url: image,
                        discount: discount,
                        stock_status: "in_stock" // Упрощенно
                    });
                }
            });
            return results;
        }
        """
        
        raw_data = await page.evaluate(extraction_script, {
            **selectors,
            "limit": limit
        })
        
        # Преобразование в Pydantic модели
        results = []
        for item in raw_data:
            try:
                product = PyaterochkaProduct(**item)
                # Оборачиваем в стандартный ParseResult
                results.append(ParseResult(
                    raw_data=product.model_dump(),
                    parsed_data=product,
                    source_url=page.url,
                    timestamp=self.get_timestamp()
                ))
            except Exception as e:
                self.logger.warning(f"Не удалось валидировать товар: {e}, данные: {item}")
                
        return results

    async def check_availability(self, product_url: str) -> bool:
        """Проверка доступности конкретного товара (опционально)"""
        # Можно реализовать отдельную логику, если нужно заходить на карточку товара
        return True


# Точка входа для тестирования
if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright
    
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            parser = PyaterochkaParser(context)
            
            # Тестовая категория (рыба/морепродукты)
            test_url = "https://5post.ru/catalog/ryba_i_moreprodukty/" 
            # Примечание: URL может отличаться в зависимости от региона, проверить в KB
            
            try:
                results = await parser.parse_category(test_url, limit=10)
                print(f"\n✅ Найдено товаров: {len(results)}")
                for r in results[:3]:
                    print(f"- {r.parsed_data.name}: {r.parsed_data.price} ₽")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
            finally:
                await browser.close()

    asyncio.run(main())
