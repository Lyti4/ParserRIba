#!/usr/bin/env python3
"""
ParserRiba - Главный скрипт запуска
Парсер цен на рыбные товары для российских сетей
"""

import os
import sys
from pathlib import Path
from utils.logger import get_logger, setup_logger

logger = get_logger("main")

def _app_root() -> Path:
    """Return source root or frozen executable directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).parent

# ИЗМЕНЕНО: фикс вывода emoji/UTF-8 в стандартной Windows-консоли.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# =============================================================================
# НАСТРОЙКА CAMOUFOX ДЛЯ WINDOWS
# =============================================================================
# Принудительно указываем путь к уже скачанному браузеру Camoufox
# Это предотвращает попытки автоматической загрузки и ошибки таймаута
if sys.platform == "win32":
    camoufox_path = r"C:\CamoufoxBrowser\camoufox-135.0.1-beta.24-win.x86_64\camoufox.exe"
    if os.path.exists(camoufox_path):
        os.environ["CAMOUFOX_BIN"] = camoufox_path
        # Отключаем проверку обновлений и авто-загрузку
        os.environ["CAMOUFOX_SKIP_DOWNLOAD"] = "1"
        logger.info("Camoufox binary configured: {}", camoufox_path)
    else:
        logger.warning("Camoufox binary not found: {}", camoufox_path)
        logger.warning("Install Camoufox or update the path in main.py")
    
    # Настройка GeoIP базы данных
    geoip_path = _app_root() / "GeoLite2-City.mmdb"
    if geoip_path.exists():
        os.environ["GEOIP_PATH"] = str(geoip_path)
        logger.info("GeoIP database configured: {}", geoip_path)
    else:
        logger.info("GeoIP database not found: {}", geoip_path)
        logger.info("GeoIP stays disabled; use `python download_geoip.py` to install it")
# =============================================================================

import asyncio
import argparse
import importlib
import yaml
from datetime import datetime
from typing import Optional, List


class ParserFactory:
    """Factory for runtime-ready parser backends only."""

    PARSERS = {
        "pyaterochka": ("parsers.pyaterochka", "PyaterochkaParser"),
    }
    LEGACY_PARSERS = ("magnit", "lenta", "auchan", "okey", "perekrestok")

    @classmethod
    def _load_parser_class(cls, store_name: str):
        """Load one runtime-ready parser class."""
        module_name, class_name = cls.PARSERS[store_name]
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    
    @classmethod
    def get_parser(cls, store_name: str, config: dict, **kwargs):
        """Return one supported parser instance."""
        if store_name in cls.LEGACY_PARSERS:
            raise NotImplementedError(
                f"{store_name} is quarantined as a legacy parser path. "
                "Use onboarding/discovery tasks until a runtime-ready backend exists."
            )
        if store_name not in cls.PARSERS:
            raise ValueError(f"Неизвестный магазин: {store_name}")
        
        parser_class = cls._load_parser_class(store_name)
        
        # Проверяем доступность Camoufox
        camoufox_available = False
        try:
            from camoufox.async_api import AsyncCamoufox
            camoufox_available = True
        except ImportError:
            logger.warning("⚠️  Camoufox недоступен, будет использоваться Playwright")
        if not camoufox_available:
            logger.warning("🔄 Pyaterochka runtime may fail without Camoufox support")
        return parser_class(
            store_name=store_name,
            region=kwargs.get('region', '77'),
            headless=kwargs.get('headless', True)
        )
    
    @classmethod
    def get_available_stores(cls) -> List[str]:
        """Return runtime-ready stores only."""
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
    output_dir: str = "data",
    headless: bool = True
):
    """Парсинг конкретного магазина."""
    logger.info(f"🚀 Запуск парсинга: {store_name.upper()}")
    
    try:
        # Создание парсера с передачей headless режима
        parser = ParserFactory.get_parser(
            store_name, 
            config, 
            shop_name=store_name,
            headless=headless
        )
        
        # Получение категорий из конфига или использование всех из KB
        store_config = config.get("stores", {}).get(store_name, {})
        
        # Получаем Knowledge Base для магазина чтобы найти URL категорий
        store_kb = parser.kb
        
        if not categories:
            # Если категории не указаны, берем все из KB
            if store_kb and store_kb.categories:
                categories = list(store_kb.categories.keys())
            else:
                categories = store_config.get("categories", [])
        
        if not categories:
            logger.warning(f"Категории для {store_name} не указаны, пропускаем")
            return []
        
        all_products = []
        
        # Запускаем браузер ОДИН раз перед всеми категориями
        use_playwright = (
            store_kb and 
            getattr(store_kb, 'recommended_tool', None) == "playwright"
        ) or (
            store_kb and 
            getattr(store_kb.anti_bot, 'requires_js', False)
        )
        
        if use_playwright:
            logger.info("🌐 Запуск браузера перед обработкой всех категорий...")
            await parser.start_browser(use_camoufox=True, headless=False if not headless else "virtual")
            # Небольшая задержка после запуска
            await asyncio.sleep(2)
        
        try:
            # Парсинг каждой категории
            for category in categories:
                logger.info(f"📦 Категория: {category}")
                
                # Определяем URL категории
                category_url = None
                
                # Если категория - это ключ из KB, используем соответствующий URL
                if store_kb and category in store_kb.categories:
                    category_url = store_kb.categories[category]
                    logger.debug(f"   URL категории из KB: {category_url}")
                # Если категория уже выглядит как URL (начинается с http)
                elif category.startswith('http'):
                    category_url = category
                    logger.debug(f"   Используем URL напрямую: {category_url}")
                # Пытаемся найти категорию по частичному совпадению
                elif store_kb:
                    for kb_cat_name, kb_cat_url in store_kb.categories.items():
                        if category.lower() in kb_cat_name.lower() or kb_cat_name.lower() in category.lower():
                            category_url = kb_cat_url
                            logger.debug(f"   Найдено совпадение в KB: {kb_cat_name} -> {category_url}")
                            break
                
                if not category_url:
                    logger.error(f"❌ Не удалось определить URL для категории: {category}")
                    continue
                
                try:
                    parse_result = await parser.parse_category(category_url, category)
                    # parse_result - это ParseResult, берем products из него
                    if parse_result and hasattr(parse_result, 'products'):
                        all_products.extend(parse_result.products)
                        logger.info(f"✅ Найдено товаров: {len(parse_result.products)}")
                    else:
                        logger.warning(f"⚠️ Пустой результат для категории {category}")
                    
                    # Задержка между категориями (чтобы видеть процесс и не спамить запросами)
                    if len(categories) > 1:
                        delay = 3  # 3 секунды между категориями
                        logger.debug(f"⏳ Пауза {delay}с перед следующей категорией...")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при парсинге категории {category}: {e}")
                    continue
        finally:
            # Закрываем браузер ПОСЛЕ всех категорий
            if use_playwright:
                logger.info("🛑 Завершение работы браузера после всех категорий...")
                await parser.close_browser()
        
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
            data.append(product.model_dump(mode="json"))
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
        "--check-env",
        action="store_true",
        help="Проверить Python, Camoufox, GeoIP и прокси"
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

    if args.check_env:
        from scripts.check_environment import main as check_environment

        exit_code = check_environment()
        if exit_code:
            raise SystemExit(exit_code)
        return
    
    # Загрузка конфига
    config = load_config(args.config)
    config["browser"]["headless"] = args.headless
    
    # Вывод списка магазинов
    if args.list_stores:
        logger.info("Available runtime-ready stores:")
        for i, store in enumerate(ParserFactory.get_available_stores(), 1):
            enabled = config.get("stores", {}).get(store, {}).get("enabled", True)
            status = "enabled" if enabled else "disabled"
            logger.info("  {}. {} ({})", i, store, status)
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
                output_dir=args.output,
                headless=args.headless
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
