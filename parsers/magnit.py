"""
Парсер для магазина "Магнит"
Использует данные из knowledge_base/magnit.md
"""
import asyncio
import re
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, BrowserContext
from loguru import logger

from .base_parser import BaseParser
from models.schemas import Product as ProductItem
from strategies.scroll_strategy import ScrollStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy


class MagnitProduct(ProductItem):
    """Модель продукта для Магнита с расширенными полями"""
    pass


class MagnitParser(BaseParser):
    """
    Парсер для сайта Магнит (magnit.ru)
    Особенности:
    - Требуется заголовок X-City-Id (берется из KB/конфига)
    - Защита: reCAPTCHA v2 (требуется стратегия обхода или ручное решение)
    - Селекторы: специфичные классы .products-grid__item
    """

    def __init__(self, config_path: str = "knowledge_base/magnit.md"):
        super().__init__(config_path=config_path)
        self.shop_name = "magnit"
        
        # Инициализация стратегий
        self.scroll_strategy = ScrollStrategy(
            scroll_step=500,
            delay_range=(1.0, 2.5),
            max_retries=3
        )
        self.lazy_load_strategy = LazyLoadStrategy(
            timeout=5000,
            check_interval=1000
        )

    async def navigate_to_category(self, page: Page, category_url: str) -> bool:
        """Переход к категории с применением хедеров из KB"""
        logger.info(f"[{self.shop_name}] Переход к категории: {category_url}")
        
        # Применяем специфичные заголовки из Knowledge Base
        headers = self.kb.headers.standard
        custom_headers = self.kb.headers.custom
        
        # Для Magnit критичен X-City-Id (если есть в custom headers)
        if custom_headers.get("X-City-Id"):
            await page.set_extra_http_headers(custom_headers)
            logger.debug(f"[{self.shop_name}] Установлены кастомные заголовки: {custom_headers}")

        try:
            await page.goto(category_url, wait_until="domcontentloaded", timeout=30000)
            
            # Проверка на капчу или блокировку
            if await self.is_blocked(page):
                logger.error(f"[{self.shop_name}] Обнаружена блокировка или капча при переходе")
                return False
                
            return True
        except Exception as e:
            logger.error(f"[{self.shop_name}] Ошибка перехода: {e}")
            return False

    async def is_blocked(self, page: Page) -> bool:
        """Проверка на наличие капчи или страницы блокировки"""
        block_indicators = [
            "iframe[src*='recaptcha']",
            ".captcha-container",
            "text=Access Denied",
            "text=Проверка безопасности"
        ]
        
        for selector in block_indicators:
            try:
                if selector.startswith("text="):
                    text = selector.replace("text=", "")
                    if await page.locator(f"text={text}").count() > 0:
                        return True
                else:
                    if await page.locator(selector).count() > 0:
                        return True
            except:
                continue
        return False

    async def parse_category(self, page: Page, category_url: str) -> List[MagnitProduct]:
        """Основной метод парсинга категории"""
        products = []
        
        # 1. Навигация
        if not await self.navigate_to_category(page, category_url):
            return products

        # 2. Применение стратегий (скролл и ленивая загрузка)
        logger.info(f"[{self.shop_name}] Запуск стратегий подгрузки...")
        await self.scroll_strategy.execute(page)
        await self.lazy_load_strategy.execute(page)
        
        # Пауза после скролла для стабилизации DOM
        await asyncio.sleep(2)

        # 3. Извлечение данных
        selectors = self.kb.selectors
        card_selector = selectors.product_card
        
        if not card_selector:
            logger.error(f"[{self.shop_name}] Не найден селектор карточки товара в KB")
            return products

        logger.info(f"[{self.shop_name}] Поиск товаров по селектору: {card_selector}")
        
        try:
            cards = await page.query_selector_all(card_selector)
            logger.info(f"[{self.shop_name}] Найдено элементов: {len(cards)}")
            
            for index, card in enumerate(cards):
                try:
                    product = await self._parse_product_card(card, selectors, index)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"[{self.shop_name}] Ошибка парсинга карточки #{index}: {e}")
                    
        except Exception as e:
            logger.error(f"[{self.shop_name}] Критическая ошибка при поиске карточек: {e}")

        logger.success(f"[{self.shop_name}] Спарсено {len(products)} товаров")
        return products

    async def _parse_product_card(self, card: Any, selectors: Any, index: int) -> Optional[MagnitProduct]:
        """Парсинг отдельной карточки товара"""
        try:
            # Извлечение данных с использованием JS для надежности
            data = await card.evaluate("""
                (el, selectors) => {
                    const getText = (selector) => {
                        if (!selector) return null;
                        const node = el.querySelector(selector);
                        return node ? node.innerText.trim() : null;
                    };
                    
                    const getAttr = (selector, attr) => {
                        if (!selector) return null;
                        const node = el.querySelector(selector);
                        return node ? node.getAttribute(attr) : null;
                    };

                    // Попытка найти цену (текущую)
                    let price = getText(selectors.price_current);
                    if (!price) {
                        // Fallback: поиск по классам цены
                        const priceNodes = el.querySelectorAll('[class*="price"], [class*="cost"]');
                        for (let node of priceNodes) {
                            if (node.innerText && !node.innerText.includes('старая')) {
                                price = node.innerText.trim();
                                break;
                            }
                        }
                    }

                    // Очистка цены от валюты и пробелов
                    let cleanPrice = null;
                    if (price) {
                        const match = price.replace(/\s/g, '').match(/\d+/);
                        if (match) cleanPrice = parseInt(match[0], 10);
                    }

                    // Ссылка
                    let link = getAttr(selectors.product_link, 'href');
                    if (!link) {
                        const linkNode = el.querySelector('a');
                        if (linkNode) link = linkNode.getAttribute('href');
                    }
                    if (link && !link.startsWith('http')) {
                        link = 'https://magnit.ru' + link;
                    }

                    // Картинка
                    let image = getAttr(selectors.image_url, 'src') || getAttr('img', 'src');
                    if (image && image.startsWith('//')) {
                        image = 'https:' + image;
                    }

                    return {
                        name: getText(selectors.product_name),
                        price: cleanPrice,
                        old_price: null,
                        weight: getText(selectors.weight_volume),
                        image: image,
                        link: link,
                        brand: null
                    };
                }
            """, selectors)

            # Валидация через Pydantic
            if not data.get('name') or not data.get('price'):
                return None

            return MagnitProduct(
                shop=self.shop_name,
                name=data['name'],
                price=data['price'],
                old_price=data.get('old_price'),
                weight=data.get('weight'),
                image_url=data.get('image'),
                product_url=data.get('link'),
                category_url="",
                parsed_at=None
            )

        except Exception as e:
            logger.debug(f"[{self.shop_name}] Ошибка извлечения данных карточки: {e}")
            return None

    async def handle_captcha(self, page: Page) -> bool:
        """Обработка reCAPTCHA v2"""
        logger.warning(f"[{self.shop_name}] Требуется решение капчи!")
        logger.info(f"[{self.shop_name}] Ожидание решения капчи пользователем (30 сек)...")
        await asyncio.sleep(30)
        
        if await self.is_blocked(page):
            logger.error(f"[{self.shop_name}] Капча не решена")
            return False
        return True


# Точка входа для тестирования
if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright

    async def main():
        parser = MagnitParser()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            test_url = "https://magnit.ru/catalog/ryba_i_moreprodukty/"
            
            products = await parser.parse_category(page, test_url)
            
            print(f"\n=== Найдено товаров: {len(products)} ===")
            for p in products[:5]:
                print(f"- {p.name}: {p.price} руб.")
                
            await browser.close()

    asyncio.run(main())
