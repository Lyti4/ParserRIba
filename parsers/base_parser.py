"""
Современный базовый парсер с интеграцией Knowledge Base, стратегий и политик.
Заменяет устаревший base_parser.py
"""
import asyncio
import random
import logging
from typing import Optional, List, Dict, Any, Type
from datetime import datetime
from curl_cffi import requests as curl_requests
from loguru import logger
from functools import wraps
from pathlib import Path

from models.schemas import Product, ProductPrice, ProductDimensions, ParseResult, CategoryInfo
from utils.kb_loader import KBLoader, ShopKnowledge
from strategies.base_strategy import BaseStrategy as Strategy
from strategies.scroll_strategy import ScrollStrategy
from strategies.pagination_strategy import PaginationStrategy
from strategies.lazy_load_strategy import LazyLoadStrategy
from policies.engine import PoliciesEngine as PolicyEngine


class BaseParser:
    """
    Базовый класс парсера с динамической загрузкой конфигурации из Knowledge Base.
    
    Особенности:
    - Автоматическая загрузка селекторов и headers из MD файлов
    - Интеграция со стратегиями (скролл, пагинация, lazy load)
    - Автоматическая обработка ошибок через Policy Engine
    - Поддержка curl-cffi (основной) и Playwright (резерв)
    """
    
    def __init__(self, shop_name: str, region: str = "77", headless: bool = True):
        """
        Инициализация парсера.
        
        Args:
            shop_name: Название магазина (pyaterochka, magnit, lenta, auchan, okey, perekrestok)
            region: Регион для X-Region header (по умолчанию Москва - 77)
            headless: Режим браузера для Playwright
        """
        self.shop_name = shop_name.lower()
        self.region = region
        self.headless = headless
        
        # Загрузка Knowledge Base
        self.kb_loader = KBLoader()
        self.kb: Optional[ShopKnowledge] = None
        self._load_knowledge_base()
        
        # Сессия curl-cffi
        self.session = curl_requests.Session()
        
        # Playwright атрибуты (ленивая инициализация)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        
        # Camoufox атрибуты
        self._camoufox_browser = None
        
        # Стратегии
        self.strategies: List[Strategy] = []
        self._init_strategies()
        
        # Policy Engine
        self.policy_engine = PolicyEngine()
        self._init_policies()
        
        logger.info(f"🚀 Парсер {self.shop_name} инициализирован")
        if self.kb:
            logger.info(f"   📚 Загружено {len(self.kb.categories)} категорий, {len(self.kb.selectors)} селекторов")
    
    def _load_knowledge_base(self):
        """Загрузка конфигурации из Knowledge Base"""
        try:
            self.kb = self.kb_loader.load_shop(self.shop_name)
            logger.debug(f"KB загружен для {self.shop_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки KB для {self.shop_name}: {e}")
            raise
    
    def _init_strategies(self):
        """Инициализация стратегий на основе KB"""
        # Стратегии инициализируются позже, когда есть страница
        self.strategies: List[Strategy] = []
        self._strategies_config = {}  # Сохраняем конфигурацию для последующего применения
        
        if not self.kb:
            return
        
        # Сохраняем конфигурацию стратегий из KB
        strategies = getattr(self.kb.anti_bot, 'strategies', []) or []
        self._strategies_config = {
            'scrolling': 'scrolling' in strategies,
            'pagination': 'pagination' in strategies,
            'lazy_load': 'lazy_load' in strategies
        }
        logger.debug(f"Конфигурация стратегий: {self._strategies_config}")
    
    def _init_policies(self):
        """Инициализация политик обработки ошибок"""
        # Политика для 403 ошибки уже есть в DEFAULT_POLICIES
        
        # Политика для CAPTCHA
        captcha_types = getattr(self.kb.anti_bot, 'captcha_types', []) if self.kb else []
        if captcha_types:
            from policies.engine import PolicyRule, ErrorType, ActionType
            self.policy_engine.add_policy(PolicyRule(
                error_types=[ErrorType.CAPTCHA],
                actions=[ActionType.SWITCH_TO_PLAYWRIGHT, ActionType.WAIT_AND_RETRY],
                max_retries=1,
                delay_between_retries=5.0,
                priority=15
            ))
        
        # Политика для таймаута уже есть в DEFAULT_POLICIES
    
    def _get_headers(self) -> dict:
        """Получение headers из Knowledge Base"""
        if not self.kb:
            return self._get_default_headers()
        
        headers = self._get_default_headers()
        
        # Добавляем custom headers из KB
        custom_headers = self.kb.headers.custom if self.kb.headers else {}
        for key, value in custom_headers.items():
            if value == "required":
                # Подставляем значения по умолчанию
                if "Region" in key:
                    headers[f"X-{key}"] = self.region
                elif "Store" in key or "Shop" in key:
                    headers[f"X-{key}"] = "1"  # Дефолтный магазин
                elif "Client" in key:
                    headers[f"X-{key}"] = "web-client"
            else:
                headers[f"X-{key}"] = str(value)
        
        return headers
    
    def _get_default_headers(self) -> dict:
        """Базовые headers"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }
    
    def get_selector(self, selector_type: str) -> Optional[str]:
        """
        Получение селектора из Knowledge Base.
        
        Args:
            selector_type: Тип селектора (product_card, product_name, price_current, etc.)
        
        Returns:
            CSS селектор или None
        """
        if not self.kb:
            return None
        
        selectors = self.kb.selectors
        selector_config = selectors.get(selector_type)
        if selector_config:
            return selector_config.css or selector_config.xpath
        return None
    
    async def start_browser(self, use_camoufox: bool = True, geoip: bool = False, 
                           block_images: bool = True, block_webgl: bool = False,
                           addons: Optional[List[str]] = None, headless: str = "virtual",
                           humanize: bool = True):
        """
        Запуск браузера Camoufox (основной) или Playwright (резерв).
        
        Args:
            use_camoufox: Использовать Camoufox вместо Playwright
            geoip: Согласовать регион с прокси (GeoIP)
            block_images: Блокировать загрузку изображений
            block_webgl: Блокировать WebGL
            addons: Список аддонов для установки (например, uBlock)
            headless: Режим запуска ("virtual", True, False)
            humanize: Гуманизировать движения курсора (только Camoufox)
        """
        if use_camoufox:
            return await self._start_camoufox(
                geoip=geoip,
                block_images=block_images,
                block_webgl=block_webgl,
                addons=addons,
                headless=headless,
                humanize=humanize
            )
        else:
            return await self._start_playwright()
    
    async def _start_camoufox(self, geoip: bool = False, block_images: bool = True,
                              block_webgl: bool = False, addons: Optional[List[str]] = None,
                              headless: str = "virtual", humanize: bool = True,
                              webgl_config: Optional[tuple] = None,
                              os_type: Optional[str] = None,
                              disable_coop: bool = True):
        """Запуск Camoufox с расширенными настройками stealth.
        
        Args:
            geoip: Использовать GeoIP для определения локации
            block_images: Блокировать изображения
            block_webgl: Блокировать WebGL
            addons: Список аддонов (пути к XPI файлам)
            headless: Режим запуска ("virtual", True, False)
                     - "virtual": использовать виртуальный дисплей (Xvfb) на Linux
                     - True: headless режим без GUI
                     - False: обычный режим с окном
            humanize: Гуманизировать движения курсора
            webgl_config: Кортеж (vendor, renderer) для WebGL spoofing
            os_type: Тип ОС для fingerprint (windows, macos, linux)
            disable_coop: Отключить Cross-Origin-Opener-Policy
        """
        try:
            from camoufox import AsyncCamoufox
            import platform
            
            # Определение ОС для корректной настройки headless
            system = platform.system()
            
            # На Windows "virtual" headless не поддерживается, используем обычный булевый флаг
            if system == "Windows" and headless == "virtual":
                effective_headless = False  # Окно браузера для Windows (чтобы видеть процесс)
                logger.info(f"🪟 Обнаружена Windows: virtual display заменен на headless={effective_headless} (видимый режим)")
            else:
                effective_headless = headless
            
            logger.info(f"🦊 Запуск Camoufox (OS={system}, headless={effective_headless}, geoip={geoip}, humanize={humanize})...")
            
            # Подготовка параметров для Camoufox launch_options()
            launch_kwargs = {
                "block_images": block_images,
                "block_webgl": block_webgl,
                "humanize": humanize,
                "disable_coop": disable_coop,
                "headless": effective_headless,
                "fingerprint": True,  # Включаем автоматический fingerprinting
                "i_know_what_im_doing": True,  # Отключаем предупреждения о безопасности
            }
            
            # GeoIP если включён
            if geoip:
                launch_kwargs["geoip"] = True
            
            # Добавляем аддоны если указаны
            if addons:
                launch_kwargs["addons"] = addons
            
            # WebGL конфигурация если передана (vendor, renderer)
            if webgl_config and isinstance(webgl_config, tuple) and len(webgl_config) == 2:
                launch_kwargs["webgl_config"] = webgl_config
                # Для webgl_config нужно указать OS
                if os_type:
                    launch_kwargs["os"] = os_type
            
            # Тип ОС для fingerprint (если не задан явно, можно определить автоматически)
            if os_type:
                launch_kwargs["os"] = os_type
            
            # Создаём браузер с параметрами
            self._camoufox_browser = AsyncCamoufox(**launch_kwargs)
            
            # Входим в контекст менеджера
            await self._camoufox_browser.__aenter__()
            
            # Создаём новую страницу
            browser = self._camoufox_browser.browser
            self._page = await browser.new_page()
            
            logger.info("✅ Camoufox запущен успешно")
            
        except ImportError as e:
            logger.warning(f"⚠️ Camoufox не установлен, пробуем Playwright: {e}")
            return await self._start_playwright()
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Camoufox: {e}")
            raise
    
    async def _start_playwright(self):
        """Запуск браузера Playwright (резервный режим)."""
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import stealth_async
            
            logger.info(f"🌐 Запуск браузера Playwright ({'невидимый' if self.headless else 'видимый'})...")
            
            self._playwright = await async_playwright().start()
            
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
            
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=args
            )
            
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            self._page = await self._context.new_page()
            
            # Применение stealth
            await stealth_async(self._page)
            
            # Маскировка webdriver
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
            """)
            
            logger.info("✅ Браузер Playwright запущен успешно")
            
        except ImportError:
            logger.warning("⚠️ Playwright не установлен, используем curl-cffi")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска браузера: {e}")
            raise
    
    async def close_browser(self):
        """Закрытие браузера"""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            if self._camoufox_browser:
                await self._camoufox_browser.__aexit__(None, None, None)
            logger.info("🛑 Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")
    
    async def close(self):
        """Алиас для close_browser"""
        await self.close_browser()
    
    async def fetch_page(self, url: str, use_impersonate: str = 'chrome124') -> Optional[str]:
        """Загрузка страницы через curl-cffi с использованием KB"""
        try:
            headers = self._get_headers()
            
            # Динамический выбор профиля на основе KB
            if self.kb and getattr(self.kb, 'recommended_tool', None) == "curl_cffi":
                use_impersonate = getattr(self.kb.anti_bot, 'recommended_impersonate', 'chrome124') or 'chrome124'
            
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=45,
                impersonate=use_impersonate,
                allow_redirects=True, 
                verify=False
            )
            
            # Обработка ответов через Policy Engine
            context = {
                "url": url,
                "status_code": response.status_code,
                "response_text": response.text[:500] if response.text else ""
            }
            
            if response.status_code == 403:
                logger.warning(f"⚠️ Защита (403) на {url}")
                action = await self.policy_engine.evaluate(context)
                if action == "rotate_proxy_and_retry":
                    # TODO: Реализовать ротацию прокси
                    logger.info("🔄 Попытка ротации прокси...")
                    return await self.fetch_page(url, use_impersonate)
                return None
            
            if response.status_code == 401:
                # Попытка добавить регион
                headers['X-Region'] = self.region
                response = self.session.get(url, headers=headers, timeout=30, impersonate=use_impersonate, verify=False)
            
            return response.text if response.status_code == 200 else None
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return None
    
    async def fetch_page_playwright(self, url: str, wait_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """Загрузка через Playwright (для JS сайтов)"""
        try:
            if not self._page:
                await self.start_browser()
            
            logger.info(f"🔗 Запрос к {url} через Playwright...")
            
            # Случайная задержка перед запросом
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            if wait_selector:
                await self._page.wait_for_selector(wait_selector, timeout=timeout)
            
            # Применение стратегий
            for strategy in self.strategies:
                await strategy.apply(self._page)
            
            # Дополнительная задержка после загрузки
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            content = await self._page.content()
            logger.info(f"✅ Страница загружена успешно")
            return content
            
        except Exception as e:
            logger.error(f"❌ Ошибка Playwright запроса: {e}")
            # Фоллбэк на curl-cffi
            return await self.fetch_page(url)
    
    def parse_product_card(self, element: Any) -> Optional[Product]:
        """
        Парсинг карточки товара с использованием селекторов из KB.
        
        Args:
            element: HTML элемент карточки товара
        
        Returns:
            Product модель или None
        """
        if not self.kb:
            return None
        
        try:
            # Извлечение данных с использованием селекторов из KB
            name_selector = self.get_selector("product_name")
            price_selector = self.get_selector("price_current")
            
            # TODO: Реализовать парсинг с BeautifulSoup или lxml
            # Это заглушка для демонстрации структуры
            
            return Product(
                id="temp_id",
                name="Temp Product",
                price=ProductPrice(current=0.0),
                category="Fish",
                product_url="https://example.com",
                shop=self.shop_name
            )
        except Exception as e:
            logger.error(f"Ошибка парсинга карточки товара: {e}")
            return None
    
    async def parse_category(self, category_url: str, category_name: str = "Unknown") -> ParseResult:
        """
        Парсинг категории товаров.
        
        Args:
            category_url: URL категории
            category_name: Имя категории для логирования
        
        Returns:
            ParseResult с списком товаров
        """
        start_time = datetime.now()
        errors = []
        warnings = []
        
        # Определение инструмента для парсинга
        use_playwright = (
            self.kb and 
            getattr(self.kb, 'recommended_tool', None) == "playwright"
        ) or (
            self.kb and 
            getattr(self.kb.anti_bot, 'requires_js', False)
        )
        
        # Если браузер еще не запущен и нужен Playwright/Camoufox - запускаем
        if use_playwright and not self._page:
            logger.info("🌐 Браузер не был запущен, запускаем сейчас...")
            await self.start_browser(use_camoufox=True, headless=False)
            await asyncio.sleep(2)
        
        # Загрузка страницы с применением региональных заголовков
        if use_playwright:
            await self._apply_regional_headers_to_page()
            
            # Переход на страницу
            logger.info(f"🔗 Переход на страницу категории: {category_url}")
            try:
                response = await self._page.goto(category_url, wait_until="domcontentloaded", timeout=45000)
                
                # Дополнительное ожидание загрузки контента
                await asyncio.sleep(3)
                
                # Применяем стратегию скроллинга если включена
                if self._strategies_config.get('scrolling'):
                    logger.info("📜 Выполняем скроллинг страницы для загрузки контента...")
                    await self._execute_scrolling()
                
                html = await self._page.content()
                
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки страницы: {e}")
                errors.append(f"Не удалось загрузить страницу {category_url}: {e}")
                return ParseResult(
                    shop=self.shop_name,
                    category=CategoryInfo(name=category_name, url=category_url),
                    products=[],
                    total_products=0,
                    errors=errors,
                    warnings=warnings
                )
        else:
            self._apply_regional_headers_to_session()
            html = await self.fetch_page(category_url)
        
        if not html:
            errors.append(f"Не удалось загрузить страницу {category_url}")
            return ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(name=category_name, url=category_url),
                products=[],
                total_products=0,
                errors=errors,
                warnings=warnings
            )
        
        # Парсинг товаров
        products = []
        if use_playwright:
            products = await self._parse_products_from_page(category_name)
        else:
            # TODO: Реализовать парсинг для curl-cffi
            logger.warning("Парсинг через curl-cffi пока не реализован")
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"✅ Категория {category_name}: найдено {len(products)} товаров за {duration_ms}мс")
        
        return ParseResult(
            shop=self.shop_name,
            category=CategoryInfo(name=category_name, url=category_url),
            products=products,
            total_products=len(products),
            errors=errors,
            warnings=warnings,
            parse_duration_ms=duration_ms
        )
    
    async def _execute_scrolling(self):
        """Выполнение скроллинга страницы для подгрузки контента"""
        try:
            # Получаем высоту страницы
            scroll_height = await self._page.evaluate("document.body.scrollHeight")
            
            # Скроллим несколько раз с паузами
            for i in range(3):
                # Скроллим на 1/3 высоты
                scroll_position = int(scroll_height * (i + 1) / 3)
                await self._page.evaluate(f"window.scrollTo(0, {scroll_position})")
                await asyncio.sleep(1.5)  # Ждем подгрузки контента
            
            # Возвращаемся вверх
            await self._page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            logger.debug("✅ Скроллинг завершен")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при скроллинге: {e}")
    
    async def _parse_products_from_page(self, category_name: str) -> List[Product]:
        """Парсинг товаров со страницы"""
        if not self._page or not self.kb:
            return []
        
        products = []
        
        try:
            # Получаем селектор карточки товара из KB (список селекторов)
            card_selectors = self.kb.selectors.get("product_card") if self.kb and self.kb.selectors else []
            
            if not card_selectors:
                logger.warning("⚠️ Селектор product_card не найден в KB")
                return []
            
            # Преобразуем в список CSS селекторов
            selectors_list = []
            if hasattr(card_selectors, '__iter__') and not isinstance(card_selectors, str):
                # Это список объектов SelectorConfig
                for sel in card_selectors:
                    if hasattr(sel, 'css') and sel.css:
                        selectors_list.append(sel.css)
            elif isinstance(card_selectors, str):
                # Это строка (один селектор)
                selectors_list.append(card_selectors)
            
            if not selectors_list:
                logger.warning("⚠️ Нет валидных CSS селекторов для product_card")
                return []
            
            # Пробуем каждый селектор по очереди
            product_cards = []
            for card_selector in selectors_list:
                try:
                    product_cards = await self._page.query_selector_all(card_selector)
                    if product_cards:
                        logger.info(f"🛒 Найдено {len(product_cards)} карточек товаров по селектору: {card_selector}")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Селектор '{card_selector}' не сработал: {e}")
                    continue
            
            if not product_cards:
                logger.warning("⚠️ Не найдено товаров ни по одному из селекторов")
                return []
            
            
            # Парсим каждую карточку
            for idx, card in enumerate(product_cards):
                try:
                    product = await self._parse_product_card(card, category_name, idx)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.debug(f"⚠️ Ошибка парсинга карточки #{idx}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге товаров: {e}")
        
        return products
    
    async def _parse_product_card(self, card_element, category_name: str, index: int) -> Optional[Product]:
        """Парсинг отдельной карточки товара"""
        try:
            # Извлекаем данные с использованием селекторов из KB
            name_selector = self.get_selector("product_name")
            price_selector = self.get_selector("price_current")
            old_price_selector = self.get_selector("price_old")
            discount_selector = self.get_selector("discount")
            image_selector = self.get_selector("product_image")
            link_selector = self.get_selector("product_link")
            
            # Извлечение имени
            name = None
            if name_selector:
                name_elem = await card_element.query_selector(name_selector)
                if name_elem:
                    name = await name_elem.inner_text()
                    name = name.strip() if name else None
            
            # Извлечение цены
            current_price = 0.0
            if price_selector:
                price_elem = await card_element.query_selector(price_selector)
                if price_elem:
                    price_text = await price_elem.inner_text()
                    # Очищаем от символов валюты и пробелов
                    price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
                    if price_text:
                        current_price = float(price_text)
            
            # Извлечение старой цены
            old_price = None
            if old_price_selector:
                old_price_elem = await card_element.query_selector(old_price_selector)
                if old_price_elem:
                    old_price_text = await old_price_elem.inner_text()
                    old_price_text = ''.join(c for c in old_price_text if c.isdigit() or c == '.')
                    if old_price_text:
                        old_price = float(old_price_text)
            
            # Извлечение скидки
            discount = None
            if discount_selector:
                discount_elem = await card_element.query_selector(discount_selector)
                if discount_elem:
                    discount_text = await discount_elem.inner_text()
                    discount_text = ''.join(c for c in discount_text if c.isdigit())
                    if discount_text:
                        discount = int(discount_text)
            
            # Извлечение ссылки
            product_url = None
            if link_selector:
                link_elem = await card_element.query_selector(link_selector)
                if link_elem:
                    product_url = await link_elem.get_attribute('href')
                    # Если относительный URL, делаем абсолютным
                    if product_url and not product_url.startswith('http'):
                        base_url = self.kb.base_url if self.kb else ""
                        product_url = base_url.rstrip('/') + '/' + product_url.lstrip('/')
            
            # Извлечение изображения
            image_url = None
            if image_selector:
                img_elem = await card_element.query_selector(image_selector)
                if img_elem:
                    image_url = await img_elem.get_attribute('src')
                    # Если относительный URL, делаем абсолютным
                    if image_url and not image_url.startswith('http'):
                        base_url = self.kb.base_url if self.kb else ""
                        image_url = base_url.rstrip('/') + '/' + image_url.lstrip('/')
            
            # Генерируем ID если нет
            product_id = f"{self.shop_name}_{category_name}_{index}"
            
            if not name:
                name = f"Товар #{index}"
            
            return Product(
                id=product_id,
                name=name,
                price=ProductPrice(current=current_price, old=old_price, discount=discount),
                category=category_name,
                product_url=product_url or "",
                shop=self.shop_name,
                image_url=image_url
            )
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка парсинга карточки товара: {e}")
            return None
    
    def _apply_regional_headers_to_session(self):
        """Применение региональных заголовков к сессии curl-cffi"""
        if not self.kb or not self.kb.headers:
            return
        
        custom_headers = self.kb.headers.custom if self.kb.headers else {}
        for header, value in custom_headers.items():
            # Подстановка региона если требуется
            if value == "required" and header in ["X-Region", "X-Region-Id"]:
                self.session.headers[header] = self.region
            elif value != "required":
                self.session.headers[header] = value
        
        logger.debug(f"Применены заголовки: {list(custom_headers.keys())}")

    async def _apply_regional_headers_to_page(self):
        """Применение региональных заголовков к странице Playwright"""
        if not self.kb or not self.kb.headers:
            return
        
        custom_headers = self.kb.headers.custom if self.kb.headers else {}
        headers_to_set = {}
        
        for header, value in custom_headers.items():
            if value == "required" and header in ["X-Region", "X-Region-Id"]:
                headers_to_set[header] = self.region
            elif value != "required":
                headers_to_set[header] = value
        
        if headers_to_set and self.page:
            await self.page.set_extra_http_headers(headers_to_set)
            logger.debug(f"Применены заголовки Playwright: {list(headers_to_set.keys())}")
    
    async def parse_all_categories(self) -> List[ParseResult]:
        """Парсинг всех категорий из Knowledge Base"""
        if not self.kb:
            return []
        
        results = []
        for category_name, category_url in self.kb.categories.items():
            logger.info(f"📦 Парсинг категории: {category_name}")
            result = await self.parse_category(category_url)
            results.append(result)
            
            # Задержка между запросами
            delay = getattr(self.kb.anti_bot, 'delay_between_requests', None)
            if delay:
                await asyncio.sleep(delay)
        
        return results
    
    async def run(self):
        """Основной метод запуска парсера"""
        logger.info(f"🎯 Запуск парсера {self.shop_name}")
        
        try:
            results = await self.parse_all_categories()
            
            total_products = sum(r.total_products for r in results)
            logger.info(f"✅ Парсинг завершен. Найдено товаров: {total_products}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга: {e}")
            raise
        finally:
            await self.close()
