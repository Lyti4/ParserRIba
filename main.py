"""
Основной файл приложения для парсинга цен на рыбные товары
"""
import asyncio
from loguru import logger
import sys

from config import STORES, OUTPUT_FILE
from parsers.pyaterochka import PyaterochkaParser
from parsers.magnit import MagnitParser
from parsers.perekrestok import PerekrestokParser
from parsers.lenta import LentaParser
from parsers.auchan import AuchanParser
from parsers.okey import OkeyParser
from utils.export import export_to_excel, print_best_deals


# Маппинг магазинов и их парсеров
PARSERS = {
    "pyaterochka": PyaterochkaParser,
    "magnit": MagnitParser,
    "perekrestok": PerekrestokParser,
    "lenta": LentaParser,
    "auchan": AuchanParser,
    "okey": OkeyParser,
}


async def main():
    """Основная функция приложения"""
    
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add("parser.log", rotation="10 MB", level="DEBUG")
    
    logger.info("🚀 Запуск парсера цен на рыбные товары")
    logger.info(f"Магазины для парсинга: {', '.join(STORES)}")
    
    all_products = []
    
    # Парсинг каждого магазина
    for store_id in STORES:
        if store_id not in PARSERS:
            logger.warning(f"Парсер для {store_id} не найден, пропускаем")
            continue
        
        try:
            logger.info(f"🏪 Начинаем парсинг магазина: {store_id}")
            
            parser_class = PARSERS[store_id]
            parser = parser_class()
            
            products = await parser.parse_fish_products()
            all_products.extend(products)
            
            logger.info(f"✅ Завершен парсинг {store_id}. Найдено товаров: {len(products)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге {store_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            continue
    
    logger.info(f"\n📊 Всего собрано товаров: {len(all_products)}")
    
    if all_products:
        # Экспорт в Excel
        logger.info(f"💾 Экспорт данных в {OUTPUT_FILE}")
        export_to_excel(all_products, OUTPUT_FILE)
        
        # Вывод лучших предложений в консоль
        print_best_deals(all_products, limit=20)
        
        logger.success(f"🎉 Парсинг завершен! Результаты сохранены в {OUTPUT_FILE}")
    else:
        logger.warning("⚠️ Не удалось получить данные о товарах")
    
    return all_products


if __name__ == "__main__":
    asyncio.run(main())
