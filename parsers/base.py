"""
Базовый класс парсера с интеграцией Knowledge Base, стратегий и политик.
Все специфичные парсеры магазинов наследуются от этого класса.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from loguru import logger
from models import Product, ParseResult, CategoryInfo, ParserConfig
from parsers.base_support import build_parser_info, extract_selector_value, resolve_category_name
from utils.kb_loader import KBLoader, ShopKnowledge
from strategies import BaseStrategy
from policies import PoliciesEngine, PolicyResult, ErrorType, ActionType


@dataclass
class PolicyContext:
    """Контекст для политик."""
    shop: str
    url: str
    page: int = 1
    request_id: Optional[str] = None
    error_count: int = 0


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
        self.kb: ShopKnowledge = self.kb_loader.load_shop(shop_name)
        
        # Инициализация политик
        self.policy_engine = PoliciesEngine()
        
        # Стратегии (заполняются в подклассах)
        self.strategies: List[BaseStrategy] = []
        
        # Конфигурация
        self.config = self._build_config()
        
        logger.info(
            "Parser initialized: {} (region: {}), categories={}, selectors={}, strategies={}",
            self.kb.name,
            region or "default",
            len(self.kb.categories),
            len(self.kb.selectors),
            len(self.kb.anti_bot.strategies),
        )
    
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
            if not context.request_id:
                import uuid
                context.request_id = str(uuid.uuid4())
            await self.policy_engine.evaluate(ErrorType.SUCCESS, context.request_id, {"products_count": len(products)})
            
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
            
            logger.info(
                "Parsed {} products from {} in {}ms",
                len(products),
                category_name,
                duration_ms,
            )
            return result
            
        except Exception as e:
            # Обработка ошибок через политики
            context.error = str(e)
            context.response_status = getattr(e, 'status_code', 500)
            if not context.request_id:
                import uuid
                context.request_id = str(uuid.uuid4())
            
            # Определение типа ошибки
            error_type = ErrorType.UNKNOWN
            if "403" in str(e):
                error_type = ErrorType.FORBIDDEN
            elif "timeout" in str(e).lower():
                error_type = ErrorType.TIMEOUT
            elif "captcha" in str(e).lower():
                error_type = ErrorType.CAPTCHA
            
            action = await self.policy_engine.evaluate(error_type, context.request_id, {"error": str(e)})
            
            if action.should_retry:
                logger.warning("Policy triggered retry: {}", action.message)
                return await self.parse_category(category_url, page)
            
            errors.append(f"Parse error: {str(e)}")
            logger.warning("Error parsing {}: {}", category_url, e)
            
            # Возврат пустого результата с ошибкой
            return ParseResult(
                shop=self.shop_name,
                category=CategoryInfo(name="Unknown", url=category_url),
                products=[],
                total_products=0,
                page=page,
                has_next_page=False,
                next_page_url=None,
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
        return resolve_category_name(url, self.kb)
    
    def _extract_selector(self, selector_type: str) -> Optional[str]:
        """
        Получение селектора из Knowledge Base.
        
        Args:
            selector_type: Тип селектора (product_card, product_name, etc.)
            
        Returns:
            CSS/XPath селектор или None
        """
        return extract_selector_value(self.kb, selector_type)
    
    async def parse_all_categories(self) -> List[ParseResult]:
        """
        Парсинг всех категорий из Knowledge Base.
        
        Returns:
            Список ParseResult для каждой категории
        """
        results = []
        
        logger.info("Starting full parse of {} with {} categories", self.kb.name, len(self.kb.categories))
        
        for category_name, category_url in self.kb.categories.items():
            logger.info("Parsing category: {}", category_name)
            result = await self.parse_category(category_url)
            results.append(result)
            
            # Задержка между запросами
            if self.config.delay_between_requests > 0:
                await asyncio.sleep(self.config.delay_between_requests)
        
        total_products = sum(r.total_products for r in results)
        logger.info("Completed full parse for {}. Total products: {}", self.kb.name, total_products)
        
        return results
    
    def get_info(self) -> Dict[str, Any]:
        """Получение информации о парсере."""
        return build_parser_info(self.kb, self.region)
