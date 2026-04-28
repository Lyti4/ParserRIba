"""
Утилиты для экспорта данных в Excel
"""
from typing import List
import pandas as pd
from loguru import logger

from models.product import FishProduct


def export_to_excel(products: List[FishProduct], filename: str = "fish_prices.xlsx"):
    """
    Экспорт списка товаров в Excel файл с группировкой по наименьшей цене
    
    Args:
        products: Список объектов FishProduct
        filename: Имя выходного файла
    """
    if not products:
        logger.warning("Нет данных для экспорта")
        return
    
    # Преобразуем в список словарей
    data = []
    for product in products:
        data.append({
            'Товар': product.name,
            'Цена (руб)': product.price,
            'Цена за кг (руб)': product.unit_price if product.unit_price else '',
            'Вес': product.weight if product.weight else '',
            'Магазин': product.store,
            'Категория': product.category,
            'Наличие': 'Да' if product.in_stock else 'Нет',
            'Ссылка': product.url,
            'Дата парсинга': product.parsed_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Сортируем по названию товара и цене
    df = df.sort_values(['Товар', 'Цена (руб)'])
    
    # Находим минимальную цену для каждого товара
    min_prices = df.groupby('Товар')['Цена (руб)'].min().reset_index()
    min_prices.columns = ['Товар', 'Минимальная цена']
    
    # Добавляем информацию о минимальной цене
    df = df.merge(min_prices, on='Товар', how='left')
    df['Выгоднее всего'] = df['Цена (руб)'] == df['Минимальная цена']
    
    # Создаем сводную таблицу с лучшими ценами
    best_prices = df[df['Выгоднее всего']].copy()
    best_prices = best_prices.sort_values('Минимальная цена')
    
    # Записываем в Excel с несколькими листами
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Полный список всех товаров
            df.to_excel(writer, sheet_name='Все товары', index=False)
            
            # Только лучшие цены
            best_prices.to_excel(writer, sheet_name='Лучшие цены', index=False)
            
            # Сводная по магазинам
            shop_summary = pd.pivot_table(
                df, 
                values='Цена (руб)', 
                index=['Товар'], 
                columns=['Магазин'], 
                aggfunc='first'
            ).reset_index()
            shop_summary.to_excel(writer, sheet_name='Сравнение по магазинам', index=False)
            
            # Статистика
            stats_data = []
            for shop in df['Магазин'].unique():
                shop_df = df[df['Магазин'] == shop]
                stats_data.append({
                    'Магазин': shop,
                    'Всего товаров': len(shop_df),
                    'Средняя цена': round(shop_df['Цена (руб)'].mean(), 2),
                    'Минимальная цена': shop_df['Цена (руб)'].min(),
                    'Максимальная цена': shop_df['Цена (руб)'].max(),
                    'Товаров с лучшей ценой': len(shop_df[shop_df['Выгоднее всего']])
                })
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Статистика', index=False)
        
        logger.info(f"Данные успешно экспортированы в {filename}")
        logger.info(f"Всего товаров: {len(df)}")
        logger.info(f"Уникальных товаров: {df['Товар'].nunique()}")
        logger.info(f"Товаров с лучшими ценами: {len(best_prices)}")
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте в Excel: {e}")
        raise


def print_best_deals(products: List[FishProduct], limit: int = 20):
    """
    Вывод в консоль товаров с лучшими ценами
    
    Args:
        products: Список объектов FishProduct
        limit: Количество товаров для вывода
    """
    if not products:
        print("Нет данных для анализа")
        return
    
    # Группируем по названию товара
    grouped = {}
    for product in products:
        if product.name not in grouped:
            grouped[product.name] = []
        grouped[product.name].append(product)
    
    # Находим лучшую цену для каждого товара
    best_deals = []
    for name, prods in grouped.items():
        best = min(prods, key=lambda p: p.price)
        best_deals.append(best)
    
    # Сортируем по цене
    best_deals.sort(key=lambda p: p.price)
    
    print("\n" + "="*80)
    print("🐟 ТОП товаров с самыми низкими ценами:")
    print("="*80)
    
    for i, product in enumerate(best_deals[:limit], 1):
        weight_info = f" ({product.weight})" if product.weight else ""
        unit_price_info = f" | {product.unit_price} руб/кг" if product.unit_price else ""
        
        print(f"{i:2}. {product.name}{weight_info}")
        print(f"    💰 {product.price} руб. в магазине {product.store}{unit_price_info}")
        print(f"    🔗 {product.url}")
        print()
