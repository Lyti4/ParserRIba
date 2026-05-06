"""
Модель продукта
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class FishProduct:
    """Модель рыбного продукта"""
    
    name: str  # Название товара
    price: float  # Цена
    store: str  # Магазин
    url: str  # Ссылка на товар
    category: str = ""  # Категория
    brand: str = ""  # Бренд
    weight: str = ""  # Вес/объем
    image_url: str = ""  # URL изображения
    description: str = ""  # Описание
    scraped_at: datetime = field(default_factory=datetime.now)  # Время парсинга
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "name": self.name,
            "price": self.price,
            "store": self.store,
            "url": self.url,
            "category": self.category,
            "brand": self.brand,
            "weight": self.weight,
            "image_url": self.image_url,
            "description": self.description,
            "scraped_at": self.scraped_at.isoformat()
        }
