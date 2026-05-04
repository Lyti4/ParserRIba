"""
Pydantic модели для унифицированного вывода данных парсеров.
Все парсеры должны возвращать данные в этих форматах.
"""

from datetime import datetime
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator


class ProductPrice(BaseModel):
    """Модель цены товара с поддержкой старой/новой цены и цены за единицу."""
    current: float = Field(..., description="Текущая цена в рублях")
    old: Optional[float] = Field(None, description="Старая цена (если есть скидка)")
    unit: Optional[float] = Field(None, description="Цена за единицу измерения (кг/л/шт)")
    currency: str = Field(default="RUB", description="Валюта")
    discount_percent: Optional[int] = Field(None, description="Процент скидки")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current": 299.99,
                "old": 399.99,
                "unit": 599.98,
                "currency": "RUB",
                "discount_percent": 25
            }
        }
    )


class ProductDimensions(BaseModel):
    """Модель физических характеристик товара."""
    weight: Optional[float] = Field(None, description="Вес в граммах или кг")
    volume: Optional[float] = Field(None, description="Объем в мл или л")
    unit_type: Optional[str] = Field(None, description="Тип единицы: 'g', 'kg', 'ml', 'l', 'pcs'")
    raw_string: Optional[str] = Field(None, description="Исходная строка из сайта (напр. '500 г')")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "weight": 500.0,
                "unit_type": "g",
                "raw_string": "500 г"
            }
        }
    )


class Product(BaseModel):
    """Основная модель товара."""
    id: Optional[str] = Field(None, description="Уникальный ID товара")
    name: str = Field(..., description="Название товара")
    brand: Optional[str] = Field(None, description="Бренд/производитель")
    
    # Гибкое поле цены: принимает float, dict или ProductPrice
    price: ProductPrice = Field(..., description="Цена товара")
    original_price: Optional[float] = Field(None, description="Старая цена (упрощенно)")
    
    dimensions: Optional[ProductDimensions] = Field(None, description="Характеристики товара")
    
    image_url: Optional[HttpUrl] = Field(None, description="URL изображения товара")
    product_link: HttpUrl = Field(..., description="Ссылка на страницу товара")
    
    category: Optional[str] = Field(None, description="Категория товара")
    subcategory: Optional[str] = Field(None, description="Подкатегория товара")
    
    in_stock: bool = Field(default=True, description="Наличие товара")
    rating: Optional[float] = Field(None, description="Рейтинг товара")
    reviews_count: Optional[int] = Field(None, description="Количество отзывов")
    
    raw_data: Optional[dict] = Field(None, description="Исходные данные парсинга")
    parsed_at: datetime = Field(default_factory=datetime.now, description="Время парсинга")

    @field_validator('price', mode='before')
    @classmethod
    def normalize_price(cls, v: Any) -> ProductPrice:
        """Приводит цену к формату ProductPrice."""
        if isinstance(v, ProductPrice):
            return v
        if isinstance(v, dict):
            return ProductPrice(**v)
        if isinstance(v, (int, float)):
            # Если пришло просто число, создаем объект цены
            return ProductPrice(current=float(v))
        raise ValueError(f"Неверный формат цены: {type(v)}")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "12345",
                "name": "Филе лосося охлажденное",
                "brand": "Русское море",
                "price": {
                    "current": 299.99,
                    "old": 399.99,
                    "unit": 599.98,
                    "currency": "RUB",
                    "discount_percent": 25
                },
                "dimensions": {
                    "weight": 500.0,
                    "unit_type": "g",
                    "raw_string": "500 г"
                },
                "product_link": "https://example.com/product/12345",
                "in_stock": True
            }
        }
    )


class CategoryInfo(BaseModel):
    """Информация о категории."""
    id: Optional[str] = Field(None, description="ID категории")
    name: str = Field(..., description="Название категории")
    url: HttpUrl = Field(..., description="URL категории")
    parent_category: Optional[str] = Field(None, description="Родительская категория")
    subcategories: List[str] = Field(default_factory=list, description="Список подкатегорий")


class ParseResult(BaseModel):
    """Результат парсинга страницы категории."""
    shop: str = Field(..., description="Название магазина")
    category: CategoryInfo = Field(..., description="Информация о категории")
    products: List[Product] = Field(..., description="Список товаров")
    total_products: int = Field(..., description="Общее количество товаров на странице")
    page: int = Field(default=1, description="Номер страницы")
    has_next_page: bool = Field(default=False, description="Есть ли следующая страница")
    next_page_url: Optional[HttpUrl] = Field(None, description="URL следующей страницы")
    
    errors: List[str] = Field(default_factory=list, description="Список ошибок при парсинге")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")
    parsed_at: datetime = Field(default_factory=datetime.now, description="Время парсинга")
    parse_duration_ms: Optional[int] = Field(None, description="Длительность парсинга в мс")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shop": "pyaterochka",
                "category": {
                    "name": "Рыба и морепродукты",
                    "url": "https://example.com/fish"
                },
                "products": [],
                "total_products": 0,
                "page": 1,
                "has_next_page": False
            }
        }
    )


class ShopInfo(BaseModel):
    """Информация о магазине из Knowledge Base."""
    name: str = Field(..., description="Название магазина (код)")
    display_name: str = Field(..., description="Отображаемое название")
    base_url: HttpUrl = Field(..., description="Базовый URL")
    categories: List[CategoryInfo] = Field(default_factory=list, description="Категории")
    selectors: dict = Field(default_factory=dict, description="CSS селекторы")
    headers: dict = Field(default_factory=dict, description="Заголовки")
    anti_bot: dict = Field(default_factory=dict, description="Анти-бот защита")
    notes: List[str] = Field(default_factory=list, description="Заметки")
    recommended_tool: str = Field(default="curl-cffi", description="Рекомендуемый инструмент")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "pyaterochka",
                "display_name": "Пятерочка",
                "base_url": "https://5ka.ru",
                "recommended_tool": "playwright"
            }
        }
    )


class ParserConfig(BaseModel):
    """Конфигурация парсера для конкретного магазина."""
    shop_name: str = Field(..., description="Название магазина")
    base_url: str = Field(..., description="Базовый URL магазина")
    use_playwright: bool = Field(default=False, description="Использовать Playwright вместо curl-cffi")
    proxy_required: bool = Field(default=False, description="Требуется ли прокси")
    delay_between_requests: float = Field(default=1.0, description="Задержка между запросами в секундах")
    max_retries: int = Field(default=3, description="Максимальное количество попыток")
    timeout_seconds: int = Field(default=30, description="Таймаут запроса в секундах")
    headers: dict = Field(default_factory=dict, description="HTTP заголовки")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shop_name": "pyaterochka",
                "base_url": "https://5ka.ru",
                "use_playwright": False,
                "delay_between_requests": 1.0,
                "max_retries": 3
            }
        }
    )
