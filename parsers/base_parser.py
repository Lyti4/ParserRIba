import asyncio
import json
import logging
import platform
import random
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from camoufox.async_api import AsyncCamoufox
from loguru import logger
from pydantic import ValidationError

from models.config import HeadersConfig, SelectorConfig, StrategyConfig
from models.product import Product
from parsers.strategies.scroll_strategy import ScrollStrategy
from utils.geoip import GeoIPService
from utils.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class BaseParser:
    """Базовый класс для всех парсеров с использованием Knowledge Base"""

    def __init__(self, store_name: str, headless: bool = True, geoip: bool = False):
        self.store_name = store_name.lower()
        self.headless = headless
        self.use_geoip = geoip
        
        # Инициализация компонентов
        self.kb = KnowledgeBase(self.store_name)
        self.geoip_service = GeoIPService() if self.use_geoip else None
        
        # Загрузка конфигурации
        self._load_knowledge_base()
        self._init_strategies()
        
        # Состояние браузера
        self._camoufox_browser: Optional[AsyncCamoufox] = None
        self._page = None
        self._context = None
        
        logger.info(f"🚀 Парсер {self.store_name} инициализирован")
        logger.info(f"   📚 Загружено {len(self.kb.categories)} категорий, {len(self.kb.selectors)} селекторов")

    def _load_knowledge_base(self):
        """Загружает базу знаний для магазина"""
        try:
            self.kb.load()
            logger.debug(f"KB загружен для {self.store_name}")
        except FileNotFoundError:
            raise ValueError(f"База знаний для '{self.store_name}' не найдена")
        except ValidationError as e:
            raise ValueError(f"Ошибка валидации KB: {e}")

    def _init_strategies(self):
        """Инициализирует стратегии на основе KB"""
        self.strategies = {}
        config = self.kb.strategies or StrategyConfig()
        
        logger.debug(f"Конфигурация стратегий: {asdict(config)}")
        
        if config.scrolling:
            self.strategies['scrolling'] = ScrollStrategy(self)
            
        # Здесь можно добавить другие стратегии (pagination, lazy_load и т.д.)

    async def _start_camoufox(self):
        """Запускает браузер Camoufox с настройками из KB"""
        if self._camoufox_browser:
            return

        system_os = platform.system()
        
        # Определяем режим headless
        # На Windows virtual display не поддерживается, используем обычный headless или видимый режим
        if system_os == "Windows":
            if self.headless:
                effective_headless = True
                logger.info("🪟 Обнаружена Windows: используется стандартный headless режим")
            else:
                effective_headless = False
                logger.info("🪟 Обнаружена Windows: virtual display заменен на headless=False (видимый режим)")
        else:
            # Linux/Mac могут использовать virtual display если нужно, но camoufox сам разберется
            effective_headless = self.headless

        logger.info(f"🦊 Запуск Camoufox (OS={system_os}, headless={effective_headless}, geoip={self.use_geoip}, humanize=True)...")

        try:
            # Формируем параметры запуска
            # Важно: передаем простые типы данных, чтобы избежать ошибок с dataclass
            launch_params = {
                "headless": effective_headless,
                "humanize": True,           # Эмуляция поведения человека
                "fingerprint": True,        # Автоматическая генерация отпечатка
                "disable_coop": True,       # Отключаем COOP для стабильности
                "block_images": False,      # Грузим картинки для правильного рендеринга
                "block_webgl": False,       # Не блокируем WebGL
                "i_know_what_im_doing": True # Отключаем предупреждения
            }
            
            logger.debug(f"🔧 Параметры запуска Camoufox: {launch_params}")

            self._camoufox_browser = AsyncCamoufox()
            
            # Запуск браузера с явной передачей аргументов
            await self._camoufox_browser.start(
                headless=launch_params["headless"],
                humanize=launch_params["humanize"],
                fingerprint=launch_params["fingerprint"],
                disable_coop=launch_params["disable_coop"],
                block_images=launch_params["block_images"],
                block_webgl=launch_params["block_webgl"],
                i_know_what_im_doing=launch_params["i_know_what_im_doing"]
            )
            
            # Создаем контекст и страницу
            self._context = await self._camoufox_browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self.kb.headers.user_agent if self.kb.headers else None
            )
            self._page = await self._context.new_page()
            
            # Применяем кастомные заголовки если есть
            if self.kb.headers and self.kb.headers.custom:
                await self._page.set_extra_http_headers(self.kb.headers.custom)
                logger.debug("Применены кастомные заголовки")

            logger.info("✅ Camoufox запущен успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка запуска Camoufox: {e}")
            await self.close_browser()
            raise

    async def close_browser(self):
        """Закрывает браузер и очищает ресурсы"""
        try:
            if self._page:
                await self._page.close()
                self._page = None
            if self._context:
                await self._context.close()
                self._context = None
            if self._camoufox_browser:
                # Корректное закрытие через контекстный менеджер
                await self._camoufox_browser.__aexit__(None, None, None)
                self._camoufox_browser = None
            logger.info("🛑 Браузер закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")

    async def parse_category(self, category_name: str) -> List[Product]:
        """Основной метод парсинга категории"""
        if category_name not in self.kb.categories:
            logger.warning(f"Категория '{category_name}' не найдена в KB")
            return []

        category_config = self.kb.categories[category_name]
        url = category_config.url
        
        products = []
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                # Запуск браузера если еще не запущен
                if not self._page:
                    await self._start_camoufox()
                    # Даем время на полную инициализацию
                    await asyncio.sleep(2)

                logger.info(f"Переход по URL: {url}")
                
                # Переход на страницу с обработкой ошибок загрузки
                try:
                    await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as nav_err:
                    if "NS_BINDING_ABORTED" in str(nav_err):
                        logger.warning("⚠️ Страница прервала загрузку (NS_BINDING_ABORTED), пробуем еще раз...")
                        await asyncio.sleep(2)
                        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    else:
                        raise

                # Ожидание появления контента
                logger.info("Ожидание загрузки контента...")
                await asyncio.sleep(5) 

                # Выполнение стратегий (скроллинг)
                if 'scrolling' in self.strategies:
                    logger.info("Выполнение стратегии скроллинга...")
                    await self.strategies['scrolling'].execute()
                    await asyncio.sleep(2) # Пауза после скролла

                # Парсинг товаров
                products = await self._parse_products_from_page(category_name)
                
                if products:
                    logger.info(f"✅ Найдено {len(products)} товаров")
                else:
                    logger.warning("⚠️ Товары не найдены после парсинга")
                
                break # Успешный выход из цикла retries

            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Ошибка при парсинге категории (попытка {retry_count}): {e}")
                if retry_count > max_retries:
                    raise
                logger.info(f"Повторная попытка через 3 секунды...")
                await asyncio.sleep(3)
                # Пробуем перезагрузить страницу
                if self._page:
                    try:
                        await self._page.reload(wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                    except:
                        pass 

        return products

    async def _parse_products_from_page(self, category_name: str) -> List[Product]:
        """Парсит товары со страницы используя селекторы из KB"""
        products = []
        
        # Получаем список селекторов для карточки товара
        # В KB они могут храниться как список строк или как объект
        card_selectors_raw = self.kb.selectors.get("product_card")
        
        card_selectors = []
        if isinstance(card_selectors_raw, list):
            card_selectors = card_selectors_raw
        elif isinstance(card_selectors_raw, str):
            card_selectors = [card_selectors_raw]
        elif hasattr(card_selectors_raw, 'css'): # Если это объект конфиг
             # Если в базе один сложный селектор, попробуем разобрать его или взять css
             # Но обычно в KB для product_card пишут просто строку CSS
             card_selectors = [card_selectors_raw.css] 
        else:
            logger.error("Неверный формат селектора product_card в KB")
            return []

        found_elements = None
        used_selector = None

        # Перебираем селекторы пока не найдем элементы
        for selector in card_selectors:
            try:
                # Пытаемся найти элементы
                elements = await self._page.query_selector_all(selector)
                if elements:
                    found_elements = elements
                    used_selector = selector
                    logger.debug(f"Найдено элементов по селектору '{selector}': {len(elements)}")
                    break
            except Exception as e:
                logger.warning(f"Селектор '{selector}' вызвал ошибку: {e}. Пробуем следующий...")
                continue
        
        if not found_elements:
            logger.warning("❌ Не удалось найти карточки товаров ни по одному из селекторов")
            # Для отладки можно сохранить HTML
            # content = await self._page.content()
            # with open(f"debug_{self.store_name}_{category_name}.html", "w", encoding="utf-8") as f:
            #     f.write(content)
            return []

        # Парсим каждый элемент
        for idx, element in enumerate(found_elements):
            try:
                product = await self._parse_product_card(element, category_name, idx)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Ошибка при парсинге карточки #{idx}: {e}")
                continue

        return products

    async def _parse_product_card(self, element, category_name: str, index: int) -> Optional[Product]:
        """Извлекает данные из отдельной карточки товара"""
        try:
            # Функция для безопасного извлечения текста
            async def get_text(selector: Optional[str]) -> str:
                if not selector: return ""
                try:
                    el = await element.query_selector(selector)
                    return (await el.inner_text()).strip() if el else ""
                except: return ""

            # Функция для безопасного извлечения атрибута
            async def get_attr(selector: Optional[str], attr: str) -> str:
                if not selector: return ""
                try:
                    el = await element.query_selector(selector)
                    return (await el.get_attribute(attr) or "").strip() if el else ""
                except: return ""
            
            # Маппинг полей из KB
            # Предполагаем, что в KB selectors хранятся в формате:
            # product_name: { css: ".name-class" }
            # price: { css: ".price-class" }
            # и т.д.
            
            sel_map = self.kb.selectors
            
            # Извлекаем данные используя селекторы из KB
            # Если селектор задан как объект SelectorConfig, берем .css
            def get_css(key: str) -> Optional[str]:
                val = sel_map.get(key)
                if isinstance(val, SelectorConfig):
                    return val.css
                elif isinstance(val, str):
                    return val
                elif isinstance(val, dict):
                    return val.get('css')
                return None

            name = await get_text(get_css("product_name"))
            price_str = await get_text(get_css("price"))
            old_price_str = await get_text(get_css("old_price"))
            image_url = await get_attr(get_css("image"), "src")
            
            # Очистка цены
            price = 0.0
            if price_str:
                clean_price = "".join(filter(str.isdigit, price_str.replace(",", ".")))
                if clean_price:
                    price = float(clean_price) / 100.0 if len(clean_price) > 2 else float(clean_price)
            
            old_price = 0.0
            if old_price_str:
                clean_old = "".join(filter(str.isdigit, old_price_str.replace(",", ".")))
                if clean_old:
                    old_price = float(clean_old) / 100.0 if len(clean_old) > 2 else float(clean_old)

            discount = 0
            if price > 0 and old_price > 0 and old_price > price:
                discount = int(((old_price - price) / old_price) * 100)

            if not name:
                return None

            return Product(
                id=f"{self.store_name}_{category_name}_{index}",
                name=name,
                price=price,
                old_price=old_price if old_price > 0 else None,
                discount=discount if discount > 0 else None,
                currency="RUB",
                category=category_name,
                shop=self.store_name,
                image_url=image_url,
                url="", # URL часто относительный, нужно склеивать с базой
                parsed_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.debug(f"Ошибка парсинга полей карточки: {e}")
            return None

    async def parse_all_categories(self) -> Dict[str, List[Product]]:
        """Парсит все категории из базы знаний"""
        results = {}
        for cat_name in self.kb.categories:
            logger.info(f"📦 Категория: {cat_name}")
            products = await self.parse_category(cat_name)
            results[cat_name] = products
            # Небольшая пауза между категориями если нужно
            await asyncio.sleep(1)
        return results
