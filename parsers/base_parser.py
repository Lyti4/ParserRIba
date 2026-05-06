import asyncio
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class Product(BaseModel):
    """Модель товара"""
    name: str
    price: float
    currency: str = "RUB"
    weight: str = ""
    unit_price: Optional[float] = None
    image_url: str = ""
    source_url: str = ""
    shop: str
    category: str
    scraped_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    class Config:
        arbitrary_types_allowed = True

class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    def __init__(self, shop_name: str, store_name: Optional[str] = None, **kwargs):
        self.shop_name = shop_name
        self.store_name = store_name or shop_name
        self.headless = kwargs.get('headless', True)
        self.geoip_path = kwargs.get('geoip_path')
        self.categories: Dict[str, str] = {}
        self.selectors: Dict[str, str] = {}
        self.strategies: Dict[str, bool] = {}
        self.current_category_name: str = ""
        
        # Загрузка Knowledge Base
        self._load_knowledge_base()
        self._init_strategies()
        
        logger.info(f"🚀 Парсер {self.store_name} инициализирован")
        logger.info(f"   📚 Загружено {len(self.categories)} категорий, {len(self.selectors)} селекторов")

    def _load_knowledge_base(self):
        """Загрузка конфигурации из Markdown файла"""
        kb_path = Path(__file__).parent.parent / "knowledge_base" / f"{self.store_name}.md"
        
        if not kb_path.exists():
            logger.error(f"❌ Knowledge Base не найден: {kb_path}")
            raise FileNotFoundError(f"KB file not found: {kb_path}")
        
        with open(kb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсинг YAML блока в начале файла
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                try:
                    config = yaml.safe_load(parts[1])
                    self.categories = config.get('categories', {})
                    self.selectors = config.get('selectors', {})
                    logger.debug(f"KB загружен для {self.store_name}")
                except Exception as e:
                    logger.error(f"Ошибка парсинга KB: {e}")
                    raise
        else:
            logger.warning("KB файл не содержит YAML заголовка")

    def _init_strategies(self):
        """Инициализация стратегий"""
        self.strategies = {
            'scrolling': True,
            'pagination': False,
            'lazy_load': False
        }
        logger.debug(f"Конфигурация стратегий: {self.strategies}")

    @abstractmethod
    async def start_browser(self):
        """Запуск браузера (реализуется в наследниках)"""
        pass

    @abstractmethod
    async def parse_category(self, category_url: str, category_name: str) -> List[Product]:
        """Парсинг категории (реализуется в наследниках)"""
        pass

    async def parse_all(self) -> List[Product]:
        """Парсинг всех категорий"""
        all_products = []
        
        for category_name, category_url in self.categories.items():
            logger.info(f"📦 Категория: {category_name}")
            self.current_category_name = category_name
            
            try:
                products = await self.parse_category(category_url, category_name)
                all_products.extend(products)
                logger.info(f"✅ Найдено {len(products)} товаров в категории {category_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка при парсинге категории {category_name}: {e}")
                
        return all_products
