"""
Модель данных для рыбных товаров
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FishProduct:
    """Модель рыбного товара"""
    name: str  # Название товара
    price: float  # Цена
    currency: str = "RUB"  # Валюта
    weight: Optional[str] = None  # Вес/объем
    unit_price: Optional[float] = None  # Цена за единицу (кг/л)
    store: str = ""  # Название магазина
    category: str = ""  # Категория
    url: str = ""  # Ссылка на товар
    image_url: Optional[str] = None  # Ссылка на изображение
    in_stock: bool = True  # Наличие
    parsed_at: datetime = field(default_factory=datetime.now)  # Время парсинга
    
    def __post_init__(self):
        """Вычисление цены за единицу если указан вес"""
        if self.weight and not self.unit_price:
            self.unit_price = self._calculate_unit_price()
    
    def _calculate_unit_price(self) -> Optional[float]:
        """Вычисление цены за килограмм/литр"""
        if not self.weight:
            return None
        
        try:
            # Парсинг веса (например, "500 г", "1.2 кг", "800мл")
            weight_str = self.weight.lower().replace(',', '.').strip()
            
            if 'кг' in weight_str or 'kg' in weight_str:
                weight_value = float(''.join(filter(lambda x: x.isdigit() or x == '.', weight_str)))
            elif 'г' in weight_str or 'g' in weight_str:
                weight_value = float(''.join(filter(lambda x: x.isdigit() or x == '.', weight_str))) / 1000
            elif 'мл' in weight_str or 'ml' in weight_str:
                weight_value = float(''.join(filter(lambda x: x.isdigit() or x == '.', weight_str))) / 1000
            elif 'л' in weight_str or 'l' in weight_str:
                weight_value = float(''.join(filter(lambda x: x.isdigit() or x == '.', weight_str)))
            else:
                return None
            
            if weight_value > 0:
                return round(self.price / weight_value, 2)
        except (ValueError, ZeroDivisionError):
            pass
        
        return None


@dataclass
class StoreInfo:
    """Информация о магазине"""
    name: str
    url: str
    parser_class: str
