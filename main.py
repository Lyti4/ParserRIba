#!/usr/bin/env python3
"""
ParserRiba - Главный скрипт запуска
Парсер цен на рыбные товары для российских сетей
"""

import asyncio
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from utils.logger import get_logger, setup_logger
from utils.session_manager import SessionManager
from utils.kb_loader import KBLoader
from policies.engine import PoliciesEngine as PolicyEngine
from models.schemas import Product

# Импорты парсеров
from parsers.pyaterochka import PyaterochkaParser
from parsers.magnit import MagnitParser
from parsers.lenta import LentaParser
from parsers.auchan import AuchanParser
from parsers.okey import OkeyParser
from parsers.perekrestok import PerekrestokParser


logger = get_logger("main")


class ParserFactory:
    """Фабрика для создания парсеров."""
    
    PARSERS = {
        "pyaterochka": PyaterochkaParser,
        "magnit": MagnitParser,
        "lenta": LentaParser,
        "auchan": AuchanParser,
        "okey": OkeyParser,
        "perekrestok": PerekrestokParser,
    }
    
    @classmethod
    def get_parser(cls, store_name: str, config: dict, **kwargs):
        if store_name not in cls.PARSERS:
            raise ValueError(f"Неизвестный магазин: {store_name}")
        
        parser_class = cls.PARSERS[store_name]
        return parser_class(config=config, **kwargs)
    
    @classmethod
    def get_available_stores(cls) -> List[str]:
        return list(cls.PARSERS.keys())


def load_config(config_path: str = "config.yaml") -> dict:
    """Загрузка конфигурации из YAML файла."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Конфиг {config_path} не найден, используем настройки по умолчанию")
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def parse_store(
    store_name: str,
    config: dict,
    categories: Optional[List[str]] = None,
    output_dir: str = "data"
):
    """Парсинг конкретного магазина."""
    logger.info(f"🚀 Запуск парсинга: {store_name.upper()}")
    
    try:
        # Создание парсера
        parser = ParserFactory.get_parser(store_name, config)
        
        # Получение категорий из конфига или использование всех
        store_config = config.get("stores", {}).get(store_name, {})
        if not categories:
            categories = store_config.get("categories", [])
        
        if not categories:
            logger.warning(f"Категории для {store_name} не указаны, пропускаем")
            return []
        
        all_products = []
        
        # Парсинг каждой категории
        for category in categories:
            logger.info(f"📦 Категория: {category}")
            
            try:
                products = await parser.parse_category(category)
                all_products.extend(products)
                logger.info(f"✅ Найдено товаров: {len(products)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при парсинге категории {category}: {e}")
                continue
        
        # Сохранение результатов
        if all_products:
            await save_results(store_name, all_products, output_dir)
        
        return all_products
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при парсинге {store_name}: {e}")
        return []


async def save_results(store_name: str, products: list, output_dir: str):
    """Сохранение результатов в JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{store_name}_{timestamp}.json"
    filepath = output_path / filename
    
    # Конвертация Pydantic моделей в dict
    data = []
    for product in products:
        if hasattr(product, "model_dump"):
            data.append(product.model_dump())
        else:
            data.append(dict(product))
    
    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 Данные сохранены: {filepath}")


async def main():
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="ParserRiba - Парсер цен на рыбные товары",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py                          # Парсинг всех включенных магазинов
  python main.py --store pyaterochka      # Только Пятерочка
  python main.py --store magnit lenta     # Магнит и Лента
  python main.py --list-stores            # Список доступных магазинов
        """
    )
    
    parser.add_argument(
        "--store", "-s",
        nargs="+",
        help="Магазины для парсинга"
    )
    parser.add_argument(
        "--category", "-c",
        nargs="+",
        help="Категории для парсинга"
    )
    parser.add_argument(
        "--config", "-f",
        default="config.yaml",
        help="Путь к конфигурационному файлу"
    )
    parser.add_argument(
        "--output", "-o",
        default="data",
        help="Директория для сохранения данных"
    )
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Уровень логирования"
    )
    parser.add_argument(
        "--list-stores",
        action="store_true",
        help="Вывести список доступных магазинов"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Запуск браузера в headless режиме"
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Запуск браузера с интерфейсом"
    )
    
    args = parser.parse_args()
    
    # Настройка логгера
    setup_logger(level=args.log_level, log_file="logs/parser_riba.log")
    
    # Загрузка конфига
    config = load_config(args.config)
    config["browser"]["headless"] = args.headless
    
    # Вывод списка магазинов
    if args.list_stores:
        print("\n📋 Доступные магазины:")
        for i, store in enumerate(ParserFactory.get_available_stores(), 1):
            enabled = config.get("stores", {}).get(store, {}).get("enabled", True)
            status = "✅" if enabled else "❌"
            print(f"  {i}. {status} {store}")
        print()
        return
    
    # Определение магазинов для парсинга
    stores_to_parse = []
    if args.store:
        stores_to_parse = args.store
    else:
        # Парсинг всех включенных магазинов из конфига
        for store_name, store_config in config.get("stores", {}).items():
            if store_config.get("enabled", True):
                stores_to_parse.append(store_name)
    
    if not stores_to_parse:
        logger.error("❌ Не указано ни одного магазина для парсинга")
        return
    
    logger.info(f"🎯 Магазины для парсинга: {', '.join(stores_to_parse)}")
    
    # Запуск парсинга
    start_time = datetime.now()
    
    try:
        for store_name in stores_to_parse:
            await parse_store(
                store_name=store_name,
                config=config,
                categories=args.category,
                output_dir=args.output
            )
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Парсинг прерван пользователем")
    except Exception as e:
        logger.error(f"❌ Фатальная ошибка: {e}")
        raise
    finally:
        elapsed = datetime.now() - start_time
        logger.info(f"⏱️  Время выполнения: {elapsed}")


if __name__ == "__main__":
    asyncio.run(main())
