"""
Модели данных для парсеров.

Новые Pydantic модели (schemas.py) обеспечивают:
- Валидацию данных
- Сериализацию в JSON
- Единую структуру для всех магазинов
- Поддержку сложных типов (цены, размеры)

Старая модель FishProduct (product.py) сохраняется для обратной совместимости.
"""

from .schemas import (
    Product,
    ProductPrice,
    ProductDimensions,
    CategoryInfo,
    ParseResult,
    ParserConfig
)

# Обратная совместимость
from .product import FishProduct

__all__ = [
    # Новые Pydantic модели
    "Product",
    "ProductPrice",
    "ProductDimensions",
    "CategoryInfo",
    "ParseResult",
    "ParserConfig",
    # Старая модель (deprecated)
    "FishProduct"
]
