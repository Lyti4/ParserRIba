#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ParserRIba - Парсер цен на рыбные товары из российских ритейлеров
Запуск через CLI или лаунчер
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import List, Dict

# Импорт парсеров
from parsers.pyaterochka import PyaterochkaParser
from parsers.magnit import MagnitParser
from parsers.perekrestok import PerekrestokParser
from parsers.lenta import LentaParser
from parsers.auchan import AuchanParser
from parsers.okey import OkeyParser

# Импорт утилит
from utils.export import ExportManager
from utils.logger import setup_logger

# Загрузка конфигурации
def load_config() -> Dict:
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "delay": 10,
        "visual_mode": False,
        "output_dir": "./data/export"
    }

def get_parser(store_name: str, headless: bool):
    """Фабрика парсеров"""
    parsers_map = {
        "pyaterochka": lambda: PyaterochkaParser(headless=headless),
        "magnit": lambda: MagnitParser(headless=headless),
        "perekrestok": lambda: PerekrestokParser(headless=headless),
        "lenta": lambda: LentaParser(headless=headless),
        "auchan": lambda: AuchanParser(headless=headless),
        "okey": lambda: OkeyParser(headless=headless),
    }
    
    store_lower = store_name.lower().strip()
    if store_lower in parsers_map:
        return parsers_map[store_lower]()
    else:
        raise ValueError(f"Неизвестный магазин: {store_name}")

def main():
    # Настройка логгера
    logger = setup_logger("main")
    
    # Получение настроек из переменных окружения (от лаунчера) или конфига
    config = load_config()
    
    shops_env = os.getenv("PARSER_SHOPS", "")
    delay_env = os.getenv("PARSER_DELAY", str(config.get("delay", 10)))
    visual_env = os.getenv("VISUAL_MODE", "false").lower() == "true"
    
    # Определение списка магазинов
    if shops_env:
        shops_to_parse = [s.strip() for s in shops_env.split(",")]
    else:
        # Если не передано через env, берем все из конфига или дефолтные
        shops_to_parse = ["pyaterochka", "magnit", "perekrestok", "lenta", "auchan", "okey"]
    
    delay = int(delay_env)
    headless = not visual_env  # Если visual_mode=True, то headless=False
    
    logger.info("🚀 Запуск парсера цен на рыбные товары")
    logger.info(f"Магазины для парсинга: {', '.join(shops_to_parse)}")
    logger.info(f"⚙️ Задержка: {delay} сек, Визуальный режим: {visual_env}")
    
    all_products = []
    
    for store_name in shops_to_parse:
        try:
            logger.info(f"🏪 Начинаем парсинг магазина: {store_name}")
            
            parser = get_parser(store_name, headless=headless)
            products = parser.parse(delay=delay)
            
            if products:
                logger.info(f"✅ Найдено товаров в {store_name}: {len(products)}")
                all_products.extend(products)
            else:
                logger.warning(f"⚠️ Товары не найдены в {store_name}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге {store_name}: {e}")
            continue
    
    # Экспорт результатов
    logger.info(f"\n📊 Всего собрано товаров: {len(all_products)}")
    
    if all_products:
        try:
            output_dir = config.get("output_dir", "./data/export")
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fish_prices_{timestamp}.xlsx"
            filepath = os.path.join(output_dir, filename)
            
            exporter = ExportManager()
            exporter.export_to_excel(all_products, filepath)
            
            logger.info(f"💾 Отчет сохранен: {filepath}")
            
            # Сохранение пути для лаунчера
            with open(os.path.join(output_dir, "last_report.txt"), "w", encoding="utf-8") as f:
                f.write(filepath)
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта: {e}")
    else:
        logger.warning("⚠️ Не удалось получить данные о товарах")
    
    logger.info("🎉 Готово!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
