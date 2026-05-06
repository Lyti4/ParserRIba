"""
Парсер с использованием Camoufox для максимального обхода антибот-систем.
Camoufox - это модифицированный Firefox с улучшенной маскировкой под реального пользователя.

Использование:
    async with CamoufoxParser("pyaterochka", "https://example.com") as parser:
        html = await parser.fetch_page("https://example.com/catalog")
        products = await parser.parse_products(html)

Преимущества Camoufox перед Playwright:
    - Лучшая маскировка navigator.webdriver
    - Реальные отпечатки браузера (fingerprints)
    - Встроенные аддоны для обхода детекции
    - Меньше ресурсов чем Chromium
"""
import asyncio
import random
from typing import Optional, List, Dict, Any
from loguru import logger

from models.product import FishProduct
from parsers.base_parser import BaseParser


class CamoufoxParser(BaseParser):
    """
    Парсер на базе Camoufox - максимальная маскировка под реального пользователя.
    
    Camoufox автоматически:
    - Генерирует реалистичные user-agent и fingerprint
    - Маскирует webdriver признаки
    - Добавляет случайные задержки и движения мыши
    - Эмулирует реального пользователя из России
    """
    
    def __init__(self, store_name: str, base_url: str, headless: bool = True, region: str = "77"):
        """
        Инициализация Camoufox парсера.
        
        Args:
            store_name: Название магазина
            base_url: Базовый URL магазина
            headless: Запуск в фоновом режиме
            region: Регион для X-Region header
        """
        super().__init__(shop_name=store_name, region=region, headless=headless)
        self.region = region
        self.base_url = base_url
        
        # Camoufox атрибуты
        self._camoufox = None
        self._browser = None
        self._context = None
        self._page = None
        
        logger.info(f"🦊 CamoufoxParser инициализирован для {store_name}")
    
    async def start_browser(self, headless: bool = None, geoip: bool = False, 
                           block_images: bool = True, block_webgl: bool = True,
                           addons: Optional[List[str]] = None):
        """
        Запуск браузера Camoufox (Firefox с улучшенной маскировкой).
        
        Args:
            headless: Запускать ли в фоновом режиме. Если None, используется значение из конструктора.
            geoip: Автоматически согласовать геолокацию с прокси
            block_images: Блокировать загрузку изображений
            block_webgl: Блокировать WebGL
            addons: Список путей к аддонам (например, uBlock Origin)
        """
        if headless is None:
            headless = self.headless
        
        try:
            from camoufox.async_api import AsyncCamoufox
            
            logger.info(f"🦊 Запуск Camoufox (headless={headless})...")
            
            # Определяем режим headless
            # Для Linux-серверов используем виртуальный дисплей
            import sys
            if sys.platform.startswith('linux') and not headless:
                headless_mode = "virtual"  # Виртуальный дисплей для серверов
            elif headless:
                headless_mode = True
            else:
                headless_mode = False
            
            # Генерация отпечатка через BrowserForge
            from utils.fingerprint import FingerprintGenerator
            fp_gen = FingerprintGenerator()
            fingerprint = fp_gen.generate_fingerprint()
            camoufox_config = fp_gen.get_camoufox_config(fingerprint)
            
            # Настройки для максимальной маскировки
            # humanize добавляет случайные задержки и движения мыши
            # i_know_what_im_doing отключает предупреждения для продакшена
            browser_args = {
                "headless": headless_mode,
                "locale": "ru-RU",
                "humanize": True,   # Эмуляция поведения человека (C++ реализация надёжнее)
                "i_know_what_im_doing": True,  # Для стабильности
                "config": camoufox_config,  # Конфигурация отпечатка из BrowserForge
            }
            
            # Добавляем geoip если требуется
            if geoip:
                browser_args["geoip"] = True
                logger.info("   🌍 GeoIP включен: автоматическое согласование региона с прокси")
            
            # Добавляем блокировку ресурсов
            if block_images:
                browser_args["block_images"] = True
            if block_webgl:
                browser_args["block_webgl"] = True
            
            # Добавляем аддоны
            if addons:
                browser_args["addons"] = addons
                logger.info(f"   🧩 Аддоны: {addons}")
            
            self._camoufox = AsyncCamoufox(**browser_args)
            
            # Запускаем браузер через контекстный менеджер
            self._browser = await self._camoufox.__aenter__()
            
            # Создаём контекст с настройками региона
            context_args = {
                "viewport": {"width": 1920, "height": 1080},
                "locale": "ru-RU",
                "timezone_id": "Europe/Moscow",
                "user_agent": await self._camoufox.get_ua(),  # Реальный UA от Camoufox
            }
            
            # Добавляем геолокацию только если она не None
            if self.region and self.region != "default":
                context_args["geolocation"] = {"latitude": 55.7558, "longitude": 37.6173}
            
            self._context = await self._browser.new_context(**context_args)
            
            # Добавляем заголовки региона из Knowledge Base
            if self.kb and self.kb.headers:
                custom_headers = self.kb.headers.custom
                headers_to_set = {}
                for header, value in custom_headers.items():
                    if value == "required" and "Region" in header:
                        headers_to_set[header] = self.region
                    elif value != "required":
                        headers_to_set[header] = value
                
                if headers_to_set:
                    await self._context.set_extra_http_headers(headers_to_set)
                    logger.debug(f"Применены региональные заголовки: {headers_to_set}")
            
            self._page = await self._context.new_page()
            
            # Блокируем ресурсы для ускорения и скрытности
            await self._page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
            await self._page.route("**/*.mp4", lambda route: route.abort())
            await self._page.route("**/analytics/*", lambda route: route.abort())
            await self._page.route("**/track/*", lambda route: route.abort())
            await self._page.route("**/telemetry/*", lambda route: route.abort())
            
            logger.info("✅ Camoufox запущен успешно")
            logger.info("   🛡️ Маскировка: webdriver скрыт, fingerprint реалистичный, OS рандомизирован")
            logger.info("   🚫 Блокировка: изображения, видео, трекеры, аналитика")
            
        except ImportError:
            logger.error("❌ Camoufox не установлен. Установите: pip install camoufox")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Camoufox: {e}")
            raise
    
    async def close_browser(self):
        """Закрытие браузера и очистка ресурсов"""
        try:
            if self._page:
                await self._page.close()
                self._page = None
            
            if self._context:
                await self._context.close()
                self._context = None
            
            if self._browser:
                await self._browser.close()
                self._browser = None
            
            if self._camoufox:
                await self._camoufox.__aexit__(None, None, None)
                self._camoufox = None
            
            logger.info("🛑 Camoufox закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии Camoufox: {e}")
    
    async def fetch_page_camoufox(
        self, 
        url: str, 
        wait_for_selector: Optional[str] = None,
        timeout: int = 30000,
        scroll_down: bool = True
    ) -> Optional[str]:
        """
        Загрузка страницы через Camoufox с полным рендерингом JavaScript.
        Алиас для совместимости.
        """
        return await self.fetch_page(
            url=url,
            wait_for_selector=wait_for_selector,
            timeout=timeout,
            scroll_down=scroll_down
        )

    async def fetch_page(
        self, 
        url: str, 
        wait_for_selector: Optional[str] = None,
        timeout: int = 30000,
        scroll_down: bool = True
    ) -> Optional[str]:
        """
        Загрузка страницы через Camoufox с полным рендерингом JavaScript.
        
        Args:
            url: URL страницы
            wait_for_selector: CSS селектор элемента, которого нужно дождаться
            timeout: Таймаут в миллисекундах
            scroll_down: Прокрутить страницу для загрузки lazy content
        
        Returns:
            HTML содержимое или None при ошибке
        """
        if not self._page:
            await self.start_browser()
        
        try:
            logger.info(f"🔗 Запрос к {url} через Camoufox...")
            
            # Случайная задержка перед запросом (эмуляция человека)
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Переход на страницу с ожиданием networkidle
            await self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Проверка на капчу или страницу защиты
            await asyncio.sleep(2.0)  # Небольшая пауза для загрузки страницы проверки
            
            captcha_selectors = [
                'iframe[src*="captcha"]',
                'div[class*="captcha"]',
                'div[class*="challenge"]',
                '#challenge-form',
                '.cf-browser-verification',
                'h1:has-text("Checking")',
                'h1:has-text("Проверка")'
            ]
            
            captcha_detected = False
            for selector in captcha_selectors:
                try:
                    captcha_element = await self._page.query_selector(selector)
                    if captcha_element:
                        captcha_detected = True
                        break
                except:
                    continue
            
            if captcha_detected:
                logger.warning("⚠️ Обнаружена капча или страница проверки!")
                if not self.headless:
                    logger.info("⏳ Ожидание ручного прохождения капчи (90 секунд)...")
                    logger.info("💡 Решите капчу в открывшемся окне браузера")
                    try:
                        # Ждем появления товаров или таймаут 90 секунд
                        await self._page.wait_for_selector(wait_for_selector, timeout=90000)
                        logger.info("✅ Капча пройдена!")
                    except Exception as e:
                        logger.error(f"❌ Таймаут ожидания капчи: {e}")
                        raise
                else:
                    logger.error("❌ Капча обнаружена, но браузер в фоновом режиме. Запустите с --no-headless")
                    raise TimeoutError("Капча не может быть пройдена в фоновом режиме")
            elif wait_for_selector:
                logger.debug(f"⏳ Ожидание селектора: {wait_for_selector}")
                try:
                    await self._page.wait_for_selector(wait_for_selector, timeout=timeout)
                except Exception as e:
                    logger.warning(f"⚠️ Селектор не найден за {timeout}мс, продолжаем...")
            
            # Дополнительная задержка для полного рендеринга
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Применение стратегий (скролл, lazy load)
            if scroll_down and self.strategies:
                for strategy in self.strategies:
                    logger.debug(f"📜 Применение стратегии: {strategy.__class__.__name__}")
                    await strategy.apply(self._page)
            
            # Получаем HTML
            html = await self._page.content()
            logger.info(f"✅ Страница загружена успешно ({len(html)} символов)")
            
            return html
            
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке {url} через Camoufox: {e}")
            
            # Попытка сделать скриншот для отладки
            try:
                screenshot_path = f"/tmp/camoufox_error_{random.randint(1000, 9999)}.png"
                await self._page.screenshot(path=screenshot_path, full_page=True)
                logger.warning(f"📸 Скриншот ошибки сохранён: {screenshot_path}")
            except:
                pass
            
            return None
    
    async def extract_with_camoufox(
        self, 
        url: str, 
        selector: str, 
        attribute: Optional[str] = None,
        timeout: int = 30000
    ) -> Optional[str]:
        """
        Извлечение конкретных данных со страницы через Camoufox.
        
        Args:
            url: URL страницы
            selector: CSS селектор элемента
            attribute: Атрибут для извлечения (None для текста)
            timeout: Таймаут в миллисекундах
        
        Returns:
            Значение или None
        """
        if not self._page:
            await self.start_browser()
        
        try:
            await self._page.goto(url, wait_until="networkidle", timeout=timeout)
            
            # Ждём появления элемента
            await self._page.wait_for_selector(selector, timeout=timeout)
            
            if attribute:
                value = await self._page.get_attribute(selector, attribute)
            else:
                value = await self._page.text_content(selector)
            
            result = value.strip() if value else None
            logger.debug(f"Извлечено из {selector}: {result[:50] if result else 'None'}...")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных: {e}")
            return None
    
    async def screenshot(self, path: str, full_page: bool = True):
        """
        Сделать скриншот страницы.
        
        Args:
            path: Путь для сохранения скриншота
            full_page: Скриншот всей страницы
        """
        if self._page:
            await self._page.screenshot(path=path, full_page=full_page)
            logger.info(f"📸 Скриншот сохранён: {path}")
    
    async def human_like_scroll(self):
        """
        Эмуляция человеческого скроллинга с паузами.
        Полезно для сайтов с lazy loading и защитой от ботов.
        """
        if not self._page:
            return
        
        try:
            # Получаем высоту страницы
            page_height = await self._page.evaluate("document.body.scrollHeight")
            viewport_height = await self._page.evaluate("window.innerHeight")
            
            current_position = 0
            scroll_step = viewport_height // 3  # Скроллим по трети экрана
            
            while current_position < page_height - viewport_height:
                # Случайная позиция скролла
                target_position = min(current_position + scroll_step + random.randint(-50, 50), 
                                     page_height - viewport_height)
                
                # Плавный скролл
                await self._page.evaluate(f"window.scrollTo({{top: {target_position}, behavior: 'smooth'}})")
                
                # Случайная пауза между скроллами (как у человека)
                pause = random.uniform(0.5, 1.5)
                await asyncio.sleep(pause)
                
                current_position = target_position
            
            # Возвращаемся наверх
            await self._page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(0.5)
            
            logger.debug("✅ Human-like скроллинг выполнен")
            
        except Exception as e:
            logger.error(f"Ошибка при скроллинге: {e}")
    
    async def parse_products_from_page(self) -> List[FishProduct]:
        """
        Парсинг товаров со страницы с использованием селекторов из KB.
        
        Returns:
            Список товаров
        """
        if not self._page or not self.kb:
            return []
        
        products = []
        
        try:
            # Получаем селектор карточки товара из KB
            card_selector = self.get_selector("product_card")
            if not card_selector:
                logger.error("❌ Селектор product_card не найден в KB")
                return products
            
            # Находим все карточки товаров
            cards = await self._page.query_selector_all(card_selector)
            logger.info(f"📦 Найдено {len(cards)} карточек товаров")
            
            for i, card in enumerate(cards):
                try:
                    # Извлекаем данные с использованием селекторов из KB
                    name = await self._extract_from_element(card, "product_name")
                    price_str = await self._extract_from_element(card, "price_current")
                    
                    if not name:
                        continue
                    
                    # Парсим цену
                    price = self._parse_price(price_str) if price_str else 0.0
                    
                    # Ссылка на товар
                    product_url = await self._extract_from_element(card, "product_link", "href")
                    if product_url and not product_url.startswith("http"):
                        # Относительный URL превращаем в абсолютный
                        from urllib.parse import urljoin
                        product_url = urljoin(self.base_url, product_url)
                    
                    # Изображение
                    image_url = await self._extract_from_element(card, "product_image", "src")
                    
                    product = FishProduct(
                        id=f"{self.shop_name}_{i}",
                        name=name,
                        price=price,
                        original_price=self._parse_price(await self._extract_from_element(card, "price_original")) if self.get_selector("price_original") else None,
                        currency="RUB",
                        category="Fish",
                        product_url=product_url or self.base_url,
                        shop=self.shop_name,
                        image_url=image_url,
                        in_stock=True,
                    )
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка парсинга карточки {i}: {e}")
                    continue
            
            logger.info(f"✅ Распаршено {len(products)} товаров")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга товаров: {e}")
        
        return products
    
    async def _extract_from_element(self, element, selector_type: str, attribute: Optional[str] = None) -> Optional[str]:
        """
        Извлечение данных из элемента с использованием селектора из KB.
        
        Args:
            element: Базовый элемент
            selector_type: Тип селектора из KB
            attribute: Атрибут для извлечения
        
        Returns:
            Значение или None
        """
        selector = self.get_selector(selector_type)
        if not selector:
            return None
        
        try:
            child = await element.query_selector(selector)
            if not child:
                return None
            
            if attribute:
                return await child.get_attribute(attribute)
            else:
                text = await child.text_content()
                return text.strip() if text else None
                
        except Exception as e:
            logger.debug(f"Не удалось извлечь {selector_type}: {e}")
            return None
    
    def _parse_price(self, price_str: str) -> float:
        """Парсинг строки цены в числовое значение"""
        if not price_str:
            return 0.0
        
        try:
            # Удаляем всё кроме цифр, точки и запятой
            import re
            cleaned = re.sub(r"[^\d.,]", "", price_str.replace(",", "."))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        await self.close_browser()


# Пример использования
async def example_usage():
    """Пример использования Camoufox парсера"""
    async with CamoufoxParser("Test Store", "https://example.com", headless=True) as parser:
        # Загружаем страницу
        html = await parser.fetch_page_camoufox("https://example.com")
        if html:
            print(f"Страница загружена, длина HTML: {len(html)}")
        
        # Делаем скриншот
        await parser.screenshot("/tmp/example_screenshot.png")
        
        # Human-like скроллинг
        await parser.human_like_scroll()


if __name__ == "__main__":
    asyncio.run(example_usage())
