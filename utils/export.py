"""
Утилиты для экспорта данных
"""
import pandas as pd
from loguru import logger
from typing import List

from models.product import FishProduct


def export_to_excel(products: List[FishProduct], filename: str):
    """Экспорт товаров в Excel файл"""
    try:
        data = [p.to_dict() for p in products]
        df = pd.DataFrame(data)
        
        # Сохраняем в Excel
        df.to_excel(filename, index=False, sheet_name='Рыбные товары')
        
        logger.info(f"Данные экспортированы в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при экспорте в Excel: {e}")
        return False


def print_best_deals(products: List[FishProduct], limit: int = 20):
    """Вывод лучших предложений по цене"""
    if not products:
        logger.warning("Нет данных для вывода")
        return
    
    # Группируем по названиям (упрощенно)
    grouped = {}
    for p in products:
        key = p.name.lower().strip()
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(p)
    
    # Находим лучшие цены
    best_deals = []
    for name, items in grouped.items():
        min_price_item = min(items, key=lambda x: x.price)
        best_deals.append(min_price_item)
    
    # Сортируем по цене
    best_deals.sort(key=lambda x: x.price)
    
    print("\n" + "="*80)
    print("🏆 ЛУЧШИЕ ПРЕДЛОЖЕНИЯ (по возрастанию цены)")
    print("="*80)
    
    for i, product in enumerate(best_deals[:limit], 1):
        print(f"{i:2}. {product.name[:50]:<50} | {product.price:>8.2f} ₽ | {product.store}")
    
    print("="*80 + "\n")
