"""
Базовый класс парсера с интеграцией Knowledge Base, стратегий и политик.
Все специфичные парсеры магазинов наследуются от этого класса.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Product, ParseResult, CategoryInfo, ParserConfig
from utils.kb_loader import KBLoader, ShopKnowledge
from strategies import BaseStrategy
from policies import PoliciesEngine, PolicyResult


class BaseParser(ABC):
    """
    Базовый класс парсера для всех магазинов.
    
    Реализует:
    - Загрузку конфигурации из Knowledge Base
    - Применение стратегий (скроллинг, пагинация)
    - Обработку ошибок через Policy Engine
    - Унифицированный вывод данных через Pydantic модели
    """
    
    def __init__(self, shop_name: str, region: Optional[str] = None):
        """
        Инициализация парсера.
        
        Args:
            shop_name: Название магазина (pyaterochka, magnit, etc.)
            region: Регион для получения цен (опционально)
        """
        self.shop_name = shop_name
        self.region = region
        self.start_time: Optional[float] = None
        
        # Загрузка конфигурации из Knowledge Base
        self.kb_loader = KBLoader()
        self.kb: ShopKnowledgeBase = self.kb_loader.load_shop(shop_name)
        
        # Инициализация политик
        self.policy_engine = PolicyEngine()
        
        # Стратегии (заполняются в подклассах)
        self.strategies: List[BaseStrategy] = []
        
        # Конфигурация
        self.config = self._build_config()
        
        print(f"🛒 Parser initialized: {self.kb.name} (region: {region or 'default'})")
        print(f"   Categories: {len(self.kb.categories)}")
        print(f"   Selectors: {len(self.kb.selectors)}")
        print(f"   Strategies: {len(self.kb.anti_bot.strategies)}")
    
    def _build_config(self) -> ParserConfig:
        """Построение конфигурации на основе Knowledge Base."""
        return ParserConfig(
            shop_name=self.kb.name,
            base_url=self.kb.base_url,
            use_playwright=self.kb.anti_bot.recommended_tool == "playwright",
            proxy_required=False,  # TODO: добавить поле в KB
            delay_between_requests=1.0,
            max_retries=3,
            timeout_seconds=30,
            headers=self.kb.headers.standard | self.kb.headers.custom,
        )
    
    async def parse_category(self, category_url: str, page: int = 1) -> ParseResult:
        """
        Парсинг страницы категории.
        
        Args:
            category_url: URL категории
            page: Номер страницы
            
        Returns:
            ParseResult с товарами и метаданными
        """
        self.start_time = time.time()
        warnings = []
        errors = []
        
        # Контекст для политик
        context = PolicyContext(
            shop=self.shop_name,
            url=category_url,
            page=page
        )
        
        try:
            # Применение стратегий пред-обработки
            await self._apply_pre_strategies(category_url)
            
            # Получение HTML (реализуется в подклассах)
            html = await self._fetch_page(category_url, page)
            
            # Парсинг товаров
            products = await self._parse_products(html, category_url)
            
            # Проверка политик после успешного парсинга
            context.response_status = 200
            context.products_count = len(products)
            self.policy_engine.evaluate(context)
            
            # Применение стратегий пост-обработки
            await self._apply_post_strategies(products)
            
            # Расчет длительности
            duration_ms = int((time.time() - self.start_time) * 1000)
            
            # Построение результата
            category_name = self._get_category_name(category_url)
            result = ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(
                    name=category_name,
                    url=category_url,
                    parent_category="Рыба и морепродукты"
                ),
                products=products,
                total_products=len(products),
                page=page,
                has_next_page=await self._has_next_page(html, page),
                next_page_url=await self._get_next_page_url(html, category_url, page),
                errors=errors,
                warnings=warnings,
                parsed_at=datetime.now(),
                parse_duration_ms=duration_ms
            )
            
            print(f"✅ Parsed {len(products)} products from {category_name} in {duration_ms}ms")
            return result
            
        except Exception as e:
            # Обработка ошибок через политики
            context.error = str(e)
            context.response_status = getattr(e, 'status_code', 500)
            
            action = self.policy_engine.evaluate(context)
            
            if action.retry:
                print(f"⚠️  Policy triggered retry: {action.reason}")
                return await self.parse_category(category_url, page)
            
            errors.append(f"Parse error: {str(e)}")
            print(f"❌ Error parsing {category_url}: {e}")
            
            # Возврат пустого результата с ошибкой
            return ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(name="Unknown", url=category_url),
                products=[],
                total_products=0,
                page=page,
                errors=errors,
                warnings=warnings,
                parsed_at=datetime.now()
            )
    
    async def _apply_pre_strategies(self, url: str) -> None:
        """Применение стратегий до запроса."""
        for strategy in self.strategies:
            if strategy.should_apply_pre("request"):
                await strategy.apply_pre(url)
    
    async def _apply_post_strategies(self, products: List[Product]) -> None:
        """Применение стратегий после парсинга."""
        for strategy in self.strategies:
            if strategy.should_apply_post("data"):
                await strategy.apply_post(products)
    
    @abstractmethod
    async def _fetch_page(self, url: str, page: int) -> str:
        """
        Получение HTML страницы.
        
        Должен быть реализован в подклассах с использованием:
        - curl-cffi (основной метод)
        - Playwright (резервный для сложных сайтов)
        """
        pass
    
    @abstractmethod
    async def _parse_products(self, html: str, category_url: str) -> List[Product]:
        """
        Парсинг товаров из HTML.
        
        Использует селекторы из Knowledge Base.
        """
        pass
    
    @abstractmethod
    async def _has_next_page(self, html: str, page: int) -> bool:
        """Проверка наличия следующей страницы."""
        pass
    
    @abstractmethod
    async def _get_next_page_url(self, html: str, category_url: str, page: int) -> Optional[str]:
        """Получение URL следующей страницы."""
        pass
    
    def _get_category_name(self, url: str) -> str:
        """Извлечение названия категории из URL или KB."""
        # Поиск в KB
        for name, cat_url in self.kb.category_urls.items():
            if cat_url in url or url in cat_url:
                return name
        
        # Fallback: извлечение из URL
        return url.rstrip('/').split('/')[-1].replace('-', ' ').title()
    
    def _extract_selector(self, selector_type: str) -> Optional[str]:
        """
        Получение селектора из Knowledge Base.
        
        Args:
            selector_type: Тип селектора (product_card, product_name, etc.)
            
        Returns:
            CSS/XPath селектор или None
        """
        selector = self.kb.selectors.get(selector_type)
        if selector:
            return selector.value
        return None
    
    async def parse_all_categories(self) -> List[ParseResult]:
        """
        Парсинг всех категорий из Knowledge Base.
        
        Returns:
            Список ParseResult для каждой категории
        """
        results = []
        
        print(f"\n📊 Starting full parse of {self.kb.name}...")
        print(f"   Total categories: {len(self.kb.categories)}")
        
        for category_name, category_url in self.kb.categories.items():
            print(f"\n🔍 Parsing category: {category_name}")
            result = await self.parse_category(category_url)
            results.append(result)
            
            # Задержка между запросами
            if self.config.delay_between_requests > 0:
                await asyncio.sleep(self.config.delay_between_requests)
        
        total_products = sum(r.total_products for r in results)
        print(f"\n✅ Completed! Total products: {total_products}")
        
        return results
    
    def get_info(self) -> Dict[str, Any]:
        """Получение информации о парсере."""
        return {
            "shop": self.kb.name,
            "region": self.region,
            "categories": list(self.kb.categories.keys()),
            "selectors": dict(self.kb.selectors),
            "headers": self.kb.headers.standard | self.kb.headers.custom,
            "anti_bot": {
                "recommended_tool": self.kb.anti_bot.recommended_tool,
                "captcha_types": self.kb.anti_bot.captcha_types,
                "strategies": self.kb.anti_bot.strategies
            },
        }
