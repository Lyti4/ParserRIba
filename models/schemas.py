"""
Pydantic модели для унифицированного вывода данных парсеров.
Все парсеры должны возвращать данные в этих форматах.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class ProductPrice(BaseModel):
    """Модель цены товара с поддержкой старой/новой цены и цены за единицу."""
    current: float = Field(..., description="Текущая цена в рублях")
    old: Optional[float] = Field(None, description="Старая цена (если есть скидка)")
    unit: Optional[float] = Field(None, description="Цена за единицу измерения (кг/л/шт)")
    currency: str = Field(default="RUB", description="Валюта")
    discount_percent: Optional[int] = Field(None, description="Процент скидки")

    class Config:
        json_schema_extra = {
            "example": {
                "current": 299.99,
                "old": 399.99,
                "unit": 599.98,
                "currency": "RUB",
                "discount_percent": 25
            }
        }


class ProductDimensions(BaseModel):
    """Модель физических характеристик товара."""
    weight: Optional[float] = Field(None, description="Вес в граммах или кг")
    volume: Optional[float] = Field(None, description="Объем в мл или л")
    unit_type: Optional[str] = Field(None, description="Тип единицы: 'g', 'kg', 'ml', 'l', 'pcs'")
    raw_string: Optional[str] = Field(None, description="Исходная строка из сайта (напр. '500 г')")

    class Config:
        json_schema_extra = {
            "example": {
                "weight": 500.0,
                "unit_type": "g",
                "raw_string": "500 г"
            }
        }


class Product(BaseModel):
    """Основная модель товара."""
    id: str = Field(..., description="Уникальный ID товара (SKU или внутренний ID магазина)")
    name: str = Field(..., description="Название товара")
    brand: Optional[str] = Field(None, description="Бренд/производитель")
    category: str = Field(..., description="Категория товара (рыба/морепродукты)")
    subcategory: Optional[str] = Field(None, description="Подкатегория")
    
    price: ProductPrice = Field(..., description="Информация о цене")
    dimensions: Optional[ProductDimensions] = Field(None, description="Вес/объем")
    
    image_url: Optional[HttpUrl] = Field(None, description="URL изображения товара")
    product_url: HttpUrl = Field(..., description="URL страницы товара")
    
    in_stock: bool = Field(default=True, description="Наличие на складе")
    rating: Optional[float] = Field(None, description="Рейтинг товара (0-5)")
    reviews_count: Optional[int] = Field(None, description="Количество отзывов")
    
    shop: str = Field(..., description="Название магазина (pyaterochka, magnit, etc.)")
    region: Optional[str] = Field(None, description="Регион получения цены")
    parsed_at: datetime = Field(default_factory=datetime.now, description="Время парсинга")
    
    # Дополнительные данные специфичные для магазина
    extra_data: Optional[dict] = Field(default_factory=dict, description="Дополнительные данные")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "12345",
                "name": "Филе лосося охлажденное",
                "brand": "Русское Море",
                "category": "Рыба охлажденная",
                "subcategory": "Лосось",
                "price": {
                    "current": 599.99,
                    "old": 799.99,
                    "unit": 1199.98,
                    "currency": "RUB",
                    "discount_percent": 25
                },
                "dimensions": {
                    "weight": 500.0,
                    "unit_type": "g",
                    "raw_string": "500 г"
                },
                "image_url": "https://example.com/image.jpg",
                "product_url": "https://example.com/product/12345",
                "in_stock": True,
                "shop": "pyaterochka",
                "region": "Москва",
                "parsed_at": "2024-01-15T10:30:00"
            }
        }


class CategoryInfo(BaseModel):
    """Информация о категории."""
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

    class Config:
        json_schema_extra = {
            "example": {
                "shop": "pyaterochka",
                "category": {
                    "name": "Рыба и морепродукты",
                    "url": "https://5ka.ru/catalog/ryba_i_moreprodukty",
                    "parent_category": "Продукты"
                },
                "products": [],
                "total_products": 0,
                "page": 1,
                "has_next_page": False,
                "errors": [],
                "warnings": ["Не найдено изображений у 3 товаров"],
                "parsed_at": "2024-01-15T10:30:00",
                "parse_duration_ms": 1523
            }
        }


class ParserConfig(BaseModel):
    """Конфигурация парсера для конкретного магазина."""
    shop_name: str = Field(..., description="Название магазина")
    base_url: HttpUrl = Field(..., description="Базовый URL магазина")
    use_playwright: bool = Field(default=False, description="Использовать Playwright вместо curl-cffi")
    proxy_required: bool = Field(default=False, description="Требуется ли прокси")
    delay_between_requests: float = Field(default=1.0, description="Задержка между запросами в секундах")
    max_retries: int = Field(default=3, description="Максимальное количество попыток")
    timeout_seconds: int = Field(default=30, description="Таймаут запроса в секундах")
    
    headers: dict = Field(default_factory=dict, description="Дополнительные заголовки")
    cookies: dict = Field(default_factory=dict, description="Куки сессии")
