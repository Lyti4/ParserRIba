import pandas as pd
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExportManager:
    def __init__(self, output_dir: str = "data/export"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_to_excel(self, products: list, filename: str = None):
        if not products:
            logger.warning("Нет данных для экспорта")
            return None

        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"fish_prices_{timestamp}.xlsx"
            
            filepath = os.path.join(self.output_dir, filename)
            
            df = pd.DataFrame(products)
            
            # Сортировка по цене (если есть колонка price)
            if 'price' in df.columns:
                # Попытка очистить цену от символов валюты и пробелов
                df['price_numeric'] = df['price'].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.', regex=False)
                df['price_numeric'] = pd.to_numeric(df['price_numeric'], errors='coerce')
                df = df.sort_values(by='price_numeric')
                df.drop(columns=['price_numeric'], inplace=True, errors='ignore')

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Все товары')
                
                # Лист с топ-20 самых дешевых
                if len(df) > 0:
                    top_20 = df.head(20)
                    top_20.to_excel(writer, index=False, sheet_name='Топ-20 дешевых')

            logger.info(f"✅ Отчет сохранен: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения Excel: {e}")
            return None
