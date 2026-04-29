"""
Умный парсер Перекрестка - автоматически находит категории и фильтрует рыбу
"""
from typing import List, Optional, Set
import re
import asyncio
from bs4 import BeautifulSoup
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class PerekrestokParser(BaseParser):
    """Умный парсер для Перекрестка с авто-поиском категорий"""
    
    # Ключевые слова для определения рыбных товаров
    FISH_KEYWORDS = [
        'рыба', 'морепродукт', 'креветк', 'краб', 'крабов', 'икра', 'лосось', 
        'сельдь', 'скумбр', 'тунец', 'горбуш', 'семг', 'форел', 'минтай', 
        'треск', 'палтус', 'камбал', 'окунь', 'судак', 'щука', 'карп', 
        'толстолоб', 'осетр', 'стерляд', 'балык', 'копчен', 'солен', 
        'вялен', 'сушен', 'консерв', 'пресерв', 'кальмар', 'осьминог', 
        'мидия', 'устриц', 'гребешок', 'криль', 'анчоус', 'сардин', 
        'мойв', 'кильк', 'хамс', 'терпуг', 'наваг', 'пикш', 'сайда',
        'зубатк', 'угорь', 'мирог', 'дорад', 'сибас', 'пангасиус', 'тилапи',
        'оладь', 'котлет', 'стик', 'филе', 'балык', 'строган', 'кусочк'
    ]
    
    # Слова для исключения (не рыбные товары)
    EXCLUDE_KEYWORDS = [
        'корм', 'для живот', 'для кош', 'для соб', 'удобр', 'книг', 'игруш',
        'одежд', 'обув', 'быт', 'техник', 'электрон', 'мебель', 'посуд',
        'канцеляр', 'товары для дома', 'чистящ', 'моющ', 'шампун', 'гель',
        'мыло', 'зубн', 'щетк', 'памперс', 'подгуз', 'салфет', 'туалет',
        'бумаж', 'полотенц', 'пластыр', 'лекарств', 'витамин', 'БАД'
    ]
    
    def __init__(self, headless: bool = True):
        super().__init__("Перекресток", "https://perekrestok.ru", headless=headless)
        self.main_url = "https://perekrestok.ru"
        self.catalog_url = "https://perekrestok.ru/catalog"
        self.visited_urls: Set[str] = set()
        self.all_products: List[FishProduct] = []
    
    def get_category_urls(self) -> List[str]:
        """Возвращает основные URL (теперь используется авто-поиск)"""
        return [self.main_url, self.catalog_url]
    
    def _is_fish_product(self, name: str, description: str = "") -> bool:
        """Проверка, относится ли товар к рыбным/морепродуктам"""
        text = (name + " " + description).lower()
        
        # Сначала проверяем исключения
        for exclude in self.EXCLUDE_KEYWORDS:
            if exclude in text:
                return False
        
        # Затем проверяем включения
        for keyword in self.FISH_KEYWORDS:
            if keyword in text:
                return True
        
        return False
    
    def _extract_brand(self, name: str, card_html) -> str:
        """Извлечение бренда/производителя из карточки товара"""
        brand = ""
        
        # Пробуем найти бренд в специальных элементах
        brand_selectors = [
            '[class*="brand"]', '[class*="manufacturer"]', '[class*="producer"]',
            '[data-brand]', '[data-manufacturer]', '.product-brand', '.item-brand',
            '.manufacturer-name', '.producer-name', '.brand-name'
        ]
        
        for selector in brand_selectors:
            brand_elem = card_html.select_one(selector)
            if brand_elem:
                brand = self.clean_text(brand_elem.get_text())
                if brand:
                    return brand
        
        # Если не нашли, пробуем извлечь из названия (часто бренд в начале)
        # Паттерны: "Бренд Название", "Бренд - Название"
        patterns = [
            r'^([A-ZА-ЯЁ][a-zа-яё]+\s+[A-ZА-ЯЁ][a-zа-ё]+)\s+[-–—]?\s*',  # Два слова с заглавной
            r'^([A-ZА-ЯЁ][a-zа-яё]+)\s+[-–—]\s+',  # Одно слово до тире
            r'^([A-Z]{2,})\s+',  # Аббревиатура в начале
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                potential_brand = match.group(1).strip()
                # Проверяем, что это не просто часть названия
                if len(potential_brand) > 2 and potential_brand[0].isupper():
                    brand = potential_brand
                    break
        
        return brand
    
    def _extract_weight(self, card_html) -> str:
        """Извлечение веса/объема из карточки товара"""
        weight_selectors = [
            '[class*="weight"]', '[class*="volume"]', '[class*="mass"]',
            '[class*="size"]', '[data-weight]', '[data-volume]', '.product-weight',
            '.item-weight', '.weight-value', '.volume-value'
        ]
        
        for selector in weight_selectors:
            weight_elem = card_html.select_one(selector)
            if weight_elem:
                weight_text = self.clean_text(weight_elem.get_text())
                if weight_text and any(c.isdigit() for c in weight_text):
                    return weight_text
        
        # Пробуем найти вес в названии (паттерны: "100 г", "500 мл", "1 кг")
        if hasattr(card_html, 'select_one'):
            name_elem = card_html.select_one('h3, [class*="name"], [class*="title"]')
            if name_elem:
                name_text = name_elem.get_text()
                weight_pattern = r'(\d+\s*[гкммл]+\.?\d*)'
                match = re.search(weight_pattern, name_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return ""
    
    async def _parse_catalog_page(self, url: str) -> List[str]:
        """Парсинг страницы каталога для поиска подкатегорий"""
        subcategories = []
        
        html = await self.fetch_page_with_js(url)
        if not html:
            return subcategories
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Ищем ссылки на категории в меню каталога
        category_selectors = [
            'nav a[href*="/catalog/"]',
            '.catalog-menu a', '.menu-catalog a', '.sidebar a',
            '[class*="category"] a', '[class*="subcategory"] a',
            '.catalog-list a', '.rubric-list a', '.section-list a',
            'a[href*="/catalog/"]'
        ]
        
        seen_links: Set[str] = set()
        for selector in category_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if href and href.startswith('/') and '/catalog/' in href:
                    full_url = f"https://perekrestok.ru{href}"
                    if full_url not in seen_links and full_url not in self.visited_urls:
                        seen_links.add(full_url)
                        # Проверяем, что ссылка ведет на категорию, а не на товар
                        if not re.search(r'/product/\d+', href):
                            subcategories.append(full_url)
                            logger.debug(f"Найдена категория: {full_url}")
        
        return subcategories
    
    async def _parse_products_from_page(self, url: str, html: str) -> int:
        """Парсинг товаров со страницы каталога"""
        count = 0
        soup = BeautifulSoup(html, 'lxml')
        
        # Различные селекторы для карточек товаров
        card_selectors = [
            'div[class*="product-card"]',
            'div[class*="ProductCard"]',
            'article[class*="product"]',
            'div[data-product-id]',
            'div[class*="catalog-item"]',
            'div[class*="good-item"]',
            'li[class*="product"]',
            '.product-item', '.good-item', '.catalog-item'
        ]
        
        product_cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                product_cards.extend(cards[:100])  # Ограничиваем количество
                break
        
        # Если не нашли по селекторам, пробуем найти все элементы с ценами
        if not product_cards:
            price_elements = soup.select('[class*="price"], [data-price]')
            for elem in price_elements:
                parent = elem.find_parent(['div', 'article', 'li'])
                if parent and parent not in product_cards:
                    product_cards.append(parent)
        
        logger.debug(f"Найдено потенциальных карточек товаров: {len(product_cards)}")
        
        for card in product_cards:
            try:
                # Извлекаем название
                name_elem = (
                    card.select_one('h3') or
                    card.select_one('[class*="name"]') or
                    card.select_one('[class*="title"]') or
                    card.select_one('a[href*="/product/"]') or
                    card.select_one('[data-name]')
                )
                
                if not name_elem:
                    continue
                
                name = self.clean_text(name_elem.get_text())
                if len(name) < 3:
                    continue
                
                # Проверяем, рыбный ли это товар
                if not self._is_fish_product(name):
                    continue
                
                # Извлекаем цену
                price_elem = (
                    card.select_one('[class*="price"]') or
                    card.select_one('[class*="cost"]') or
                    card.select_one('[data-price]') or
                    card.select_one('.price-value') or
                    card.select_one('.current-price')
                )
                
                if not price_elem:
                    continue
                
                price = self.clean_price(price_elem.get_text())
                if not price or price <= 0:
                    continue
                
                # Извлекаем ссылку
                link_elem = card.select_one('a[href*="/product/"]')
                url_prod = link_elem.get('href', '') if link_elem else ''
                
                if not url_prod.startswith('http'):
                    url_prod = f"https://perekrestok.ru{url_prod}" if url_prod else url
                
                # Извлекаем бренд и вес
                brand = self._extract_brand(name, card)
                weight = self._extract_weight(card)
                
                # Создаем продукт
                product = FishProduct(
                    name=name,
                    price=price,
                    store=self.store_name,
                    url=url_prod,
                    category="рыба/морепродукты",
                    brand=brand,
                    weight=weight
                )
                
                self.all_products.append(product)
                count += 1
                
            except Exception as e:
                logger.debug(f"Ошибка при парсинге карточки: {e}")
                continue
        
        return count
    
    async def _scroll_and_load_all(self, page):
        """Прокрутка страницы для загрузки всех товаров (для lazy loading)"""
        try:
            previous_height = await page.evaluate('document.body.scrollHeight')
            
            for i in range(5):  # Максимум 5 прокруток
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)  # Ждем подгрузки
                
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == previous_height:
                    break
                previous_height = new_height
            
            # Возвращаемся вверх
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"Ошибка при прокрутке страницы: {e}")
    
    async def parse_fish_products(self) -> List[FishProduct]:
        """Основной метод парсинга - авто-поиск категорий и товаров"""
        logger.info("🔍 Начинаю автоматический поиск категорий с рыбой и морепродуктами...")
        
        self.all_products = []
        self.visited_urls = set()
        
        # Запускаем браузер
        if not await self.start_browser():
            logger.error("Не удалось запустить браузер")
            return []
        
        try:
            assert self.page is not None
            
            # Шаг 1: Заходим на главную и ищем каталог
            logger.info(f"📂 Переход на главную страницу: {self.main_url}")
            await self.page.goto(self.main_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            
            # Делаем скриншот для отладки
            await self.screenshot("debug_main_page.png")
            
            # Шаг 2: Ищем ссылку на каталог или сразу переходим в каталог
            catalog_links = [
                self.catalog_url,
                "https://perekrestok.ru/catalog",
                "https://perekrestok.ru/katalog"
            ]
            
            categories_to_visit = [self.catalog_url]
            
            # Шаг 3: Рекурсивный обход категорий
            visited_categories: Set[str] = set()
            queue = categories_to_visit.copy()
            
            iteration = 0
            max_iterations = 50  # Ограничение на количество категорий
            
            while queue and iteration < max_iterations:
                iteration += 1
                current_url = queue.pop(0)
                
                if current_url in visited_categories:
                    continue
                
                visited_categories.add(current_url)
                self.visited_urls.add(current_url)
                
                logger.info(f"[{iteration}/{max_iterations}] Обработка категории: {current_url}")
                
                # Загружаем страницу категории
                try:
                    await self.page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)
                    
                    # Прокручиваем для lazy loading
                    await self._scroll_and_load_all(self.page)
                    await asyncio.sleep(2)
                    
                    # Получаем HTML
                    html = await self.page.content()
                    
                    # Парсим товары на этой странице
                    found_count = await self._parse_products_from_page(current_url, html)
                    if found_count > 0:
                        logger.info(f"✅ Найдено {found_count} рыбных товаров в категории")
                    
                    # Ищем подкатегории на этой странице
                    subcategories = await self._parse_catalog_page(current_url)
                    
                    for subcat in subcategories:
                        if subcat not in visited_categories:
                            queue.append(subcat)
                            logger.debug(f"➕ Добавлена подкатегория в очередь: {subcat}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке {current_url}: {e}")
                    continue
                
                # Небольшая пауза между категориями
                await asyncio.sleep(2)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 Всего найдено рыбных товаров в Перекрестке: {len(self.all_products)}")
            logger.info(f"📂 Обработано категорий: {len(visited_categories)}")
            logger.info(f"{'='*60}\n")
            
            # Выводим статистику по брендам
            if self.all_products:
                brands_count = {}
                for prod in self.all_products:
                    brand = prod.brand if prod.brand else "Без бренда"
                    brands_count[brand] = brands_count.get(brand, 0) + 1
                
                logger.info("🏷️ Топ производителей:")
                sorted_brands = sorted(brands_count.items(), key=lambda x: x[1], reverse=True)[:10]
                for brand, count in sorted_brands:
                    logger.info(f"   {brand}: {count} товаров")
            
            return self.all_products
            
        finally:
            await self.close()
