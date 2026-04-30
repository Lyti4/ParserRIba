import os
import sys
import logging
from dotenv import load_dotenv
from utils.logger import setup_logger
from utils.export import ExportManager

# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logger = setup_logger("main")

def main():
    logger.info("🚀 Запуск парсера цен на рыбные товары")
    
    # Получение настроек из переменных окружения (от лаунчера)
    shops_str = os.getenv("PARSER_SHOPS", "pyaterochka")
    delay = int(os.getenv("PARSER_DELAY", "10"))
    visual_mode = os.getenv("VISUAL_MODE", "false").lower() == "true"
    
    shops = [s.strip() for s in shops_str.split(",")]
    logger.info(f"Магазины для парсинга: {', '.join(shops)}")
    logger.info(f"Задержка: {delay} сек, Визуальный режим: {'ВКЛ' if visual_mode else 'ВЫКЛ'}")

    all_products = []

    # Динамический импорт парсеров
    for shop in shops:
        try:
            module_name = f"parsers.{shop}"
            module = __import__(module_name, fromlist=[None])
            
            # Поиск класса парсера (обычно назван как магазин с суффиксом Parser)
            class_name = "".join(part.capitalize() for part in shop.split("_")) + "Parser"
            ParserClass = getattr(module, class_name, None)
            
            if not ParserClass:
                # Попытка найти класс с именем магазина в нижнем регистре + Parser
                class_name = shop + "Parser"
                ParserClass = getattr(module, class_name, None)

            if ParserClass:
                logger.info(f"🏪 Начинаем парсинг магазина: {shop}")
                parser = ParserClass(headless=not visual_mode)
                products = parser.parse(delay=delay)
                all_products.extend(products)
                logger.info(f"✅ {shop}: найдено {len(products)} товаров")
            else:
                logger.error(f"❌ Класс парсера для {shop} не найден")
                
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта модуля {shop}: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге {shop}: {e}")

    # Экспорт результатов
    if all_products:
        logger.info(f"\n📊 Всего собрано товаров: {len(all_products)}")
        exporter = ExportManager()
        report_path = exporter.save_to_excel(all_products)
        if report_path:
            logger.info(f"🎉 Готово! Отчет сохранен: {report_path}")
    else:
        logger.warning("⚠️ Не удалось получить данные о товарах")

if __name__ == "__main__":
    main()
